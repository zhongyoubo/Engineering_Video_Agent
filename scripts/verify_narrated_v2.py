"""Real Qwen -> forced alignment -> exact-length Remotion video integration."""

import json, os, subprocess, sys, time, urllib.request, shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0, str(root / "apps/api/src"))
from explainer.config import Settings
from explainer.db import Database
from explainer.domain import Brief, StoryboardIR
from explainer.api import insert_revision
from explainer.worker import run_once
from explainer.storage import Storage

out = root / ".verify-narrated"
out.mkdir(exist_ok=True)
env = os.environ.copy()
env.update(
    QWEN_BASE_MODEL=str(root / ".models/qwen-base"),
    QWEN_REFERENCE_WAV=str(root / "assets/voices/professional-male/reference.wav"),
    QWEN_REFERENCE_TEXT=str(root / "assets/voices/professional-male/reference.txt"),
    QWEN_SERVICE_KEY="integration-only-speech-key-123456",
    QWEN_CPU_THREADS="4",
)
log = (out / "speech.log").open("w")
p = subprocess.Popen(
    [
        str(root / ".speech-venv/bin/python"),
        "-m",
        "uvicorn",
        "services.qwen.server:app",
        "--host",
        "127.0.0.1",
        "--port",
        "7862",
    ],
    env=env,
    stdout=log,
    stderr=log,
)
try:
    for _ in range(120):
        try:
            urllib.request.urlopen("http://127.0.0.1:7862/health", timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    settings = Settings(
        data_dir=out / "data",
        api_token="integration-only-api-key-123456",
        tts_engine="qwen",
        tts_url="http://127.0.0.1:7862",
        tts_key=env["QWEN_SERVICE_KEY"],
        alignment_engine="stable-ts",
        alignment_python=str(root / ".speech-venv/bin/python"),
        alignment_model=str(root / ".models/tiny.pt"),
        chrome_executable=os.environ.get("CHROME_EXECUTABLE", ""),
    ).prepare()
    db = Database(settings.data_dir)
    db.execute(
        "INSERT OR IGNORE INTO projects VALUES(?,?,?,?)",
        ("demo", "local", "Narrated integration", time.time()),
    )
    brief = Brief(
        title="从内容到讲解视频",
        prompt="将源码或提示词变成讲解视频。",
        target_seconds=20,
        duration_mode="exact",
        voice="qwen",
        require_alignment=True,
    )
    scenes = [
        (
            "title",
            "从内容出发，让理解发生。",
            "输入项目源码或提示词，开始创作讲解视频。",
            ["项目源码", "创作提示词"],
        ),
        (
            "flow",
            "从理解，到生动讲解",
            "系统梳理内容，编排分镜，生成旁白和动画。",
            ["内容理解", "分镜编排", "配音对齐", "动画渲染"],
        ),
        (
            "summary",
            "让复杂，一目了然。",
            "脚本、字幕和工程可以继续编辑。",
            ["可编辑", "可追溯", "可导出"],
        ),
    ]
    board = StoryboardIR(
        title=brief.title,
        language="zh-CN",
        accent="blue",
        audience="general",
        scenes=[
            dict(
                id=f"s{i}",
                type=t,
                title=title,
                narration=n,
                bullets=b,
                claim_ids=["c_prompt"],
                verification="user_provided",
                duration=6,
            )
            for i, (t, title, n, b) in enumerate(scenes)
        ],
    )
    revision = insert_revision(db, settings, "local", "demo", brief, storyboard=board)
    run_once(settings, db, job_id=revision["job_id"])
    job = db.one("SELECT * FROM jobs WHERE id=?", (revision["job_id"],))
    assert job["state"] == "SUCCEEDED", job
    store = Storage(settings, db)
    dest = out / "deliverables"
    dest.mkdir(exist_ok=True)
    for output in db.all(
        "SELECT * FROM outputs WHERE revision_id=?", (revision["revision_id"],)
    ):
        asset, path = store.get("local", output["asset_id"])
        shutil.copyfile(path, dest / asset["filename"])
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(dest / "explainer.mp4"), "-f", "null", "-"],
        check=True,
    )
    metadata = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-of",
                "json",
                str(dest / "explainer.mp4"),
            ]
        )
    )
    video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
    assert int(video["nb_frames"]) == 600
    alignment = json.loads((dest / "alignment.json").read_text())
    assert all(a["method"] == "forced_words" for a in alignment.values())
    report = dict(
        result="passed",
        actual_qwen=True,
        forced_alignment=True,
        exact_frames=600,
        seconds=20,
        full_decode=True,
        scenes=len(alignment),
        model_revision=json.loads((root / ".models/qwen-base/origin.json").read_text()),
    )
    (out / "verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)
finally:
    p.terminate()
    p.wait(timeout=30)
    log.close()
