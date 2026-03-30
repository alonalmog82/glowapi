from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List


class PRState(str, Enum):
    OPEN = "OPEN"
    MERGED = "MERGED"
    DECLINED = "DECLINED"
    UNKNOWN = "UNKNOWN"


@dataclass
class PRInfo:
    pr_url: str
    pr_id: str
    state: PRState


@dataclass
class FileCommit:
    path: str
    content: str


class GitProvider(ABC):

    @abstractmethod
    def create_branch(self, repo_name: str, branch_name: str, base_branch: str) -> None:
        """Create a new branch from base_branch."""

    @abstractmethod
    def read_file(self, repo_name: str, file_path: str, ref: str) -> str:
        """Read and return the text content of a file at the given ref."""

    @abstractmethod
    def commit_files(self, repo_name: str, branch: str, files: List[FileCommit], message: str) -> None:
        """Commit one or more files to the branch in a single operation where possible."""

    @abstractmethod
    def create_pr(self, repo_name: str, branch: str, base: str, title: str, body: str) -> PRInfo:
        """Open a pull request and return its info."""

    @abstractmethod
    def get_pr_status(self, repo_name: str, branch_name: str) -> PRInfo:
        """Return the current state of the PR for the given branch."""
