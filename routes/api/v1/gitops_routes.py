import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from loguru import logger

from models.gitops_models import (
    GitOpsCreateBranchRequest,
    GitOpsCreateBranchResponse,
    GitOpsCreatePRRequest,
    GitOpsCreatePRResponse,
    GitOpsStatusResponse,
    GitOpsUpdateRequest,
    GitOpsUpdateResponse,
)
from utils import callback_store
from utils.providers.base import FileCommit
from utils.providers.factory import get_provider
from utils.providers.template import apply_substitutions, derive_sidecar_path

router = APIRouter()


def _sidecar(payload: dict) -> str:
    return json.dumps(payload, indent=2)


def _handle_error(e: Exception, context: str):
    logger.error(f"{context}: {e}")
    status = getattr(e, "status", None)
    if status == 422:
        raise HTTPException(status_code=422, detail=str(e))
    if status == 404:
        raise HTTPException(status_code=404, detail=str(e))
    raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-pr", response_model=GitOpsCreatePRResponse)
async def create_pr(request: GitOpsCreatePRRequest):
    logger.info(f"create-pr provider={request.provider} repo={request.repo_name} branch={request.branch_name}")
    try:
        provider = get_provider(request.provider)

        provider.create_branch(request.repo_name, request.branch_name, request.base_branch)

        template_raw = provider.read_file(request.repo_name, request.template_file, ref=request.base_branch)
        rendered = apply_substitutions(template_raw, request.substitutions)

        sidecar_path = derive_sidecar_path(request.target_file)
        commit_msg = request.commit_message or f"Add {request.target_file}"
        provider.commit_files(
            request.repo_name,
            request.branch_name,
            [FileCommit(request.target_file, rendered), FileCommit(sidecar_path, _sidecar(request.model_dump()))],
            commit_msg,
        )

        pr_info = provider.create_pr(
            request.repo_name, request.branch_name, request.base_branch, request.pr_title, request.pr_body
        )
        logger.info(f"PR created: {pr_info.pr_url}")

        if request.callback_url:
            callback_store.register(
                pr_id=pr_info.pr_id,
                provider=request.provider,
                repo_name=request.repo_name,
                branch_name=request.branch_name,
                callback_url=request.callback_url,
            )

        return GitOpsCreatePRResponse(
            branch_name=request.branch_name,
            pr_url=pr_info.pr_url,
            pr_id=pr_info.pr_id,
            target_file=request.target_file,
            sidecar_file=sidecar_path,
        )
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e, "create-pr")


@router.post("/branch", response_model=GitOpsCreateBranchResponse)
async def create_branch(request: GitOpsCreateBranchRequest):
    logger.info(f"branch provider={request.provider} repo={request.repo_name} branch={request.branch_name}")
    try:
        provider = get_provider(request.provider)

        provider.create_branch(request.repo_name, request.branch_name, request.base_branch)

        template_raw = provider.read_file(request.repo_name, request.template_file, ref=request.base_branch)
        rendered = apply_substitutions(template_raw, request.substitutions)

        sidecar_path = derive_sidecar_path(request.target_file)
        commit_msg = request.commit_message or f"Add {request.target_file}"
        provider.commit_files(
            request.repo_name,
            request.branch_name,
            [FileCommit(request.target_file, rendered), FileCommit(sidecar_path, _sidecar(request.model_dump()))],
            commit_msg,
        )

        return GitOpsCreateBranchResponse(
            branch_name=request.branch_name,
            target_file=request.target_file,
            sidecar_file=sidecar_path,
        )
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e, "branch")


@router.post("/update", response_model=GitOpsUpdateResponse)
async def update(request: GitOpsUpdateRequest):
    logger.info(f"update provider={request.provider} repo={request.repo_name} target={request.target_file}")
    try:
        provider = get_provider(request.provider)

        sidecar_path = derive_sidecar_path(request.target_file)
        try:
            sidecar_raw = provider.read_file(request.repo_name, sidecar_path, ref=request.base_branch)
        except Exception as e:
            if getattr(e, "status", None) == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Sidecar not found at {sidecar_path} on {request.base_branch}",
                )
            raise

        original = json.loads(sidecar_raw)
        merged = {**original.get("substitutions", {}), **request.new_substitutions}

        template_raw = provider.read_file(request.repo_name, original["template_file"], ref=request.base_branch)
        rendered = apply_substitutions(template_raw, merged)

        updated_sidecar = {
            **original,
            "substitutions": merged,
            "_updated_at": datetime.now(timezone.utc).isoformat(),
        }

        provider.create_branch(request.repo_name, request.branch_name, request.base_branch)

        commit_msg = request.commit_message or f"Update {request.target_file}"
        provider.commit_files(
            request.repo_name,
            request.branch_name,
            [
                FileCommit(request.target_file, rendered),
                FileCommit(sidecar_path, json.dumps(updated_sidecar, indent=2)),
            ],
            commit_msg,
        )

        pr_title = request.pr_title or f"Update {request.target_file}"
        pr_info = provider.create_pr(
            request.repo_name, request.branch_name, request.base_branch, pr_title, request.pr_body
        )
        logger.info(f"Update PR created: {pr_info.pr_url}")

        if request.callback_url:
            callback_store.register(
                pr_id=pr_info.pr_id,
                provider=request.provider,
                repo_name=request.repo_name,
                branch_name=request.branch_name,
                callback_url=request.callback_url,
            )

        return GitOpsUpdateResponse(
            branch_name=request.branch_name,
            pr_url=pr_info.pr_url,
            pr_id=pr_info.pr_id,
            target_file=request.target_file,
            sidecar_file=sidecar_path,
            applied_substitutions=merged,
        )
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e, "update")


@router.get("/status", response_model=GitOpsStatusResponse)
async def get_status(provider: str, repo_name: str, branch_name: str):
    logger.info(f"status provider={provider} repo={repo_name} branch={branch_name}")
    try:
        pr_info = get_provider(provider).get_pr_status(repo_name, branch_name)
        return GitOpsStatusResponse(
            state=pr_info.state,
            pr_url=pr_info.pr_url,
            pr_id=pr_info.pr_id,
            branch_name=branch_name,
            repo_name=repo_name,
        )
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e, "status")
