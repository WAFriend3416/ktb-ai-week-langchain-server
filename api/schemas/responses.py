"""
API Response Schemas

컬쳐핏 분석 응답 스키마 정의
"""

from pydantic import BaseModel, Field
from typing import Any, Optional


class AnalysisStatus(BaseModel):
    """분석 상태"""
    success: bool
    elapsed_seconds: float
    error: Optional[str] = None


class CultureFitResponse(BaseModel):
    """
    컬쳐핏 전체 분석 응답

    회사 분석 + 구직자 분석 + 매칭 결과
    """
    company: dict[str, Any] = Field(
        ...,
        description="회사 컬쳐핏 분석 결과"
    )
    applicant: dict[str, Any] = Field(
        ...,
        description="구직자 프로필 분석 결과"
    )
    matching: dict[str, Any] = Field(
        ...,
        description="컬쳐핏 매칭/비교 결과"
    )
    status: AnalysisStatus = Field(
        ...,
        description="분석 상태 정보"
    )


class CompanyAnalysisResponse(BaseModel):
    """회사 단독 분석 응답"""
    company: dict[str, Any]
    status: AnalysisStatus


class ApplicantAnalysisResponse(BaseModel):
    """구직자 단독 분석 응답"""
    applicant: dict[str, Any]
    status: AnalysisStatus


class ErrorResponse(BaseModel):
    """에러 응답"""
    detail: str
    error_type: str
    timestamp: str
