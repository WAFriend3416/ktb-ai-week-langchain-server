"""
API Request Schemas

컬쳐핏 분석 요청 스키마 정의
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional


class CultureFitRequest(BaseModel):
    """
    컬쳐핏 전체 분석 요청

    회사 URL + 구직자 PDF S3 키 → 병렬 분석 후 비교
    """
    company_url: HttpUrl = Field(
        ...,
        description="회사 채용 페이지 URL",
        examples=["https://toss.im/career/jobs"]
    )
    applicant_s3_keys: list[str] = Field(
        ...,
        description="구직자 PDF S3 키 목록 (이력서, 포트폴리오, 자기소개서)",
        examples=[["users/123/resume.pdf", "users/123/portfolio.pdf"]]
    )
    applicant_name: Optional[str] = Field(
        None,
        description="구직자 이름 (선택)",
        examples=["홍길동"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "company_url": "https://toss.im/career/jobs",
                    "applicant_s3_keys": [
                        "applicants/user123/resume.pdf",
                        "applicants/user123/portfolio.pdf",
                        "applicants/user123/essay.pdf"
                    ],
                    "applicant_name": "홍길동"
                }
            ]
        }
    }


class CompanyAnalysisRequest(BaseModel):
    """회사 단독 분석 요청"""
    company_url: HttpUrl = Field(..., description="회사 채용 페이지 URL")


class ApplicantAnalysisRequest(BaseModel):
    """구직자 단독 분석 요청"""
    s3_keys: list[str] = Field(..., description="구직자 PDF S3 키 목록")
    applicant_name: Optional[str] = Field(None, description="구직자 이름")
