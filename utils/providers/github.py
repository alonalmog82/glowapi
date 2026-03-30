import base64
import time
from typing import List

import jwt
import requests
from github import Github

from settings import get_settings
from utils.providers.base import FileCommit, GitProvider, PRInfo, PRState


def _normalize_pem(raw: str) -> str:
    """Restore newlines in PEM keys that were flattened when stored as env vars."""
    if "\\n" in raw:
        return raw.replace("\\n", "\n")
    return raw


def _generate_jwt(client_id: str, private_key: str) -> str:
    now = int(time.time())
    payload = {
        "iat": now - 60,   # issued 60s ago to account for clock skew
        "exp": now + (9 * 60),
        "iss": client_id,
    }
    return jwt.encode(payload, _normalize_pem(private_key), algorithm="RS256")


def _get_installation_token(jwt_token: str, installation_id: str) -> str:
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
    }
    r = requests.post(url, headers=headers, timeout=10)
    if r.status_code != 201:
        raise RuntimeError(f"GitHub authentication failed ({r.status_code}): {r.json()}")
    return r.json()["token"]


class GitHubProvider(GitProvider):

    def _get_client(self) -> Github:
        s = get_settings()
        if not s.github_client_id or not s.github_app_installation_id or not s.github_app_private_key:
            raise RuntimeError(
                "GitHub App credentials not configured. "
                "Set GITHUB_CLIENT_ID, GITHUB_APP_INSTALLATION_ID, and JWT_TOKEN."
            )
        jwt_token = _generate_jwt(s.github_client_id, s.github_app_private_key)
        token = _get_installation_token(jwt_token, s.github_app_installation_id)
        return Github(token)

    def create_branch(self, repo_name: str, branch_name: str, base_branch: str) -> None:
        repo = self._get_client().get_repo(repo_name)
        sha = repo.get_branch(base_branch).commit.sha
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sha)

    def read_file(self, repo_name: str, file_path: str, ref: str) -> str:
        repo = self._get_client().get_repo(repo_name)
        obj = repo.get_contents(file_path, ref=ref)
        return base64.b64decode(obj.content).decode("utf-8")

    def commit_files(self, repo_name: str, branch: str, files: List[FileCommit], message: str) -> None:
        # GitHub requires one API call per file. For atomic multi-file commits,
        # the Trees API can be used as a future improvement.
        repo = self._get_client().get_repo(repo_name)
        for f in files:
            repo.create_file(f.path, message, f.content, branch=branch)

    def create_pr(self, repo_name: str, branch: str, base: str, title: str, body: str) -> PRInfo:
        repo = self._get_client().get_repo(repo_name)
        pr = repo.create_pull(title=title, body=body, head=branch, base=base)
        return PRInfo(pr_url=pr.html_url, pr_id=str(pr.number), state=PRState.OPEN)

    def get_pr_status(self, repo_name: str, branch_name: str) -> PRInfo:
        repo = self._get_client().get_repo(repo_name)
        owner = repo_name.split("/")[0]
        prs = repo.get_pulls(state="all", head=f"{owner}:{branch_name}")
        if prs.totalCount == 0:
            return PRInfo(pr_url="", pr_id="", state=PRState.UNKNOWN)
        pr = prs[0]
        if pr.merged:
            state = PRState.MERGED
        elif pr.state == "closed":
            state = PRState.DECLINED
        else:
            state = PRState.OPEN
        return PRInfo(pr_url=pr.html_url, pr_id=str(pr.number), state=state)
