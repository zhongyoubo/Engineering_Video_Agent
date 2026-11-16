import ast
import hashlib
import io
import json
import re
import stat
import zipfile
from collections import Counter
from pathlib import PurePosixPath

from ..domain import Claim, ContentIR, Evidence

TEXT_EXT = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".vue",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".h",
    ".cpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".html",
    ".css",
    ".sql",
    ".sh",
    ".ipynb",
}
LANGUAGES = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".vue": "Vue",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".swift": "Swift",
    ".kt": "Kotlin",
}
SKIP = {"node_modules", ".git", ".venv", "venv", "__pycache__", "vendor", "dist", ".next", "build"}
BINARY_EXT = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".mp4",
    ".webm",
    ".mp3",
    ".wav",
    ".zip",
    ".gz",
    ".pdf",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".exe",
    ".dll",
    ".so",
    ".a",
    ".o",
    ".wasm",
    ".pyc",
}
SECRET = re.compile(
    r"((?:['\"]?(?:api[_-]?key|secret|password|token)['\"]?)\s*[:=]\s*)"
    r"(?:(['\"])([^\r\n]*?)\2|([^\s,;}]+))",
    re.I,
)


class InvalidArchive(ValueError):
    pass


def redact(text):
    text = SECRET.sub(lambda m: m.group(1) + '"[REDACTED]"', text)
    return re.sub(
        r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----",
        "[PRIVATE KEY REMOVED]",
        text,
        flags=re.S,
    )


def read_archive(data, settings):
    if len(data) > settings.max_upload_bytes:
        raise InvalidArchive("归档超过大小限制")
    files, skipped, total = {}, 0, 0
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        if len(archive.infolist()) > settings.max_files:
            raise InvalidArchive("归档文件数超过限制")
        normalized = set()
        for item in archive.infolist():
            name = item.filename
            path = PurePosixPath(name)
            mode = item.external_attr >> 16
            if (
                "\\" in name
                or "\x00" in name
                or path.is_absolute()
                or ".." in path.parts
                or any(":" in part for part in path.parts)
                or stat.S_ISLNK(mode)
                or (stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR})
            ):
                raise InvalidArchive("归档包含不安全路径、链接或特殊文件")
            canonical = str(path)
            if canonical in normalized:
                raise InvalidArchive("归档包含重复路径")
            normalized.add(canonical)
            total += item.file_size
            if total > settings.max_expanded_bytes:
                raise InvalidArchive("展开大小超过限制")
            if item.file_size > 1024 * 1024 and item.file_size / max(item.compress_size, 1) > 250:
                raise InvalidArchive("压缩比异常")
            if item.flag_bits & 1:
                raise InvalidArchive("不支持加密归档")
            if item.is_dir():
                continue
            sensitive = (
                path.name.startswith(".env")
                or path.name in {".npmrc", ".pypirc", ".netrc"}
                or ".ssh" in path.parts
                or any(x in path.name.lower() for x in ["id_rsa", "credentials", "private_key"])
            )
            if sensitive or any(p in SKIP for p in path.parts) or path.suffix.lower() in BINARY_EXT:
                skipped += 1
                continue
            if item.file_size > 512 * 1024:
                skipped += 1
                continue
            content = archive.read(item)
            decoded = content.decode("utf-8", errors="replace")
            if b"\x00" in content or decoded.count("\ufffd") > max(2, len(decoded) // 100):
                skipped += 1
                continue
            files[name] = {
                "text": redact(decoded),
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
    except (zipfile.BadZipFile, RuntimeError, OSError, NotImplementedError) as exc:
        raise InvalidArchive("ZIP 损坏或编码不支持") from exc
    if not files:
        raise InvalidArchive("未找到可解析的源码或文档")
    return {
        "files": files,
        "skipped": skipped,
        "expanded_bytes": total,
        "archive_hash": hashlib.sha256(data).hexdigest(),
    }


def analyze(brief, manifest=None):
    evidence, claims, warnings = [], [], []
    if not manifest:
        claims = [Claim(id="c_prompt", statement=brief.prompt, status="user_provided")]
        return ContentIR(
            title=brief.title,
            kind="prompt",
            summary=brief.prompt,
            claims=claims,
            evidence=[],
            languages=[],
            modules=[],
            files_count=0,
            warnings=["内容来自用户提示词；没有源码运行证据。"],
        )
    files = manifest["files"]
    counts = Counter(
        LANGUAGES[PurePosixPath(n).suffix] for n in files if PurePosixPath(n).suffix in LANGUAGES
    )
    paths = sorted(
        files,
        key=lambda n: (
            0
            if PurePosixPath(n).name.lower().startswith("readme")
            else 1
            if PurePosixPath(n).name in {"package.json", "pyproject.toml"}
            else 2,
            n,
        ),
    )
    for index, name in enumerate(paths[:50]):
        item = files[name]
        text, suffix = item["text"], PurePosixPath(name).suffix
        eid = f"e{index + 1}"
        evidence.append(
            Evidence(id=eid, path=name, kind="source", excerpt=text[:2600], sha256=item["sha256"])
        )
        statement = ""
        if PurePosixPath(name).name.lower().startswith("readme"):
            plain = re.sub(r"[`#>*]", "", text).strip()
            statement = plain[:350]
        elif suffix == ".py":
            try:
                tree = ast.parse(text)
                names = [
                    n.name
                    for n in ast.walk(tree)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                ]
                if names:
                    statement = f"{name} 定义了 " + "、".join(names[:7])
            except SyntaxError:
                warnings.append(f"{name} 无法解析为 Python AST，保留静态文本。")
        elif PurePosixPath(name).name == "package.json":
            try:
                package = json.loads(text)
                deps = list(package.get("dependencies", {}))[:10]
                statement = f"{name} 声明依赖：" + "、".join(deps) if deps else f"{name} 包含项目配置。"
            except (ValueError, AttributeError, TypeError):
                warnings.append(f"{name} 配置无法解析。")
        elif suffix in LANGUAGES:
            names = re.findall(r"(?:function|class|func|fn)\s+([A-Za-z_][\w]*)", text)[:7]
            if names:
                statement = f"{name} 包含符号：" + "、".join(names)
        if statement:
            claims.append(
                Claim(id=f"c{index + 1}", statement=statement, status="observed_static", evidence_ids=[eid])
            )
    if not claims:
        claims.append(
            Claim(
                id="c_files",
                statement=f"项目包含 {len(files)} 个可解析文本文件。",
                status="observed_static",
                evidence_ids=[e.id for e in evidence[:3]],
            )
        )
    modules = sorted(
        {
            PurePosixPath(n).parts[0] if len(PurePosixPath(n).parts) > 1 else PurePosixPath(n).stem
            for n in files
        }
    )[:12]
    return ContentIR(
        title=brief.title,
        kind="source",
        summary=claims[0].statement[:500],
        claims=claims,
        evidence=evidence,
        languages=[x for x, _ in counts.most_common()],
        modules=modules,
        files_count=len(files),
        warnings=warnings
        + [
            "静态分析不等同于功能或性能验证。",
            f"跳过 {manifest['skipped']} 个依赖、敏感或非文本文件；未将原始源码发送给外部模型。",
        ],
    )
