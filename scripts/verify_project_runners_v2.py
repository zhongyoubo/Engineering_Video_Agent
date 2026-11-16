"""Execute ONLY authored fixtures on host to verify the runner logic, not container isolation."""

import json, os, subprocess, sys, shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0, str(root / "apps/api/src"))
from explainer.domain import Brief
from explainer.adapters.project_plan import project_plan

out = root / ".verify-runtime"
out.mkdir(exist_ok=True)
fixtures = {
    "python-cli": {"demo.py": 'print("verified fixture output")'},
    "static-web": {
        "index.html": '<button id="go" onclick="document.getElementById(&quot;result&quot;).textContent=&quot;ready&quot;">Run</button><p id="result">waiting</p>'
    },
    "python-api": {
        "app.py": 'from fastapi import FastAPI\napp=FastAPI()\n@app.get("/health")\ndef health():return {"status":"ok"}\n'
    },
    "node-web": {
        "package.json": json.dumps(
            {
                "name": "fixture-node",
                "version": "1.0.0",
                "scripts": {"start": "node server.js"},
            }
        ),
        "server.js": 'require("http").createServer((q,s)=>{s.setHeader("Content-Type","text/html");s.end("<h1 id=\\"status\\">Node application ready</h1>")}).listen(8765,"127.0.0.1")',
    },
    "vue-vite": {
        "package.json": json.dumps(
            {
                "name": "vue-fixture",
                "version": "1.0.0",
                "type": "module",
                "scripts": {"dev": "vite", "build": "vite build"},
                "dependencies": {"vue": "3.5.13"},
                "devDependencies": {"vite": "6.3.5"},
            }
        ),
        "index.html": '<div id="app"></div><script type="module" src="/main.js"></script>',
        "main.js": 'import {createApp} from "vue";createApp({template:"<h1>Vue fixture ready</h1>"}).mount("#app")',
    },
    "react-vite": {
        "package.json": json.dumps(
            {
                "name": "react-fixture",
                "version": "1.0.0",
                "type": "module",
                "scripts": {"dev": "vite", "build": "vite build"},
                "dependencies": {"react": "19.2.0", "react-dom": "19.2.0"},
                "devDependencies": {"vite": "6.3.5"},
            }
        ),
        "index.html": '<div id="app"></div><script type="module" src="/main.js"></script>',
        "main.js": 'import React from "react";import {createRoot} from "react-dom/client";createRoot(document.getElementById("app")).render(React.createElement("h1",null,"React fixture ready"));',
    },
}
reports = []
for kind, files in fixtures.items():
    source = out / kind / "source"
    source.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (source / name).write_text(text)
    runtime = "node-web" if kind.endswith("vite") else kind
    entry = (
        "package.json"
        if runtime == "node-web"
        else "app.py"
        if runtime == "python-api"
        else "index.html"
        if runtime == "static-web"
        else "demo.py"
    )
    actions = (
        [
            {"kind": "click", "target": "#go"},
            {"kind": "assert_text", "target": "#result", "value": "ready"},
        ]
        if runtime == "static-web"
        else []
    )
    brief = Brief(
        title="Fixture",
        input_id="i",
        runtime=runtime,
        runtime_entry=entry,
        runtime_actions=actions,
        api_requests=[{"method": "GET", "path": "/health", "expected_status": 200}]
        if runtime == "python-api"
        else [],
    )
    plan = project_plan({"files": {n: {"text": s} for n, s in files.items()}}, brief)
    planfile = out / kind / "plan.json"
    planfile.write_text(json.dumps(plan))
    target = out / kind / "output"
    subprocess.run(
        [
            "node",
            "infra/sandbox/project-runner.mjs",
            "--plan",
            str(planfile.resolve()),
            "--source",
            str(source.resolve()),
            "--output",
            str(target.resolve()),
            "--python",
            str(root / ".venv/bin/python"),
            "--cache-root",
            "/tmp/explainer-v2-npm-cache",
        ],
        check=True,
        timeout=150,
    )
    result = json.loads((target / "result.json").read_text())
    assert result["exit_code"] == 0, (kind, result)
    reports.append(
        {
            "kind": kind,
            "passed": True,
            "actions": result["actions"],
            "requests": len(result["requests"]),
        }
    )
    print("Fixture passed:", kind, flush=True)
report = {
    "result": "passed",
    "actual_runners": reports,
    "container_isolation_tested": False,
    "note": "Only authored fixtures executed directly; production upload path still requires Docker isolation",
}
(out / "verification.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
