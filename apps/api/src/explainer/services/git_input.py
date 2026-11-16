"""Public HTTPS Git snapshot import: no credentials, hooks, submodules or checkout execution."""

import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from .process import Runner


def git_snapshot(url, ref, settings):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in settings.git_allowed_hosts.split(",")
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in {None, 443}
    ):
        raise ValueError("Only approved public HTTPS Git repositories are allowed")
    if not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?/?", parsed.path):
        raise ValueError("Invalid repository path")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./-]{0,160}", ref) or ".." in ref:
        raise ValueError("Invalid Git ref")
    with tempfile.TemporaryDirectory(dir=settings.data_dir, prefix="git-") as temporary:
        directory = Path(temporary)

        def limit():
            total = sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())
            if total > settings.max_expanded_bytes:
                raise ValueError("Git snapshot exceeds disk budget")

        runner = Runner(limit)
        env = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "HOME": str(directory),
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_LFS_SKIP_SMUDGE": "1",
        }
        git = [
            "git",
            "-c",
            "credential.helper=",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "protocol.file.allow=never",
            "-c",
            "protocol.ext.allow=never",
            "-c",
            "http.followRedirects=false",
        ]
        runner.run(git + ["init", "--quiet", "repo"], cwd=directory, env=env)
        repo = directory / "repo"
        runner.run(git + ["remote", "add", "origin", url], cwd=repo, env=env)
        runner.run(git + ["fetch", "--depth=1", "--no-tags", "origin", ref], cwd=repo, env=env, timeout=90)
        commit = runner.run(git + ["rev-parse", "FETCH_HEAD"], cwd=repo, env=env).strip()
        if not re.fullmatch("[0-9a-f]{40,64}", commit):
            raise ValueError("Invalid commit hash")
        destination = directory / "snapshot.zip"
        runner.run(
            git + ["archive", "--format=zip", "--output=" + str(destination), commit], cwd=repo, env=env
        )
        if destination.stat().st_size > settings.max_upload_bytes:
            raise ValueError("Archive too large")
        return destination.read_bytes(), {"kind": "git", "url": url, "ref": ref, "commit": commit}
