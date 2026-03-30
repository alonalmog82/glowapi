from typing import Dict, Literal, Optional

from pydantic import BaseModel

from utils.providers.base import PRState


class GitOpsCreatePRRequest(BaseModel):
    provider: Literal["github", "bitbucket"] = "github"
    repo_name: str
    branch_name: str
    base_branch: str = "main"
    template_file: str
    target_file: str
    substitutions: Dict[str, str]
    pr_title: str
    pr_body: str = ""
    commit_message: Optional[str] = None
    callback_url: Optional[str] = None


class GitOpsCreatePRResponse(BaseModel):
    branch_name: str
    pr_url: str
    pr_id: str
    target_file: str
    sidecar_file: str


class GitOpsCreateBranchRequest(BaseModel):
    provider: Literal["github", "bitbucket"] = "github"
    repo_name: str
    branch_name: str
    base_branch: str = "main"
    template_file: str
    target_file: str
    substitutions: Dict[str, str]
    commit_message: Optional[str] = None


class GitOpsCreateBranchResponse(BaseModel):
    branch_name: str
    target_file: str
    sidecar_file: str


class GitOpsUpdateRequest(BaseModel):
    provider: Literal["github", "bitbucket"] = "github"
    repo_name: str
    base_branch: str = "main"
    target_file: str
    new_substitutions: Dict[str, str]
    branch_name: str
    pr_title: Optional[str] = None
    pr_body: str = ""
    commit_message: Optional[str] = None
    callback_url: Optional[str] = None


class GitOpsUpdateResponse(BaseModel):
    branch_name: str
    pr_url: str
    pr_id: str
    target_file: str
    sidecar_file: str
    applied_substitutions: Dict[str, str]


class GitOpsStatusResponse(BaseModel):
    state: PRState
    pr_url: str
    pr_id: str
    branch_name: str
    repo_name: str
