from __future__ import annotations

from pydantic import BaseModel, Field

from nimbusware_maker.terraform_validate import RollbackMode


class TerraformValidateBody(BaseModel):
    workspace_path: str = Field(min_length=1, max_length=2000)
    run_id: str | None = Field(default=None, max_length=36)
    deploy_environment: str | None = Field(default=None, max_length=32)


class DeployCredentialsBody(BaseModel):
    aws_profile: str | None = Field(default=None, max_length=200)
    github_repo: str | None = Field(default=None, max_length=200)
    workflow_path: str | None = Field(default=None, max_length=500)
    deploy_environment: str | None = Field(default=None, max_length=32)


class DeployApproveBody(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)


class DeployApplyBody(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)
    workspace_path: str = Field(min_length=1, max_length=2000)
    deploy_environment: str | None = Field(default=None, max_length=32)


class DeploySmokeBody(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)
    api_url: str | None = Field(default=None, max_length=2000)
    web_url: str | None = Field(default=None, max_length=2000)
    use_playwright: bool = False


class DeployRollbackBody(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)
    workspace_path: str = Field(min_length=1, max_length=2000)
    mode: RollbackMode = "destroy"
    deploy_environment: str | None = Field(default=None, max_length=32)


class DeployCiPollBody(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)
    branch: str | None = Field(default=None, max_length=200)
