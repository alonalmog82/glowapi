from typing import List

import requests

from settings import get_settings
from utils.providers.base import FileCommit, GitProvider, PRInfo, PRState

_BASE = "https://api.bitbucket.org/2.0"

_STATE_MAP = {
    "OPEN": PRState.OPEN,
    "MERGED": PRState.MERGED,
    "DECLINED": PRState.DECLINED,
    "SUPERSEDED": PRState.DECLINED,
}


class BitbucketProvider(GitProvider):

    def _token(self) -> str:
        token = get_settings().bitbucket_workspace_token
        if not token:
            raise RuntimeError(
                "Bitbucket workspace token not configured. Set BITBUCKET_WORKSPACE_TOKEN."
            )
        return token

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token()}"}

    def _json_headers(self) -> dict:
        return {**self._auth_headers(), "Content-Type": "application/json"}

    def _parse_repo(self, repo_name: str):
        parts = repo_name.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid repo_name '{repo_name}'. Expected 'workspace/slug'.")
        return parts[0], parts[1]

    def create_branch(self, repo_name: str, branch_name: str, base_branch: str) -> None:
        workspace, slug = self._parse_repo(repo_name)
        # Resolve HEAD commit of base branch first
        r = requests.get(
            f"{_BASE}/repositories/{workspace}/{slug}/refs/branches/{base_branch}",
            headers=self._auth_headers(),
            timeout=15,
        )
        r.raise_for_status()
        sha = r.json()["target"]["hash"]
        r = requests.post(
            f"{_BASE}/repositories/{workspace}/{slug}/refs/branches",
            headers=self._json_headers(),
            json={"name": branch_name, "target": {"hash": sha}},
            timeout=15,
        )
        r.raise_for_status()

    def read_file(self, repo_name: str, file_path: str, ref: str) -> str:
        workspace, slug = self._parse_repo(repo_name)
        r = requests.get(
            f"{_BASE}/repositories/{workspace}/{slug}/src/{ref}/{file_path}",
            headers=self._auth_headers(),
            timeout=15,
        )
        r.raise_for_status()
        return r.text

    def commit_files(self, repo_name: str, branch: str, files: List[FileCommit], message: str) -> None:
        # Bitbucket supports multiple files in a single multipart POST — atomically committed.
        workspace, slug = self._parse_repo(repo_name)
        data = {"message": message, "branch": branch}
        for f in files:
            data[f.path] = f.content
        r = requests.post(
            f"{_BASE}/repositories/{workspace}/{slug}/src",
            headers=self._auth_headers(),
            data=data,
            timeout=15,
        )
        r.raise_for_status()

    def create_pr(self, repo_name: str, branch: str, base: str, title: str, body: str) -> PRInfo:
        workspace, slug = self._parse_repo(repo_name)
        r = requests.post(
            f"{_BASE}/repositories/{workspace}/{slug}/pullrequests",
            headers=self._json_headers(),
            json={
                "title": title,
                "description": body,
                "source": {"branch": {"name": branch}},
                "destination": {"branch": {"name": base}},
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return PRInfo(
            pr_url=data["links"]["html"]["href"],
            pr_id=str(data["id"]),
            state=PRState.OPEN,
        )

    def get_pr_status(self, repo_name: str, branch_name: str) -> PRInfo:
        workspace, slug = self._parse_repo(repo_name)
        r = requests.get(
            f"{_BASE}/repositories/{workspace}/{slug}/pullrequests",
            headers=self._auth_headers(),
            params={"q": f'source.branch.name="{branch_name}"', "state": "ALL"},
            timeout=15,
        )
        r.raise_for_status()
        values = r.json().get("values", [])
        if not values:
            return PRInfo(pr_url="", pr_id="", state=PRState.UNKNOWN)
        pr = values[0]
        return PRInfo(
            pr_url=pr["links"]["html"]["href"],
            pr_id=str(pr["id"]),
            state=_STATE_MAP.get(pr["state"], PRState.UNKNOWN),
        )
