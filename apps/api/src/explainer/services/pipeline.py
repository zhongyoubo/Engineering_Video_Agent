import json
import shutil
import threading
import time
import zipfile
from pathlib import Path

from ..adapters.runtime import execute_runtime
from ..adapters.native_agent import native_plan, NativeAgentError
from .engineering.workspace import EngineeringError
from ..adapters.voice import estimated_cues, probe, synthesize, voice_cache_key
from ..config import ROOT
from ..db import encode
from ..domain import Brief, ContentIR, Cue, Scene, StoryboardIR
from ..storage import Storage
from .ingestion import analyze
from .planning import plan
from .process import Runner
from .quality import inspect, inspect_video
from .editorial import (
    prepare_presentation,
    require_publishable,
    publication_findings,
    EditorialError,
    register_runtime_scene,
)
from .timeline import allocate, required_tempo, word_cues, TimelineConflict
from ..adapters.alignment import forced_align, validate_words


class Canceled(Exception):
    pass


class LostLease(Exception):
    pass


class StagePaused(Exception):
    pass


class Pipeline:
    def __init__(self, settings, db, job, until_stage=None):
        self.settings, self.db, self.job = settings, db, job
        self.store = Storage(settings, db)
        self.tenant = job["tenant"]
        self.revision = db.one(
            "SELECT * FROM revisions WHERE id=? AND tenant=?", (job["revision_id"], self.tenant)
        )
        self.brief = Brief.model_validate_json(self.revision["brief"])
        self.directory = settings.data_dir / "work" / job["id"]
        self.directory.mkdir(parents=True, exist_ok=True)
        self.runner = Runner(self.guard)
        self.stopped = threading.Event()
        self.until_stage = until_stage

    def guard(self):
        row = self.db.one("SELECT state,fence,lease_owner FROM jobs WHERE id=?", (self.job["id"],))
        if not row or row["fence"] != self.job["fence"] or row["lease_owner"] != self.job["lease_owner"]:
            raise LostLease()
        if row["state"] == "CANCEL_REQUESTED":
            raise Canceled()

    def heartbeat(self):
        while not self.stopped.wait(max(1, self.settings.lease_seconds / 3)):
            if not self.db.heartbeat(self.job, self.settings.lease_seconds):
                return

    def asset(self, path, kind, mime, filename=None):
        return self.store.put(self.tenant, Path(path).read_bytes(), kind, filename or Path(path).name, mime)[
            "id"
        ]

    def stage(self, name, progress, function):
        self.guard()
        existing = self.db.one(
            "SELECT payload FROM checkpoints WHERE job_id=? AND stage=?", (self.job["id"], name)
        )
        if existing:
            if self.until_stage == name:
                raise StagePaused()
            return json.loads(existing["payload"])
        self.db.execute(
            "UPDATE jobs SET stage=?,progress=?,updated=? WHERE id=? AND fence=?",
            (name, progress, time.time(), self.job["id"], self.job["fence"]),
        )
        self.db.event(self.job, "stage.started", {"stage": name, "progress": progress})
        result = function()
        self.guard()
        with self.db.transaction() as c:
            self.db.lock_job(c, self.job["id"])
            current = c.execute(
                "SELECT fence,lease_owner,state FROM jobs WHERE id=?", (self.job["id"],)
            ).fetchone()
            if current["fence"] != self.job["fence"] or current["lease_owner"] != self.job["lease_owner"]:
                raise LostLease()
            if current["state"] == "CANCEL_REQUESTED":
                raise Canceled()
            for column, value in result.get("revision_fields", {}).items():
                if column not in {"content", "storyboard", "quality", "brief"}:
                    raise ValueError("Invalid revision update")
                c.execute(f"UPDATE revisions SET {column}=? WHERE id=?", (encode(value), self.revision["id"]))
            for role, asset_id in result.get("outputs", {}).items():
                c.execute(
                    "INSERT INTO outputs VALUES(?,?,?) ON CONFLICT(revision_id,role) DO UPDATE SET asset_id=excluded.asset_id",
                    (self.revision["id"], role, asset_id),
                )
            c.execute("INSERT INTO checkpoints VALUES(?,?,?)", (self.job["id"], name, encode(result)))
            self.db.event(self.job, "stage.completed", {"stage": name}, c)
        if self.until_stage == name:
            raise StagePaused()
        return result

    def run(self):
        thread = threading.Thread(target=self.heartbeat, daemon=True)
        thread.start()
        try:
            self._run()
        except StagePaused:
            self.db.release_stage(self.job)
        except Canceled:
            self.db.finish(self.job, "CANCELED")
        except LostLease:
            pass
        except Exception as exc:
            # No provider keys, prompts or raw subprocess output in the user-facing error.
            code = type(exc).__name__
            self.db.finish(
                self.job,
                "FAILED",
                str(exc)
                if isinstance(exc, (TimelineConflict, NativeAgentError, EngineeringError, EditorialError))
                else f"{code}: 阶段 {self.db.one('SELECT stage FROM jobs WHERE id=?', (self.job['id'],))['stage']} 未完成；检查服务和运行配置。",
            )
            raise
        finally:
            self.stopped.set()
            thread.join(timeout=3)

    def _run(self):
        manifest = None
        if self.brief.input_id:
            row = self.db.one(
                "SELECT * FROM inputs WHERE id=? AND tenant=?", (self.brief.input_id, self.tenant)
            )
            if not row or row["project_id"] != self.revision["project_id"]:
                raise ValueError("Invalid input reference")
            manifest = json.loads(row["manifest"])

        def understanding():
            content = (
                ContentIR.model_validate_json(self.revision["content"])
                if self.revision["content"]
                else analyze(self.brief, manifest)
            )
            return {"content": content.model_dump(), "revision_fields": {"content": content.model_dump()}}

        analyzed = self.stage("understanding", 0.06, understanding)
        content = ContentIR.model_validate(analyzed["content"])

        def planning():
            outputs = {}
            production_plan = None
            editing = self.brief.agent_change is not None
            if self.revision["storyboard"] and not editing:
                board = StoryboardIR.model_validate_json(self.revision["storyboard"])
            elif self.brief.video_mode == "engineering" and not editing:
                from .engineering.agent import NativeEngineeringAgent
                from .engineering.integration import professional_preflight

                if self.brief.mode != "storyboard":
                    professional_preflight(self.brief, self.settings)
                agent = NativeEngineeringAgent(
                    self.settings,
                    self.runner,
                    content,
                    self.brief,
                    manifest,
                    self.directory / "production-planning",
                    lambda kind, payload: self.db.event(self.job, kind, payload),
                )
                plan_document, board, agent_report = agent.plan()
                production_plan = plan_document.model_dump()
                from .planning import distribute

                board = distribute(board, self.brief.target_seconds)
                outputs["agent"] = self.store.put(
                    self.tenant, encode(agent_report).encode(), "report", "agent-run.json", "application/json"
                )["id"]
            elif self.brief.agent_engine != "pipeline":
                board, agent_report = native_plan(
                    content,
                    self.brief,
                    self.settings,
                    manifest,
                    self.directory / "native-agent",
                    self.runner,
                    lambda kind, payload: self.db.event(self.job, kind, payload),
                    **(
                        {"existing_board": StoryboardIR.model_validate_json(self.revision["storyboard"])}
                        if editing and self.revision["storyboard"]
                        else {}
                    ),
                )
                from .planning import distribute

                if not editing:
                    board = distribute(board, self.brief.target_seconds)
                outputs["agent"] = self.store.put(
                    self.tenant, encode(agent_report).encode(), "report", "agent-run.json", "application/json"
                )["id"]
            else:
                board = plan(content, self.brief, self.settings)
            prepare_presentation(board, self.brief)
            valid = {x.id for x in content.claims}
            evid = {x.id for x in content.evidence}
            if any(set(s.claim_ids) - valid or set(s.evidence_ids) - evid for s in board.scenes):
                raise ValueError("Invalid claim reference")
            if self.brief.video_mode == "engineering":
                if production_plan is None:
                    parent_plan = self.db.one(
                        "SELECT asset_id FROM outputs WHERE revision_id=? AND role='production_plan'",
                        (self.revision.get("parent_id"),),
                    )
                    if not parent_plan:
                        raise EngineeringError("Engineering revisions require the original production plan")
                    _, path = self.store.get(self.tenant, parent_plan["asset_id"])
                    production_plan = json.loads(path.read_text())
                    production_plan["revision_request"] = (
                        self.brief.agent_change.model_dump()
                        if editing
                        else "Use the saved edited storyboard and actual props as authoritative."
                    )
                if board.editorial:
                    production_plan["editorial"] = board.editorial.model_dump()
                outputs["production_plan"] = self.store.put(
                    self.tenant,
                    encode(production_plan).encode(),
                    "report",
                    "production-plan.json",
                    "application/json",
                )["id"]
            self.brief.agent_change = None
            board.width, board.height = self.brief.render_profile.width, self.brief.render_profile.height
            board.design_pack = self.brief.design_pack
            return {
                "board": board.model_dump(),
                "production_plan": production_plan,
                "revision_fields": {"storyboard": board.model_dump(), "brief": self.brief.model_dump()},
                "outputs": outputs,
            }

        planned = self.stage("planning", 0.16, planning)
        board = StoryboardIR.model_validate(planned["board"])
        if self.brief.mode == "storyboard":
            self.db.event(self.job, "preview.ready", {"mode": "storyboard"})
            self.db.finish(self.job, "SUCCEEDED")
            return

        def runtime():
            result = (
                execute_runtime(self.settings, manifest, self.brief, self.directory, self.runner)
                if manifest
                else {"state": "not_requested", "message": "提示词视频没有源码运行。"}
            )
            if result.get("image_path"):
                result["media_id"] = self.asset(result["image_path"], "capture", "image/png")
            if result.get("video_path"):
                result["media_id"] = self.asset(result["video_path"], "capture", "video/webm")
                result["media_kind"] = "video"
            return {"runtime": result}

        runtime_result = self.stage("runtime", 0.24, runtime)["runtime"]
        if runtime_result.get("state") == "observed":
            observed = Scene(
                id="observed_run",
                type="ui"
                if runtime_result.get("plan", {}).get("kind", self.brief.runtime)
                in {"static-web", "node-web"}
                else "terminal",
                title="隔离运行观察" if self.brief.language == "zh-CN" else "Isolated execution",
                subtitle="本次环境中的实际结果 / OBSERVED IN THIS RUN",
                narration=(
                    "画面展示本次隔离环境的实际运行结果。它只证明该输入在本次环境中的观察，"
                    "不代表生产性能或全部功能均已验证。"
                    if self.brief.language == "zh-CN"
                    else "This is the actual output observed in this isolated run. It is not a production benchmark."
                ),
                code=runtime_result.get("log", "")[:1400],
                media_id=runtime_result.get("media_id"),
                media_kind=runtime_result.get("media_kind", "image"),
                verification="runtime",
            )
            # Rebuild from immutable planning checkpoint so recovery does not duplicate runtime scenes.
            board.scenes = [s for s in board.scenes if s.id != "observed_run"]
            board.scenes.insert(max(1, len(board.scenes) - 1), observed)
            register_runtime_scene(board, observed.id)
            # The runtime scene is real evidence, not an unplanned exception to the contract.
            if self.brief.video_mode == "engineering":
                planned["production_plan"]["shots"] = [
                    shot for shot in planned["production_plan"]["shots"] if shot["scene_id"] != observed.id
                ] + [
                    {
                        "scene_id": observed.id,
                        "visual": "Present the actual isolated runtime recording with its evidence label",
                        "movement": "Preserve capture aspect ratio and hold the verified operation result",
                        "assets": [observed.media_id] if observed.media_id else [],
                    }
                ]
        # Revalidate after runtime insertion, before paying for narration.
        board = StoryboardIR.model_validate(board.model_dump())
        if self.brief.presentation_profile == "creator":
            require_publishable(board, content)

        def voice():
            if self.brief.video_mode == "engineering":
                from .engineering.integration import professional_preflight

                professional_preflight(self.brief, self.settings)
            audio = []
            directory = self.directory / "voice"
            directory.mkdir(exist_ok=True)
            for scene in board.scenes:
                self.guard()
                result = None
                cache_key = voice_cache_key(
                    scene.narration, board.language, self.brief.voice, self.settings, self.brief.voice_spec
                )
                cached = self.db.one(
                    "SELECT * FROM voice_cache WHERE tenant=? AND key=?", (self.tenant, cache_key)
                )
                if cached and not scene.audio_id:
                    scene.audio_id = cached["asset_id"]
                if scene.audio_id and cached and scene.audio_id == cached["asset_id"]:
                    _, existing = self.store.get(self.tenant, scene.audio_id)
                    result = {
                        "path": str(existing),
                        "duration": probe(existing, self.runner),
                        "engine": "reused",
                        "source_engine": cached["engine"] if cached else "unknown",
                    }
                else:
                    scene.audio_id = None
                if (
                    self.brief.video_mode == "engineering"
                    and self.brief.quality_profile == "professional"
                    and result
                    and result.get("source_engine", result["engine"]) not in {"qwen", "edge", "ming"}
                ):
                    # Legacy/unknown audio caches must not satisfy a formal narration request.
                    result = None
                    scene.audio_id = None
                if result and scene.audio_id:
                    timing = self.db.one(
                        "SELECT * FROM audio_timings WHERE tenant=? AND asset_id=?",
                        (self.tenant, scene.audio_id),
                    )
                    if timing:
                        result["words"] = json.loads(timing["payload"])
                        result["alignment_method"] = timing["method"]
                if result is None:
                    result = synthesize(
                        scene,
                        board.language,
                        self.brief.voice,
                        self.settings,
                        directory,
                        self.runner,
                        self.brief.voice_spec,
                    )
                result["scene_id"] = scene.id
                if result.get("path"):
                    from .audio_analysis import waveform

                    result["measurement"] = waveform(result["path"])
                    if result["measurement"]["silent"] and self.brief.quality_profile == "professional":
                        raise EngineeringError("旁白音轨为静音，不能作为正式配音交付")
                    result["audio_id"] = self.asset(result["path"], "audio", "audio/wav", scene.id + ".wav")
                    self.db.execute(
                        "INSERT INTO voice_cache VALUES(?,?,?,?,?) ON CONFLICT(tenant,key) DO UPDATE SET asset_id=excluded.asset_id,duration=excluded.duration,engine=excluded.engine",
                        (
                            self.tenant,
                            cache_key,
                            result["audio_id"],
                            result["duration"],
                            result.get("source_engine", result["engine"]),
                        ),
                    )
                if result.get("audio_id") and result.get("words"):
                    self.db.execute(
                        "INSERT INTO audio_timings VALUES(?,?,?,?) ON CONFLICT(tenant,asset_id) DO UPDATE SET method=excluded.method,payload=excluded.payload",
                        (
                            self.tenant,
                            result["audio_id"],
                            result["alignment_method"],
                            encode(result["words"]),
                        ),
                    )
                audio.append(result)
                self.db.event(self.job, "voice.ready", {"scene_id": scene.id, "engine": result["engine"]})
            return {"audio": audio}

        audio = self.stage("voice", 0.34, voice)["audio"]

        def compile_timeline():
            nonlocal board
            tempo = required_tempo(board, audio, self.brief)
            audio_index = {a["scene_id"]: dict(a) for a in audio}
            methods = []
            alignment_report = {}
            aligned_dir = self.directory / "alignment"
            aligned_dir.mkdir(exist_ok=True)
            for scene in board.scenes:
                a = audio_index[scene.id]
                words = a.get("words", [])
                if a.get("audio_id"):
                    _, path = self.store.get(self.tenant, a["audio_id"])
                    if tempo > 1 and not scene.locked:
                        speed = min(self.brief.max_tempo, tempo * 1.002)
                        target = aligned_dir / (scene.id + "-fitted.wav")
                        self.runner.run(
                            [
                                "ffmpeg",
                                "-v",
                                "error",
                                "-y",
                                "-i",
                                path,
                                "-af",
                                f"atempo={speed}",
                                "-ar",
                                "48000",
                                "-ac",
                                "1",
                                target,
                            ]
                        )
                        a["duration"] = probe(target, self.runner)
                        a["audio_id"] = self.asset(target, "audio", "audio/wav", scene.id + "-fitted.wav")
                        words = [{**w, "start": w["start"] / speed, "end": w["end"] / speed} for w in words]
                        path = target
                    if self.settings.alignment_engine == "stable-ts" or (
                        self.brief.require_alignment and not words
                    ):
                        words = forced_align(
                            path,
                            scene.narration,
                            board.language,
                            a["duration"],
                            self.settings,
                            aligned_dir,
                            self.runner,
                        )
                        a["alignment_method"] = "forced_words"
                    if words:
                        validate_words(words, scene.narration, a["duration"])
                        scene.cues = word_cues(words, board.language)
                        method = a.get("alignment_method", "native_words")
                        self.db.execute(
                            "INSERT INTO audio_timings VALUES(?,?,?,?) ON CONFLICT(tenant,asset_id) DO UPDATE SET method=excluded.method,payload=excluded.payload",
                            (self.tenant, a["audio_id"], method, encode(words)),
                        )
                    else:
                        if self.brief.require_alignment:
                            raise TimelineConflict("需要真实语音对齐，但对齐器未就绪")
                        scene.cues = [
                            Cue.model_validate(c) for c in estimated_cues(scene.narration, a["duration"])
                        ]
                        method = "estimated_sentence"
                    scene.audio_id = a["audio_id"]
                else:
                    if self.brief.require_alignment:
                        raise TimelineConflict("无配音，无法执行真实语音对齐")
                    method = "estimated_sentence"
                    scene.cues = []
                methods.append(method)
                alignment_report[scene.id] = {"method": method, "words": words, "audio_id": a.get("audio_id")}
            board = allocate(board, list(audio_index.values()), self.brief)
            from .motion import compile_motion

            for scene in board.scenes:
                compile_motion(
                    scene,
                    alignment_report[scene.id]["words"],
                    board.fps,
                    allow_estimated=self.brief.quality_profile == "draft",
                )
            for scene in board.scenes:
                if not scene.audio_id:
                    scene.cues = [
                        Cue.model_validate(c) for c in estimated_cues(scene.narration, scene.duration)
                    ]
            board.audio_alignment = methods[0] if len(set(methods)) == 1 else "mixed"
            board = StoryboardIR.model_validate(board.model_dump())
            if self.brief.video_mode == "engineering":
                from ..adapters.native_contract import DesignedScene
                from .engineering.contracts import ProductionPlan

                effective = dict(planned["production_plan"])
                effective["editorial"] = board.editorial.model_dump() if board.editorial else None
                effective["storyboard"] = {
                    "protocol": "1.0",
                    "scenes": [
                        {key: scene.model_dump()[key] for key in DesignedScene.model_fields}
                        for scene in board.scenes
                    ],
                }
                planned["production_plan"] = ProductionPlan.model_validate(effective).model_dump()
            asset = self.store.put(
                self.tenant, encode(alignment_report).encode(), "report", "alignment.json", "application/json"
            )
            return {
                "board": board.model_dump(),
                "fitted_audio": list(audio_index.values()),
                "production_plan": planned.get("production_plan"),
                "revision_fields": {"storyboard": board.model_dump()},
                "outputs": {"alignment": asset["id"]},
            }

        compiled = self.stage("timeline", 0.48, compile_timeline)
        board = StoryboardIR.model_validate(compiled["board"])
        audio = compiled.get("fitted_audio", audio)
        planned["production_plan"] = compiled.get("production_plan", planned.get("production_plan"))
        self.db.event(self.job, "preview.ready", {"mode": "compiled", "frames": board.total_frames})

        def rendering():
            directory = self.directory / "render"
            public = directory / "public"
            public.mkdir(parents=True, exist_ok=True)
            props = board.model_dump()
            props["motion_review_required"] = self.brief.video_mode == "engineering"
            props["voice_spec"] = self.brief.voice_spec.model_dump()
            for scene in props["scenes"]:
                for field, target in [("audio_id", "audio_src"), ("media_id", "media_src")]:
                    if scene.get(field):
                        asset, path = self.store.get(self.tenant, scene[field])
                        extension = {"audio/wav": ".wav", "image/png": ".png", "video/webm": ".webm"}.get(
                            asset["mime"]
                        )
                        if not extension:
                            raise ValueError("Invalid media type")
                        name = asset["id"] + extension
                        shutil.copyfile(path, public / name)
                        scene[target] = name
            font = ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf"
            from .engineering.integration import check_font

            check_font(board, font)
            shutil.copyfile(font, public / "noto.otf")
            (directory / "props.json").write_text(encode(props))
            if self.brief.video_mode == "engineering":
                from .engineering.integration import build_engineering_video

                video, extra_outputs = build_engineering_video(
                    self, board, content, manifest, props, public, planned["production_plan"]
                )
                extra_outputs["production_plan"] = self.store.put(
                    self.tenant,
                    encode(planned["production_plan"]).encode(),
                    "report",
                    "production-plan.json",
                    "application/json",
                )["id"]
                metadata = inspect_video(
                    video, self.runner, board.total_frames, board.width, board.height, board.fps
                )
                return {
                    "metadata": metadata,
                    "outputs": {
                        "video": self.asset(video, "video", "video/mp4", "explainer.mp4"),
                        **extra_outputs,
                    },
                    "engineering": True,
                }
            env = __import__("os").environ.copy()
            if self.settings.chrome_executable:
                env["CHROME_EXECUTABLE"] = self.settings.chrome_executable
            env["RENDER_CONCURRENCY"] = str(self.settings.render_concurrency)
            self.runner.run(
                ["node", ROOT / "packages/video/render.mjs", directory],
                cwd=ROOT,
                timeout=self.settings.render_timeout,
                env=env,
            )
            video = directory / "video.mp4"
            metadata = inspect_video(
                video, self.runner, board.total_frames, board.width, board.height, board.fps
            )
            outputs = {"video": self.asset(video, "video", "video/mp4", "explainer.mp4")}
            cover = directory / "cover.png"
            if cover.exists():
                outputs["cover"] = self.asset(cover, "cover", "image/png", "cover.png")
            if self.brief.presentation_profile == "creator" and "cover" not in outputs:
                raise EditorialError("创作者成片缺少实际渲染的独立封面")
            return {"metadata": metadata, "outputs": outputs}

        rendered = self.stage("render", 0.58, rendering)

        def quality():
            report = inspect(board, content, runtime_result, audio, self.brief.target_seconds)
            report["publication"] = {
                "presentation_profile": board.presentation_profile,
                "editorial_plan": board.editorial.model_dump() if board.editorial else None,
                "findings": publication_findings(board, content),
                "cover_exported": bool(rendered.get("outputs", {}).get("cover")),
            }
            report["findings"].extend(report["publication"]["findings"])
            report["media"] = rendered["metadata"]
            report["video_mode"] = self.brief.video_mode
            report["quality_profile"] = self.brief.quality_profile
            report["voice_engine_requested"] = self.brief.voice
            report["voice_engines_actual"] = sorted({a.get("source_engine", a["engine"]) for a in audio})
            report["engineering_source"] = bool(rendered.get("engineering"))
            aid = self.store.put(
                self.tenant, encode(report).encode(), "report", "quality.json", "application/json"
            )["id"]
            return {"report": report, "revision_fields": {"quality": report}, "outputs": {"quality": aid}}

        report = self.stage("quality", 0.92, quality)["report"]

        def export():
            def stamp(value):
                ms = max(0, round(value * 1000))
                return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"

            script = f"# {board.title}\n\n"
            captions, index = [], 1
            for scene in board.scenes:
                script += f"## {scene.title}\n\n{scene.narration}\n\n"
                for cue in scene.cues:
                    start = scene.start_frame / board.fps
                    captions.append(
                        f"{index}\n{stamp(start + cue.start)} --> {stamp(start + cue.end)}\n{cue.text}\n"
                    )
                    index += 1
            script_id = self.store.put(self.tenant, script.encode(), "script", "script.md", "text/markdown")[
                "id"
            ]
            caption_id = self.store.put(
                self.tenant, "\n".join(captions).encode(), "subtitle", "subtitles.srt", "text/plain"
            )["id"]
            package = self.directory / "project.zip"
            narration_id = None
            audio_analysis_id = None
            if any(scene.audio_id for scene in board.scenes):
                # Mix at absolute scene positions, preserving deliberate visual holds.
                args = ["ffmpeg", "-v", "error", "-y"]
                filters, streams = [], []
                for scene in board.scenes:
                    if scene.audio_id:
                        _, path = self.store.get(self.tenant, scene.audio_id)
                        args.extend(["-i", path])
                        i = len(streams)
                        delay = round(scene.start_frame / board.fps * 1000)
                        filters.append(f"[{i}:a]adelay={delay}:all=1[a{i}]")
                        streams.append(f"[a{i}]")
                duration = board.total_frames / board.fps
                filters.append(
                    "".join(streams)
                    + f"amix=inputs={len(streams)}:normalize=0,apad,atrim=duration={duration}[out]"
                )
                narration_path = self.directory / "narration.wav"
                self.runner.run(
                    args
                    + [
                        "-filter_complex",
                        ";".join(filters),
                        "-map",
                        "[out]",
                        "-ar",
                        "48000",
                        "-ac",
                        "1",
                        narration_path,
                    ],
                    timeout=120,
                )
                narration_id = self.asset(narration_path, "audio", "audio/wav", "narration.wav")
                from .audio_analysis import waveform

                measured = waveform(narration_path)
                audio_analysis_id = self.store.put(
                    self.tenant,
                    encode(measured).encode(),
                    "report",
                    "audio-analysis.json",
                    "application/json",
                )["id"]
            with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("project.json", encode(board.model_dump()))
                z.writestr("content.json", encode(content.model_dump()))
                z.writestr("quality.json", encode(report))
                for role, name in [
                    ("cover", "cover.png"),
                    ("production_plan", "production-plan.json"),
                    ("visual_review", "visual-review.json"),
                    ("authoring_journal", "authoring-journal.json"),
                    ("engineering_project", "remotion-project.zip"),
                ]:
                    item = self.db.one(
                        "SELECT asset_id FROM outputs WHERE revision_id=? AND role=?",
                        (self.revision["id"], role),
                    )
                    if item:
                        _, path = self.store.get(self.tenant, item["asset_id"])
                        z.write(path, name)
                agent_output = self.db.one(
                    "SELECT asset_id FROM outputs WHERE revision_id=? AND role='agent'",
                    (self.revision["id"],),
                )
                if agent_output:
                    _, path = self.store.get(self.tenant, agent_output["asset_id"])
                    z.write(path, "agent-run.json")
                z.writestr("script.md", script)
                z.writestr("subtitles.srt", "\n".join(captions))
                alignment_id = compiled.get("outputs", {}).get("alignment")
                if alignment_id:
                    _, path = self.store.get(self.tenant, alignment_id)
                    z.write(path, "alignment.json")
                if narration_id:
                    z.write(narration_path, "narration.wav")
                z.writestr(
                    "README.txt",
                    "Editable Explainer Studio IR v1.0. Source archive and secrets are excluded.\n"
                    "Alignment method is recorded in quality.json. See alignment report in the application. Media paths are in manifest.json.\n",
                )
                manifest_out = {}
                for scene in board.scenes:
                    for aid in [scene.audio_id, scene.media_id]:
                        if aid and aid not in manifest_out:
                            a, path = self.store.get(self.tenant, aid)
                            target = "media/" + a["id"] + "-" + a["filename"]
                            z.write(path, target)
                            manifest_out[aid] = {"path": target, "sha256": a["hash"], "mime": a["mime"]}
                z.writestr("manifest.json", encode(manifest_out))
            package_id = self.asset(package, "package", "application/zip", "editable-project.zip")
            outputs = {"script": script_id, "subtitles": caption_id, "package": package_id}
            if narration_id:
                outputs["narration"] = narration_id
            if audio_analysis_id:
                outputs["audio_analysis"] = audio_analysis_id
            return {"outputs": outputs}

        self.stage("export", 0.98, export)
        errors = any(f["severity"] == "error" for f in report["findings"])
        no_voice = any(a["engine"] == "none" for a in audio) and self.brief.voice != "none"
        runtime_missing = self.brief.require_real_demo and runtime_result.get("state") != "observed"
        self.db.finish(self.job, "PARTIAL" if errors or no_voice or runtime_missing else "SUCCEEDED")
