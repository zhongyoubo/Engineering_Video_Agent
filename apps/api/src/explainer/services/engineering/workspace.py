import hashlib
import json
from pathlib import PurePosixPath
import shutil
import zipfile

from ...config import ROOT


class EngineeringError(RuntimeError):
    pass


def source_path(value):
    path = PurePosixPath(value)
    if (
        str(path) != value
        or "\\" in value
        or ":" in value
        or ".." in path.parts
        or path.is_absolute()
        or not path.parts
        or path.parts[0] != "src"
        or path.name
        in {
            "index.tsx",
            "Root.tsx",
            "contracts.ts",
            "env.d.ts",
            "motion-kit.tsx",
            "theme.tsx",
            "code-view.tsx",
            "mechanism-kit.tsx",
            "presentation.tsx",
            "scene-objects.tsx",
            "semantic-kit.tsx",
            "semantic-types.ts",
            "review-plan.ts",
        }
        or any(p.startswith(".") or p == "node_modules" for p in path.parts)
        or path.suffix not in {".tsx", ".ts", ".css"}
    ):
        raise EngineeringError("Generated edits are restricted to src visual components")
    return path


def atomic_json(path, value):
    temporary = path.with_suffix(".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temporary.replace(path)


class Workspace:
    def __init__(self, directory):
        self.root = directory
        self.project = directory / "project"
        self.state_path = directory / "state.json"
        directory.mkdir(parents=True, exist_ok=True)
        self.state = (
            json.loads(self.state_path.read_text())
            if self.state_path.exists()
            else {
                "protocol": "3.0",
                "iteration": 0,
                "files": {},
                "journal": [],
                "build_hash": None,
                "preview_hash": None,
                "review_hash": None,
                "review": None,
                "frames": [],
                "finished": False,
            }
        )

    def prepare(self, props, media_directory):
        shutil.copytree(
            ROOT / "packages/engineering-template",
            self.project,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("node_modules", "output"),
        )
        shutil.copytree(media_directory, self.project / "public", dirs_exist_ok=True)
        shutil.copyfile(ROOT / "assets/fonts/LICENSE.txt", self.project / "public/FONT-LICENSE.txt")
        from ..assets.registry import restore_assets

        props = {**props, "generated_assets": restore_assets(self)}
        from ..render_plan import build_render_plan

        props["render_plan"] = build_render_plan(props, self.project / "public")
        atomic_json(self.project / "props.json", props)
        for name, text in self.state["files"].items():
            target = self.project / source_path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)

    def fingerprint(self):
        h = hashlib.sha256()
        for path in sorted(
            p for p in self.project.rglob("*") if p.is_file() and "node_modules" not in p.parts
        ):
            h.update(str(path.relative_to(self.project)).encode())
            h.update(b"\0")
            h.update(path.read_bytes())
        return h.hexdigest()

    def edit(self, edits):
        if sum(len(e.content.encode()) for e in edits) > 400000:
            raise EngineeringError("Source edit size exceeds budget")
        # Validate the entire patch before applying any edit.
        for edit in edits:
            source_path(edit.path)
            if "\ufffd" in edit.content or "\x00" in edit.content:
                raise EngineeringError("Invalid source text encoding")
        candidate = {**self.state["files"], **{e.path: e.content for e in edits}}
        if sum(len(v.encode()) for v in candidate.values()) > 1000000:
            raise EngineeringError("Project source exceeds budget")
        for edit in edits:
            target = self.project / source_path(edit.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(edit.content)
        self.state["files"] = candidate
        self.invalidate()

    def invalidate(self):
        for key in ["build_hash", "preview_hash", "review_hash"]:
            self.state[key] = None
        self.state["frames"], self.state["review"], self.state["finished"] = [], None, False
        self.state["clips"], self.state["motion_frames"] = [], []

    def record(self, kind, data):
        self.state["journal"].append({"step": self.state["iteration"], "kind": kind, "data": data})
        self.state["iteration"] += 1
        atomic_json(self.state_path, self.state)

    def export(self, destination, plan):
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(self.project.rglob("*")):
                if path.is_file() and "node_modules" not in path.parts:
                    archive.write(path, str(path.relative_to(self.project)))
            archive.writestr(
                "generated-assets.json",
                json.dumps(
                    {
                        k: {f: v for f, v in r.items() if f not in {"svg", "image_png", "preview_png"}}
                        for k, r in self.state.get("generated_assets", {}).items()
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            archive.writestr("production-plan.json", json.dumps(plan, ensure_ascii=False, indent=2))
            archive.writestr(
                "authoring-journal.json", json.dumps(self.state["journal"], ensure_ascii=False, indent=2)
            )
            archive.writestr(
                "visual-review.json", json.dumps(self.state["review"], ensure_ascii=False, indent=2)
            )
