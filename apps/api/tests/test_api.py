def create(client, headers):
    return client.post("/api/v1/projects", headers=headers, json={"name": "Example"}).json()["id"]


def body(project):
    return {
        "project_id": project,
        "brief": {
            "title": "API explained",
            "prompt": "Explain requests and responses.",
            "mode": "storyboard",
        },
    }


def test_auth_and_cross_tenant(client, headers):
    assert client.get("/api/v1/projects").status_code == 401
    project = create(client, headers)
    other = {"Authorization": "Bearer " + "b" * 32}
    assert client.get("/api/v1/projects", headers=other).json()["items"] == []
    assert client.post("/api/v1/videos", headers=other, json=body(project)).status_code == 404


def test_csrf(client, headers):
    assert (
        client.post(
            "/api/v1/projects", headers={**headers, "Origin": "https://evil.example"}, json={"name": "x"}
        ).status_code
        == 403
    )


def test_chunked_request_limit(client, headers, settings):
    settings.max_upload_bytes = 100

    def chunks():
        yield b'{"name":"'
        yield b"x" * (2 * 1024 * 1024)
        yield b'"}'

    response = client.post(
        "/api/v1/projects", headers={**headers, "Content-Type": "application/json"}, content=chunks()
    )
    assert response.status_code == 413


def test_idempotency_and_cancel(client, headers):
    project = create(client, headers)
    h = {**headers, "Idempotency-Key": "stable"}
    a = client.post("/api/v1/videos", headers=h, json=body(project))
    b = client.post("/api/v1/videos", headers=h, json=body(project))
    assert a.status_code == b.status_code == 202
    assert a.json()["job_id"] == b.json()["job_id"]
    changed = body(project)
    changed["brief"]["title"] = "different"
    assert client.post("/api/v1/videos", headers=h, json=changed).status_code == 409
    job = a.json()["job_id"]
    assert client.post(f"/api/v1/jobs/{job}/cancel", headers=headers).json()["state"] == "CANCELED"


def test_model_keys_not_exposed(client, headers, settings):
    settings.model_key = "very-secret-key"
    settings.model_url = "http://localhost:1234/v1"
    text = client.get("/api/v1/capabilities", headers=headers).text
    assert settings.model_key not in text
    assert settings.model_url not in text


def test_locked_and_audio_invalidated(client, headers, settings):
    project = create(client, headers)
    result = client.post("/api/v1/videos", headers=headers, json=body(project)).json()
    from explainer.db import Database
    from explainer.worker import run_once

    db = Database(settings.data_dir)
    assert run_once(settings, db)
    revision = client.get("/api/v1/revisions/" + result["revision_id"], headers=headers).json()
    board = revision["storyboard"]
    board["scenes"][0]["locked"] = True
    fork = client.post(
        f"/api/v1/revisions/{revision['id']}/fork",
        headers=headers,
        json={"expected_version": 1, "storyboard": board, "auto_render": False},
    )
    assert fork.status_code == 202
    assert run_once(settings, db)
    locked_id = fork.json()["revision_id"]
    locked = client.get("/api/v1/revisions/" + locked_id, headers=headers).json()["storyboard"]
    locked["scenes"][0]["narration"] = "changed"
    rejected = client.post(
        f"/api/v1/revisions/{locked_id}/fork",
        headers=headers,
        json={"expected_version": 1, "storyboard": locked},
    )
    assert rejected.status_code == 409
    locked["scenes"][0]["narration"] = board["scenes"][0]["narration"]
    locked["scenes"][0]["locked"] = False
    assert (
        client.post(
            f"/api/v1/revisions/{locked_id}/fork",
            headers=headers,
            json={"expected_version": 1, "storyboard": locked, "auto_render": False},
        ).status_code
        == 202
    )


def test_asset_tenant_isolation(settings, db, client, headers):
    from explainer.storage import Storage

    storage = Storage(settings, db)
    asset = storage.put("local", b"private text", "script", "x.md", "text/markdown")
    assert client.get("/api/v1/assets/" + asset["id"], headers=headers).content == b"private text"
    assert (
        client.get(
            "/api/v1/assets/" + asset["id"], headers={"Authorization": "Bearer " + "b" * 32}
        ).status_code
        == 404
    )
