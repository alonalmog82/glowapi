import base64
from unittest.mock import MagicMock, patch

import pytest

from utils.providers.base import FileCommit, PRState
from utils.providers.github import GitHubProvider, _normalize_pem


def _make_provider():
    with patch("utils.providers.github._generate_jwt", return_value="jwt"), \
         patch("utils.providers.github._get_installation_token", return_value="token"), \
         patch("utils.providers.github.get_settings") as mock_settings:
        mock_settings.return_value.github_client_id = "cid"
        mock_settings.return_value.github_app_installation_id = "iid"
        mock_settings.return_value.github_app_private_key = "key"
        return GitHubProvider()


@pytest.fixture
def provider():
    return _make_provider()


@pytest.fixture
def mock_repo():
    with patch("utils.providers.github.Github") as mock_cls, \
         patch("utils.providers.github._generate_jwt", return_value="jwt"), \
         patch("utils.providers.github._get_installation_token", return_value="token"), \
         patch("utils.providers.github.get_settings") as mock_settings:
        mock_settings.return_value.github_client_id = "cid"
        mock_settings.return_value.github_app_installation_id = "iid"
        mock_settings.return_value.github_app_private_key = "key"
        mock_gh = MagicMock()
        mock_cls.return_value = mock_gh
        repo = MagicMock()
        mock_gh.get_repo.return_value = repo
        yield repo


def test_normalize_pem_replaces_escaped_newlines():
    assert _normalize_pem("BEGIN\\nEND") == "BEGIN\nEND"


def test_normalize_pem_passthrough():
    assert _normalize_pem("BEGIN\nEND") == "BEGIN\nEND"


def test_create_branch(mock_repo):
    mock_repo.get_branch.return_value.commit.sha = "abc123"
    p = _make_provider()
    with patch("utils.providers.github.Github") as mock_cls, \
         patch("utils.providers.github._generate_jwt", return_value="jwt"), \
         patch("utils.providers.github._get_installation_token", return_value="token"), \
         patch("utils.providers.github.get_settings") as s:
        s.return_value.github_client_id = "cid"
        s.return_value.github_app_installation_id = "iid"
        s.return_value.github_app_private_key = "key"
        mock_cls.return_value.get_repo.return_value = mock_repo
        p.create_branch("org/repo", "feature", "main")
    mock_repo.create_git_ref.assert_called_once_with(ref="refs/heads/feature", sha="abc123")


def test_read_file(mock_repo):
    mock_repo.get_contents.return_value.content = base64.b64encode(b"hello").decode()
    with patch("utils.providers.github.Github") as mock_cls, \
         patch("utils.providers.github._generate_jwt", return_value="jwt"), \
         patch("utils.providers.github._get_installation_token", return_value="token"), \
         patch("utils.providers.github.get_settings") as s:
        s.return_value.github_client_id = "cid"
        s.return_value.github_app_installation_id = "iid"
        s.return_value.github_app_private_key = "key"
        mock_cls.return_value.get_repo.return_value = mock_repo
        p = GitHubProvider()
        result = p.read_file("org/repo", "path/file.txt", "main")
    assert result == "hello"


def test_create_pr_returns_open_state(mock_repo):
    mock_pr = MagicMock()
    mock_pr.html_url = "https://github.com/org/repo/pull/42"
    mock_pr.number = 42
    mock_repo.create_pull.return_value = mock_pr
    with patch("utils.providers.github.Github") as mock_cls, \
         patch("utils.providers.github._generate_jwt", return_value="jwt"), \
         patch("utils.providers.github._get_installation_token", return_value="token"), \
         patch("utils.providers.github.get_settings") as s:
        s.return_value.github_client_id = "cid"
        s.return_value.github_app_installation_id = "iid"
        s.return_value.github_app_private_key = "key"
        mock_cls.return_value.get_repo.return_value = mock_repo
        info = GitHubProvider().create_pr("org/repo", "feature", "main", "Title", "Body")
    assert info.pr_id == "42"
    assert info.state == PRState.OPEN


def test_get_pr_status_merged(mock_repo):
    mock_pr = MagicMock()
    mock_pr.merged = True
    mock_pr.state = "closed"
    mock_pr.html_url = "https://github.com/org/repo/pull/1"
    mock_pr.number = 1
    mock_repo.get_pulls.return_value.totalCount = 1
    mock_repo.get_pulls.return_value.__getitem__ = lambda _, i: mock_pr
    with patch("utils.providers.github.Github") as mock_cls, \
         patch("utils.providers.github._generate_jwt", return_value="jwt"), \
         patch("utils.providers.github._get_installation_token", return_value="token"), \
         patch("utils.providers.github.get_settings") as s:
        s.return_value.github_client_id = "cid"
        s.return_value.github_app_installation_id = "iid"
        s.return_value.github_app_private_key = "key"
        mock_cls.return_value.get_repo.return_value = mock_repo
        info = GitHubProvider().get_pr_status("org/repo", "feature")
    assert info.state == PRState.MERGED


def test_get_pr_status_unknown_when_no_prs(mock_repo):
    mock_repo.get_pulls.return_value.totalCount = 0
    with patch("utils.providers.github.Github") as mock_cls, \
         patch("utils.providers.github._generate_jwt", return_value="jwt"), \
         patch("utils.providers.github._get_installation_token", return_value="token"), \
         patch("utils.providers.github.get_settings") as s:
        s.return_value.github_client_id = "cid"
        s.return_value.github_app_installation_id = "iid"
        s.return_value.github_app_private_key = "key"
        mock_cls.return_value.get_repo.return_value = mock_repo
        info = GitHubProvider().get_pr_status("org/repo", "no-such-branch")
    assert info.state == PRState.UNKNOWN
