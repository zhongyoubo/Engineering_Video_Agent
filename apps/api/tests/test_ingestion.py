import io
import stat
import zipfile

import pytest

from explainer.domain import Brief
from explainer.services.ingestion import InvalidArchive, analyze, read_archive


def archive(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, body in files.items():
            z.writestr(name, body)
    return out.getvalue()


@pytest.mark.parametrize(
    "name", ["../outside.py", "/outside.py", "dir/../../bad.py", "C:/a.py", "dir\\bad.py"]
)
def test_reject_paths(settings, name):
    with pytest.raises(InvalidArchive):
        read_archive(archive({name: "print('x')"}), settings)


def test_symlink(settings):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        info = zipfile.ZipInfo("link.py")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(info, "/etc/passwd")
    with pytest.raises(InvalidArchive):
        read_archive(out.getvalue(), settings)


def test_duplicate(settings):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("x.py", "one")
        with pytest.warns(UserWarning):
            z.writestr("x.py", "two")
    with pytest.raises(InvalidArchive):
        read_archive(out.getvalue(), settings)


def test_redaction_and_ast(settings):
    data = archive(
        {
            ".env": "API_KEY=abcdef123456",
            "main.py": "api_key='abcdef123456'\ndef sync_files():\n pass\n",
            "README.md": "# Sync\nCopies changed files.",
            "node_modules/x.js": "ignored",
        }
    )
    result = read_archive(data, settings)
    assert ".env" not in result["files"]
    assert "abcdef123456" not in str(result)
    content = analyze(Brief(title="Sync", input_id="test"), result)
    assert content.languages == ["Python"]
    assert any("sync_files" in c.statement for c in content.claims)
    assert all(c.status == "observed_static" for c in content.claims)
    assert result["skipped"] == 2


def test_limits(settings):
    settings.max_expanded_bytes = 5
    with pytest.raises(InvalidArchive):
        read_archive(archive({"x.py": "abcdef"}), settings)
