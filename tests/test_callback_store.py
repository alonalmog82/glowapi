from utils import callback_store


def test_register_and_get():
    callback_store.register("pr-1", "github", "org/repo", "branch", "https://example.com/cb")
    entry = callback_store.get("pr-1")
    assert entry["callback_url"] == "https://example.com/cb"
    assert entry["branch_name"] == "branch"
    assert entry["provider"] == "github"


def test_get_missing_returns_none():
    assert callback_store.get("nonexistent") is None


def test_remove():
    callback_store.register("pr-2", "github", "org/repo", "b", "https://x.com")
    callback_store.remove("pr-2")
    assert callback_store.get("pr-2") is None


def test_remove_missing_is_safe():
    callback_store.remove("nonexistent")


def test_clear():
    callback_store.register("pr-3", "bitbucket", "ws/repo", "b", "https://y.com")
    callback_store.clear()
    assert callback_store.get("pr-3") is None
