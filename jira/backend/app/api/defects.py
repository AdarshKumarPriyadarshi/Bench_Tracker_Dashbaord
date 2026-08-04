from fastapi import APIRouter, Depends, Query

from app.dependencies import get_jira_client
from app.services.jira_client import JiraClient
from app.services.defect_service import DefectService
from app.models.defect import (
    DefectOverview,
    DefectBySysFuncResponse,
    DefectListResponse,
    DefectTrendResponse,
)

router = APIRouter(prefix="/api/defects", tags=["defects"])


def get_defect_service(client: JiraClient = Depends(get_jira_client)) -> DefectService:
    return DefectService(client)


@router.get("/overview", response_model=DefectOverview)
async def get_overview(
    project_key: str = Query("ADASDAI"),
    release: str | None = None,
    release_candidate: str | None = None,
    safety_type: str | None = None,
    service: DefectService = Depends(get_defect_service),
):
    return await service.get_overview(project_key, release, release_candidate, safety_type)


@router.get("/by-sysfunc", response_model=DefectBySysFuncResponse)
async def get_by_sysfunc(
    project_key: str = Query("ADASDAI"),
    release: str | None = None,
    release_candidate: str | None = None,
    safety_type: str | None = None,
    service: DefectService = Depends(get_defect_service),
):
    return await service.get_by_sysfunc(project_key, release, release_candidate, safety_type)


@router.get("/list", response_model=DefectListResponse)
async def get_defect_list(
    project_key: str = Query("ADASDAI"),
    release: str | None = None,
    release_candidate: str | None = None,
    safety_type: str | None = None,
    sysfunc: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DefectService = Depends(get_defect_service),
):
    return await service.get_list(project_key, release, release_candidate, safety_type, sysfunc, status, page, page_size)


@router.get("/trend", response_model=DefectTrendResponse)
async def get_trend(
    project_key: str = Query("ADASDAI"),
    days: int = Query(7, ge=1, le=30),
    release: str | None = None,
    release_candidate: str | None = None,
    safety_type: str | None = None,
    service: DefectService = Depends(get_defect_service),
):
    return await service.get_trend(project_key, days, release, release_candidate, safety_type)
