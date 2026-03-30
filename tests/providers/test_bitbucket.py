from unittest.mock import MagicMock, patch

import pytest

from utils.providers.base import FileCommit, PRState
from utils.providers.bitbucket import BitbucketProvider


@pytest.fixture
def provider():
    with patch("utils.providers.bitbucket.get_settings") as s:
        s.return_value.bitbucket_workspace_token = "test-token"
        yield BitbucketProvider()


@patch("utils.providers.bitbucket.requests.get")
@patch("utils.providers.bitbucket.requests.post")
def test_create_branch(mock_post, mock_get, provider):
    mock_get.return_value = MagicMock(json=lambda: {"target": {"hash": "abc123"}})
    mock_get.return_value.raise_for_status = MagicMock()
    mock_post.return_value.raise_for_status = MagicMock()

    provider.create_branch("ws/repo", "feature", "main")

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["name"] == "feature"
    assert kwargs["json"]["target"]["hash"] == "abc123"


@patch("utils.providers.bitbucket.requests.get")
def test_read_file(mock_get, provider):
    mock_get.return_value.text = "file content"
    mock_get.return_value.raise_for_status = MagicMock()

    result = provider.read_file("ws/repo", "path/file.tf", "main")
    assert result == "file content"


@patch("utils.providers.bitbucket.requests.post")
def test_commit_files_sends_all_files_in_one_request(mock_post, provider):
    mock_post.return_value.raise_for_status = MagicMock()

    provider.commit_files(
        "ws/repo", "feature",
        [FileCommit("a.tf", "content-a"), FileCommit("a.tf.json", '{}')],
        "msg"
    )
    assert mock_post.call_count == 1
    _, kwargs = mock_post.call_args
    assert kwargs["data"]["a.tf"] == "content-a"
    assert kwargs["data"]["a.tf.json"] == "{}"
    assert kwargs["data"]["branch"] == "feature"


@patch("utils.providers.bitbucket.requests.post")
def test_create_pr(mock_post, provider):
    mock_post.return_value.json = lambda: {
        "id": 42,
        "links": {"html": {"href": "https://bitbucket.org/ws/repo/pull-requests/42"}}
    }
    mock_post.return_value.raise_for_status = MagicMock()

    info = provider.create_pr("ws/repo", "feature", "main", "Title", "Body")
    assert info.pr_id == "42"
    assert info.state == PRState.OPEN
    assert "pull-requests/42" in info.pr_url


@patch("utils.providers.bitbucket.requests.get")
def test_get_pr_status_merged(mock_get, provider):
    mock_get.return_value.json = lambda: {
        "values": [{"id": 1, "state": "MERGED", "links": {"html": {"href": "https://bb.org/pr/1"}}}]
    }
    mock_get.return_value.raise_for_status = MagicMock()

    assert provider.get_pr_status("ws/repo", "feature").state == PRState.MERGED


@patch("utils.providers.bitbucket.requests.get")
def test_get_pr_status_declined(mock_get, provider):
    mock_get.return_value.json = lambda: {
        "values": [{"id": 2, "state": "DECLINED", "links": {"html": {"href": "https://bb.org/pr/2"}}}]
    }
    mock_get.return_value.raise_for_status = MagicMock()

    assert provider.get_pr_status("ws/repo", "feature").state == PRState.DECLINED


@patch("utils.providers.bitbucket.requests.get")
def test_get_pr_status_unknown_when_empty(mock_get, provider):
    mock_get.return_value.json = lambda: {"values": []}
    mock_get.return_value.raise_for_status = MagicMock()

    assert provider.get_pr_status("ws/repo", "no-branch").state == PRState.UNKNOWN


def test_invalid_repo_name_raises(provider):
    with pytest.raises(ValueError, match="Invalid repo_name"):
        provider.create_branch("no-slash", "feature", "main")
