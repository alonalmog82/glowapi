import hashlib
import hmac
import json

import requests
from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from settings import get_settings
from utils import callback_store

router = APIRouter()


def _deliver_callback(pr_id: str, event: str, pr_url: str = "") -> None:
    registration = callback_store.get(pr_id)
    if not registration:
        return

    payload = {
        "event": event,
        "pr_id": pr_id,
        "pr_url": pr_url,
        "branch_name": registration["branch_name"],
        "repo_name": registration["repo_name"],
        "provider": registration["provider"],
    }
    url = registration["callback_url"]

    for attempt in range(1, 3):
        try:
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code < 500:
                logger.info(f"Callback delivered to {url} (status {r.status_code})")
                callback_store.remove(pr_id)
                return
            logger.warning(f"Callback attempt {attempt} got {r.status_code} from {url}")
        except Exception as e:
            logger.warning(f"Callback attempt {attempt} failed for {url}: {e}")

    logger.error(f"Failed to deliver callback to {url} after 2 attempts — pr_id={pr_id}")


def _verify_hmac(secret: str, body: bytes, signature_header: str, prefix: str = "sha256=") -> bool:
    expected = prefix + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature_header, expected)


@router.post("/github")
async def github_webhook(request: Request):
    body = await request.body()
    secret = get_settings().github_webhook_secret

    if secret:
        sig = request.headers.get("X-Hub-Signature-256", "")
        if not _verify_hmac(secret, body, sig):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = request.headers.get("X-GitHub-Event", "")
    if event != "pull_request":
        return {"status": "ignored", "event": event}

    action = payload.get("action")
    pr = payload.get("pull_request", {})
    pr_id = str(pr.get("number", ""))
    pr_url = pr.get("html_url", "")

    if action == "closed":
        if pr.get("merged"):
            logger.info(f"GitHub PR #{pr_id} merged")
            _deliver_callback(pr_id, "PR_MERGED", pr_url)
        else:
            logger.info(f"GitHub PR #{pr_id} declined/closed")
            _deliver_callback(pr_id, "PR_DECLINED", pr_url)

    return {"status": "ok"}


@router.post("/bitbucket")
async def bitbucket_webhook(request: Request):
    body = await request.body()
    secret = get_settings().bitbucket_webhook_secret

    if secret:
        sig = request.headers.get("X-Hub-Signature", "")
        if not _verify_hmac(secret, body, sig):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = request.headers.get("X-Event-Key", "")
    pr = payload.get("pullrequest", {})
    pr_id = str(pr.get("id", ""))
    pr_url = pr.get("links", {}).get("html", {}).get("href", "")

    if event == "pullrequest:fulfilled":
        logger.info(f"Bitbucket PR #{pr_id} merged")
        _deliver_callback(pr_id, "PR_MERGED", pr_url)
    elif event == "pullrequest:rejected":
        logger.info(f"Bitbucket PR #{pr_id} declined")
        _deliver_callback(pr_id, "PR_DECLINED", pr_url)
    else:
        return {"status": "ignored", "event": event}

    return {"status": "ok"}
