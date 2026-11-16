import copy
import importlib.util
import json
from pathlib import Path
import sys
import time

import pytest

from explainer.adapters.native_agent import native_plan, NativeAgentError, safe_source
from explainer.adapters.native_contract import strict_schema, validate_design
from explainer.domain import Brief, Diagram
from explainer.services.ingestion import analyze
from explainer.services.process import Runner, ProcessError

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("native_driver", ROOT / "services/native_agent/driver.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def design():
    return {
        "protocol": "1.0",
        "scenes": [
            {
                "id": "explain",
                "type": "flow",
                "title": "From request to response",
                "subtitle": "",
                "narration": "A request moves through the service and produces a response.",
                "bullets": ["Request", "Service", "Response"],
                "code": "",
                "claim_ids": ["c_prompt"],
                "evidence_ids": [],
                "duration": 20,
                "diagram": {
                    "nodes": [
                        {
                            "id": "request",
                            "label": "Request",
                            "detail": "A clear input",
                            "x": 160,
                            "y": 200,
                            "reveal": 0.05,
                            "emphasis": "none",
                        },
                        {
                            "id": "service",
                            "label": "Service",
                            "detail": "Defined behavior",
                            "x": 740,
                            "y": 200,
                            "reveal": 0.15,
                            "emphasis": "pulse",
                        },
                    ],
                    "edges": [{"source": "request", "target": "service", "label": "Process", "reveal": 0.2}],
                },
            }
        ],
    }


def task(provider="codex", timeout=3):
    return {
        "provider": provider,
        "model": "",
        "max_turns": 3,
        "budget_usd": 0.1,
        "timeout": timeout,
        "brief": {"title": "Test"},
        "content": {},
    }


def test_native_output_rejects_fake_evidence_and_asset_injection():
    brief = Brief(title="Test", prompt="Test", agent_engine="codex")
    content = analyze(brief)
    result = validate_design(design(), content, brief)
    assert result.scenes[0].diagram and result.scenes[0].verification == "concept"
    bad = design()
    bad["scenes"][0]["claim_ids"] = ["invented"]
    with pytest.raises(ValueError):
        validate_design(bad, content, brief)
    bad = design()
    bad["scenes"][0]["media_id"] = "other-tenant"
    with pytest.raises(ValueError):
        validate_design(bad, content, brief)
    bad = design()
    bad["scenes"][0]["verification"] = "runtime"
    with pytest.raises(ValueError):
        validate_design(bad, content, brief)


def test_diagram_rejects_invalid_edges_and_duplicate_nodes():
    graph = design()["scenes"][0]["diagram"]
    graph["edges"][0]["target"] = "missing"
    with pytest.raises(ValueError):
        Diagram.model_validate(graph)
    graph["edges"] = []
    graph["nodes"].append(copy.deepcopy(graph["nodes"][0]))
    with pytest.raises(ValueError):
        Diagram.model_validate(graph)


def test_strict_schema_for_both_native_providers():
    def check(value):
        if isinstance(value, dict):
            if value.get("type") == "object":
                assert value["additionalProperties"] is False
                assert set(value["required"]) == set(value["properties"])
            for child in value.values():
                check(child)
        if isinstance(value, list):
            for child in value:
                check(child)

    check(strict_schema())


def test_safe_source_does_not_load_repository_hooks():
    assert safe_source("src/app.ts")
    for name in [
        ".claude/settings.json",
        ".codex/config.toml",
        "nested/AGENTS.md",
        ".env.production",
        ".mcp.json",
    ]:
        assert not safe_source(name)
    for name in ["../bad", "/tmp/bad", "C:/bad", "a\\b"]:
        with pytest.raises(ValueError):
            safe_source(name)


def test_missing_native_dependencies_fail_without_template_fallback(settings, tmp_path):
    brief = Brief(title="Native", prompt="Explain", agent_engine="codex")
    with pytest.raises(NativeAgentError, match="没有回退"):
        native_plan(analyze(brief), brief, settings, None, tmp_path / "native", Runner(), lambda *args: None)


def test_native_cli_commands_never_bypass_permissions(tmp_path):
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps(strict_schema()))
    codex = driver.command(task(), schema, tmp_path / "result.json")
    assert "--sandbox" in codex and codex[codex.index("--sandbox") + 1] == "read-only"
    assert "--ephemeral" in codex and "--output-schema" in codex
    claude = driver.command(task("claude-code"), schema, tmp_path / "result.json")
    assert "--bare" in claude and "--strict-mcp-config" in claude
    assert claude[claude.index("--tools") + 1] == "Read,Glob,Grep"
    assert not any("bypass" in part or "dangerously" in part for part in codex + claude)


