import json
from unittest.mock import MagicMock, patch

import pytest

from utils.providers.base import PRInfo, PRState

_CREATE_PR_PAYLOAD = {
    "provider": "github",
    "repo_name": "org/repo",
    "branch_name": "feature/test",
    "template_file": "templates/client.tpl",
    "target_file": "clients/acme.tf",
    "substitutions": {"name": "acme", "region": "us-east-1"},
    "pr_title": "Add acme",
}

_UPDATE_PAYLOAD = {
    "provider": "github",
    "repo_name": "org/repo",
    "base_branch": "main",
    "target_file": "clients/acme.tf",
    "new_substitutions": {"region": "eu-west-1"},
    "branch_name": "update/acme",
}

_SIDECAR_CONTENT = json.dumps({
    "provider": "github",
    "repo_name": "org/repo",
    "template_file": "templates/client.tpl",
    "target_file": "clients/acme.tf",
    "substitutions": {"name": "acme", "region": "us-east-1"},
})


def _mock_provider(template="module {{name}} { region = {{region}} }"):
    p = MagicMock()
    p.create_branch.return_value = None
    p.read_file.return_value = template
    p.commit_files.return_value = None
    p.create_pr.return_value = PRInfo(
        pr_url="https://github.com/org/repo/pull/1", pr_id="1", state=PRState.OPEN
    )
    p.get_pr_status.return_value = PRInfo(
        pr_url="https://github.com/org/repo/pull/1", pr_id="1", state=PRState.OPEN
    )
    return p


def test_healthcheck(client):
    r = client.get("/healthcheck")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_pr_success(client):
    mock_p = _mock_provider()
    with patch("routes.api.v1.gitops_routes.get_provider", return_value=mock_p):
        r = client.post("/api/v1/gitops/create-pr", json=_CREATE_PR_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    assert data["pr_url"] == "https://github.com/org/repo/pull/1"
    assert data["sidecar_file"] == "clients/acme.tf.json"
    assert data["branch_name"] == "feature/test"


def test_create_pr_commits_two_files(client):
    mock_p = _mock_provider()
    with patch("routes.api.v1.gitops_routes.get_provider", return_value=mock_p):
        client.post("/api/v1/gitops/create-pr", json=_CREATE_PR_PAYLOAD)
    files_committed = mock_p.commit_files.call_args[0][2]
    assert len(files_committed) == 2
    paths = [f.path for f in files_committed]
    assert "clients/acme.tf" in paths
    assert "clients/acme.tf.json" in paths


def test_create_pr_registers_callback(client):
    from utils import callback_store
    mock_p = _mock_provider()
    payload = {**_CREATE_PR_PAYLOAD, "callback_url": "https://example.com/cb"}
    with patch("routes.api.v1.gitops_routes.get_provider", return_value=mock_p):
        client.post("/api/v1/gitops/create-pr", json=payload)
    assert callback_store.get("1") is not None
    assert callback_store.get("1")["callback_url"] == "https://example.com/cb"


def test_create_pr_missing_required_field(client):
    payload = {k: v for k, v in _CREATE_PR_PAYLOAD.items() if k != "pr_title"}
    r = client.post("/api/v1/gitops/create-pr", json=payload)
    assert r.status_code == 422


def test_create_branch_success(client):
    mock_p = _mock_provider()
    with patch("routes.api.v1.gitops_routes.get_provider", return_value=mock_p):
        r = client.post("/api/v1/gitops/branch", json={
            k: v for k, v in _CREATE_PR_PAYLOAD.items() if k != "pr_title"
        })
    assert r.status_code == 200
    assert r.json()["sidecar_file"] == "clients/acme.tf.json"
    mock_p.create_pr.assert_not_called()


def test_update_success(client):
    mock_p = _mock_provider()
    mock_p.read_file.side_effect = [_SIDECAR_CONTENT, "module {{name}} { region = {{region}} }"]
    with patch("routes.api.v1.gitops_routes.get_provider", return_value=mock_p):
        r = client.post("/api/v1/gitops/update", json=_UPDATE_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    assert data["applied_substitutions"]["region"] == "eu-west-1"
    assert data["applied_substitutions"]["name"] == "acme"  # preserved from original


def test_update_sidecar_not_found(client):
    mock_p = _mock_provider()
    err = Exception("Not found")
    err.status = 404
    mock_p.read_file.side_effect = err
    with patch("routes.api.v1.gitops_routes.get_provider", return_value=mock_p):
        r = client.post("/api/v1/gitops/update", json=_UPDATE_PAYLOAD)
    assert r.status_code == 404


def test_status_open(client):
    mock_p = _mock_provider()
    with patch("routes.api.v1.gitops_routes.get_provider", return_value=mock_p):
        r = client.get("/api/v1/gitops/status", params={
            "provider": "github", "repo_name": "org/repo", "branch_name": "feature/test"
        })
    assert r.status_code == 200
    assert r.json()["state"] == "OPEN"


def test_invalid_provider_raises(client):
    payload = {**_CREATE_PR_PAYLOAD, "provider": "gitlab"}
    r = client.post("/api/v1/gitops/create-pr", json=payload)
    assert r.status_code == 422
