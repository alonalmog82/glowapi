from typing import Dict, Optional

# In-memory store: pr_id → callback registration.
# v1: entries are lost on pod restart. Acceptable since PRs typically close within minutes.
# Upgrade path: swap _store for a Redis client for multi-replica or long-lived requirements.
_store: Dict[str, dict] = {}


def register(pr_id: str, provider: str, repo_name: str, branch_name: str, callback_url: str) -> None:
    _store[pr_id] = {
        "provider": provider,
        "repo_name": repo_name,
        "branch_name": branch_name,
        "callback_url": callback_url,
    }


def get(pr_id: str) -> Optional[dict]:
    return _store.get(pr_id)


def remove(pr_id: str) -> None:
    _store.pop(pr_id, None)


def clear() -> None:
    """Clear all entries. Intended for use in tests."""
    _store.clear()