@pytest.mark.parametrize("provider", ["codex", "claude-code"])
def test_actual_subprocess_protocol_with_authored_fixture(provider, tmp_path, capsys):
    output = tmp_path / "out.json"
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps(strict_schema()))
    fixture = tmp_path / "fixture.py"
    fixture.write_text(
        "import sys,json\nfrom pathlib import Path\n"
        "request=sys.stdin.read()\n"
        f"design={design()!r}\n"
        f"Path({str(output)!r}).write_text(json.dumps(design))\n"
        'print(json.dumps({"type":"item.started","item":{"type":"reasoning","text":"SECRET_RAW_THOUGHT"}}),flush=True)\n'
        'print(json.dumps({"type":"result","subtype":"success","structured_output":design}),flush=True)\n'
    )
    result = driver.run_cli(
        task(provider), schema, output, tmp_path, executable_command=[sys.executable, str(fixture)]
    )
    assert result == design()
    assert "SECRET_RAW_THOUGHT" not in capsys.readouterr().out


def test_driver_rejects_failure_even_with_valid_file(tmp_path):
    output = tmp_path / "out.json"
    output.write_text(json.dumps(design()))
    fixture = tmp_path / "bad.py"
    fixture.write_text('import sys\nsys.stdin.read()\nprint(\'{"type":"turn.failed"}\')\n')
    with pytest.raises(RuntimeError, match="failed"):
        driver.run_cli(
            task(), tmp_path / "schema", output, tmp_path, executable_command=[sys.executable, str(fixture)]
        )


def test_driver_timeout_terminates_subprocess(tmp_path):
    fixture = tmp_path / "slow.py"
    fixture.write_text("import sys,time\nsys.stdin.read()\ntime.sleep(30)\n")
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="timeout"):
        driver.run_cli(
            task(timeout=0.2),
            tmp_path / "schema",
            tmp_path / "out",
            tmp_path,
            executable_command=[sys.executable, str(fixture)],
        )
    assert time.monotonic() - started < 3


def test_pipeline_native_mode_is_connected_and_exported(settings, db, monkeypatch):
    from explainer.api import insert_revision
    from explainer.worker import run_once

    calls = []

    def fake(content, brief, *args):
        calls.append(brief.agent_engine)
        return validate_design(design(), content, brief), {
            "provider": brief.agent_engine,
            "test_fixture": True,
        }

    monkeypatch.setattr("explainer.services.pipeline.native_plan", fake)
    db.execute("INSERT INTO projects VALUES(?,?,?,?)", ("native", "local", "Native", time.time()))
    brief = Brief(title="Test", prompt="Test", mode="storyboard", agent_engine="claude-code")
    result = insert_revision(db, settings, "local", "native", brief)
    run_once(settings, db, job_id=result["job_id"])
    assert calls == ["claude-code"]
    assert db.one("SELECT state FROM jobs WHERE id=?", (result["job_id"],))["state"] == "SUCCEEDED"
    assert db.one("SELECT * FROM outputs WHERE revision_id=? AND role='agent'", (result["revision_id"],))


def test_native_capabilities_do_not_expose_keys(client, settings, headers):
    settings.codex_api_key = "DO_NOT_EXPOSE_THIS_KEY"
    response = client.get("/api/v1/capabilities", headers=headers)
    assert response.status_code == 200 and "DO_NOT_EXPOSE_THIS_KEY" not in response.text
    assert {x["provider"] for x in response.json()["native_agents"]} == {"codex", "claude-code"}


def test_process_callback_failure_fails_job_instead_of_losing_events():
    def reject(line):
        raise ValueError("bad event")

    with pytest.raises(ProcessError, match="event handler"):
        Runner().run([sys.executable, "-c", 'print("line",flush=True)'], on_line=reject)


