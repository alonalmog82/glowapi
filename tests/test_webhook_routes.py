import hashlib
import hmac
import json
from unittest.mock import patch

import pytest


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _github_payload(action: str, merged: bool = False, pr_number: int = 1) -> dict:
    return {
        "action": action,
        "pull_request": {
            "number": pr_number,
            "merged": merged,
            "html_url": f"https://github.com/org/repo/pull/{pr_number}",
        }
    }


def _bb_payload(pr_id: int = 42) -> dict:
    return {
        "pullrequest": {
            "id": pr_id,
            "links": {"html": {"href": f"https://bitbucket.org/ws/repo/pull-requests/{pr_id}"}}
        }
    }


def test_github_webhook_merged(client):
    from utils import callback_store
    callback_store.register("1", "github", "org/repo", "feature", "https://example.com/cb")

    body = json.dumps(_github_payload("closed", merged=True)).encode()
    with patch("routes.api.v1.webhook_routes.requests.post") as mock_post, \
         patch("routes.api.v1.webhook_routes.get_settings") as mock_settings:
        mock_settings.return_value.github_webhook_secret = None
        mock_post.return_value.status_code = 200
        r = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={"X-GitHub-Event": "pull_request", "Content-Type": "application/json"},
        )
    assert r.status_code == 200
    mock_post.assert_called_once()
    payload_sent = mock_post.call_args[1]["json"]
    assert payload_sent["event"] == "PR_MERGED"
    assert callback_store.get("1") is None  # removed after delivery


def test_github_webhook_declined(client):
    from utils import callback_store
    callback_store.register("2", "github", "org/repo", "feature", "https://example.com/cb")

    body = json.dumps(_github_payload("closed", merged=False, pr_number=2)).encode()
    with patch("routes.api.v1.webhook_routes.requests.post") as mock_post, \
         patch("routes.api.v1.webhook_routes.get_settings") as mock_settings:
        mock_settings.return_value.github_webhook_secret = None
        mock_post.return_value.status_code = 200
        client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={"X-GitHub-Event": "pull_request", "Content-Type": "application/json"},
        )
    payload_sent = mock_post.call_args[1]["json"]
    assert payload_sent["event"] == "PR_DECLINED"


def test_github_webhook_ignores_non_pr_events(client):
    with patch("routes.api.v1.webhook_routes.get_settings") as mock_settings:
        mock_settings.return_value.github_webhook_secret = None
        r = client.post(
            "/api/v1/webhooks/github",
            content=b"{}",
            headers={"X-GitHub-Event": "push", "Content-Type": "application/json"},
        )
    assert r.json()["status"] == "ignored"


def test_github_webhook_invalid_signature_rejected(client):
    body = b'{"action": "closed"}'
    with patch("routes.api.v1.webhook_routes.get_settings") as mock_settings:
        mock_settings.return_value.github_webhook_secret = "correct-secret"
        r = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": "sha256=invalidsig",
                "Content-Type": "application/json",
            },
        )
    assert r.status_code == 401


def test_github_webhook_valid_signature_accepted(client):
    body = json.dumps(_github_payload("opened")).encode()
    secret = "my-secret"
    sig = _sign(secret, body)
    with patch("routes.api.v1.webhook_routes.get_settings") as mock_settings:
        mock_settings.return_value.github_webhook_secret = secret
        r = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
    assert r.status_code == 200


def test_bitbucket_webhook_merged(client):
    from utils import callback_store
    callback_store.register("42", "bitbucket", "ws/repo", "feature", "https://example.com/cb")

    body = json.dumps(_bb_payload(42)).encode()
    with patch("routes.api.v1.webhook_routes.requests.post") as mock_post, \
         patch("routes.api.v1.webhook_routes.get_settings") as mock_settings:
        mock_settings.return_value.bitbucket_webhook_secret = None
        mock_post.return_value.status_code = 200
        r = client.post(
            "/api/v1/webhooks/bitbucket",
            content=body,
            headers={"X-Event-Key": "pullrequest:fulfilled", "Content-Type": "application/json"},
        )
    assert r.status_code == 200
    assert mock_post.call_args[1]["json"]["event"] == "PR_MERGED"


def test_bitbucket_webhook_ignored_event(client):
    with patch("routes.api.v1.webhook_routes.get_settings") as mock_settings:
        mock_settings.return_value.bitbucket_webhook_secret = None
        r = client.post(
            "/api/v1/webhooks/bitbucket",
            content=b"{}",
            headers={"X-Event-Key": "repo:push", "Content-Type": "application/json"},
        )
    assert r.json()["status"] == "ignored"
