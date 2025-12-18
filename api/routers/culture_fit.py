"""
Culture-Fit Analysis Router

컬쳐핏 분석 API 엔드포인트
"""

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from api.schemas.requests import (
    CultureFitRequest,
    CompanyAnalysisRequest,
    ApplicantAnalysisRequest,
)
from api.schemas.responses import (
    CultureFitResponse,
    CompanyAnalysisResponse,
    ApplicantAnalysisResponse,
    AnalysisStatus,
)
from api.services.pipeline import (
    run_full_analysis,
    run_company_analysis,
    run_applicant_analysis,
)


router = APIRouter(prefix="/api/culture-fit", tags=["culture-fit"])


@router.post(
    "/analyze",
    response_model=CultureFitResponse,
    summary="컬쳐핏 전체 분석",
    description="""
    회사 URL + 구직자 PDF → 컬쳐핏 분석 (병렬 처리)

    **처리 흐름:**
    1. 회사 분석 + 구직자 분석: 병렬 실행 (asyncio.gather)
    2. 비교 분석: 순차 실행 (둘 다 완료 후)

    **예상 소요 시간:** 60-90초
    """
)
async def analyze_culture_fit(request: CultureFitRequest) -> CultureFitResponse:
    """
    컬쳐핏 전체 분석 실행

    - 회사 채용 페이지 스크래핑 + 분석
    - 구직자 PDF 분석 (S3에서 로드)
    - 두 결과 비교하여 매칭 점수 계산
    """
    start_time = time.time()

    try:
        result = await run_full_analysis(
            company_url=str(request.company_url),
            applicant_s3_keys=request.applicant_s3_keys,
            applicant_name=request.applicant_name,
            save_to_db=False  # API에서는 DB 저장 안 함 (별도 처리)
        )

        elapsed = time.time() - start_time

        return CultureFitResponse(
            company=result["company"],
            applicant=result["applicant"],
            matching=result["matching"],
            status=AnalysisStatus(
                success=True,
                elapsed_seconds=round(elapsed, 2),
                error=None
            )
        )

    except Exception as e:
        elapsed = time.time() - start_time
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": str(e),
                "error_type": type(e).__name__,
                "elapsed_seconds": round(elapsed, 2),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.post(
    "/company",
    response_model=CompanyAnalysisResponse,
    summary="회사 단독 분석",
    description="회사 채용 페이지 URL만으로 컬쳐핏 분석"
)
async def analyze_company(request: CompanyAnalysisRequest) -> CompanyAnalysisResponse:
    """회사 단독 컬쳐핏 분석"""
    start_time = time.time()

    try:
        result = await run_company_analysis(
            company_url=str(request.company_url),
            save_to_db=False
        )

        elapsed = time.time() - start_time

        return CompanyAnalysisResponse(
            company=result["company"],
            status=AnalysisStatus(
                success=True,
                elapsed_seconds=round(elapsed, 2),
                error=None
            )
        )

    except Exception as e:
        elapsed = time.time() - start_time
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": str(e),
                "error_type": type(e).__name__,
                "elapsed_seconds": round(elapsed, 2)
            }
        )


@router.post(
    "/applicant",
    response_model=ApplicantAnalysisResponse,
    summary="구직자 단독 분석",
    description="구직자 PDF S3 키로 프로필 분석"
)
async def analyze_applicant(request: ApplicantAnalysisRequest) -> ApplicantAnalysisResponse:
    """구직자 단독 프로필 분석"""
    start_time = time.time()

    try:
        result = await run_applicant_analysis(
            s3_keys=request.s3_keys,
            applicant_name=request.applicant_name,
            save_to_db=False
        )

        elapsed = time.time() - start_time

        return ApplicantAnalysisResponse(
            applicant=result["applicant"],
            status=AnalysisStatus(
                success=True,
                elapsed_seconds=round(elapsed, 2),
                error=None
            )
        )

    except Exception as e:
        elapsed = time.time() - start_time
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": str(e),
                "error_type": type(e).__name__,
                "elapsed_seconds": round(elapsed, 2)
            }
        )


@router.get(
    "/health",
    summary="헬스체크",
    description="API 서버 상태 확인"
)
async def health_check() -> dict[str, Any]:
    """API 서버 헬스체크"""
    return {
        "status": "healthy",
        "service": "culture-fit-analysis",
        "timestamp": datetime.now().isoformat()
    }