def test_single_scene_native_edit_preserves_locks_and_audio():
    from explainer.adapters.native_contract import merge_scene_design
    from explainer.domain import Cue

    brief = Brief(title="Test", prompt="Test", agent_engine="codex")
    board = validate_design(design(), analyze(brief), brief)
    board.scenes[0].audio_id = "existing-audio"
    board.scenes[0].cues = [Cue(start=0, end=2, text="Existing caption")]
    other = board.scenes[0].model_copy(deep=True)
    other.id, other.locked = "locked-scene", True
    board.scenes.append(other)
    changed = validate_design(design(), analyze(brief), brief)
    changed.scenes[0].title = "A clearer title"
    merged = merge_scene_design(board, changed, "explain")
    assert merged.scenes[1].model_dump() == board.scenes[1].model_dump()
    assert merged.scenes[0].audio_id == "existing-audio"
    changed.scenes[0].narration = "A newly recorded narration."
    assert merge_scene_design(board, changed, "explain").scenes[0].audio_id is None
    board.scenes[0].locked = True
    with pytest.raises(ValueError):
        merge_scene_design(board, changed, "explain")


def test_native_change_endpoint_queues_job_and_clears_instruction_after_commit(
    client, settings, db, headers, monkeypatch
):
    from explainer.api import insert_revision
    from explainer.adapters.native_contract import merge_scene_design
    from explainer.worker import run_once

    brief = Brief(title="Test", prompt="Test", agent_engine="codex", mode="storyboard")
    board = validate_design(design(), analyze(brief), brief)
    db.execute("INSERT INTO projects VALUES(?,?,?,?)", ("edit-native", "local", "Edit", time.time()))
    result = insert_revision(db, settings, "local", "edit-native", brief, storyboard=board)
    run_once(settings, db, job_id=result["job_id"])

    def revise(content, brief, *args, existing_board=None):
        assert brief.agent_change.instruction == "Make the title clearer"
        proposed = validate_design(design(), content, brief)
        proposed.scenes[0].title = "A clearer title"
        return merge_scene_design(existing_board, proposed, brief.agent_change.scene_id), {
            "test_fixture": True
        }

    monkeypatch.setattr("explainer.services.pipeline.native_plan", revise)
    response = client.post(
        "/api/v1/revisions/" + result["revision_id"] + "/changes",
        headers=headers,
        json={"scene_id": "explain", "instruction": "Make the title clearer", "auto_render": False},
    )
    assert response.status_code == 202
    run_once(settings, db, job_id=response.json()["job_id"])
    revised = client.get("/api/v1/revisions/" + response.json()["revision_id"], headers=headers).json()
    assert revised["brief"]["agent_change"] is None
    assert revised["storyboard"]["scenes"][0]["title"] == "A clearer title"


def test_terminal_sse_drains_more_than_one_page(client, settings, db, headers):
    from explainer.api import insert_revision

    brief = Brief(title="Events", prompt="Events")
    db.execute("INSERT INTO projects VALUES(?,?,?,?)", ("sse", "local", "Events", time.time()))
    r = insert_revision(db, settings, "local", "sse", brief)
    job = db.one("SELECT * FROM jobs WHERE id=?", (r["job_id"],))
    for i in range(205):
        db.event(job, "agent.progress", {"step": str(i)})
    db.execute("UPDATE jobs SET state='SUCCEEDED' WHERE id=?", (r["job_id"],))
    response = client.get("/api/v1/jobs/" + r["job_id"] + "/events", headers=headers)
    assert response.text.count("agent.progress") == 205
    assert "event: done" in response.text


def test_container_invocation_redacts_keys_and_cleans_up(settings, tmp_path, monkeypatch):
    settings.native_agent_providers = "codex"
    settings.codex_api_key = "NATIVE_PROVIDER_SECRET"
    monkeypatch.setattr("explainer.adapters.native_agent.shutil.which", lambda name: "/usr/bin/docker")
    removed = []
    monkeypatch.setattr(
        "explainer.adapters.native_agent.subprocess.run", lambda args, **kwargs: removed.append(args)
    )

    class FixtureRunner:
        def guard(self):
            pass

        def run(self, args, **kwargs):
            assert "NATIVE_PROVIDER_SECRET" not in repr(args)
            assert kwargs["env"]["CODEX_API_KEY"] == "NATIVE_PROVIDER_SECRET"
            assert "--read-only" in args and "no-new-privileges" in args
            assert "--user" in args and args[args.index("--user") + 1] == "10001:10001"
            kwargs["on_line"](
                json.dumps({"protocol": "1.0", "type": "result", "ok": True, "design": design()})
            )

    brief = Brief(title="Test", prompt="Test", agent_engine="codex")
    board, report = native_plan(
        analyze(brief), brief, settings, None, tmp_path / "job", FixtureRunner(), lambda *args: None
    )
    assert report["state"] == "validated" and board.scenes
    assert removed and removed[0][:3] == ["docker", "rm", "-f"]
