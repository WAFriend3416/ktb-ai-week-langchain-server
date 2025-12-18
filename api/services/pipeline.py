"""
Culture-Fit Analysis Pipeline Service

핵심 비즈니스 로직:
- 회사 분석 + 구직자 분석: 병렬 실행 (asyncio.gather)
- 비교 분석: 순차 실행 (둘 다 완료 후)
"""

import asyncio
import time
from typing import Any, Optional

from api.langchain_pipeline.chains.company_chain import CompanyAnalysisChain
from api.langchain_pipeline.chains.applicant_chain import ApplicantAnalysisChain
from api.langchain_pipeline.chains.compare_chain import CultureFitCompareChain


async def run_full_analysis(
    company_url: str,
    applicant_s3_keys: list[str],
    applicant_name: Optional[str] = None,
    save_to_db: bool = False
) -> dict[str, Any]:
    """
    컬쳐핏 전체 분석 실행

    1. 회사 분석 + 구직자 분석: 병렬 실행 (asyncio.gather)
    2. 비교 분석: 순차 실행 (둘 다 완료 후)

    Args:
        company_url: 회사 채용 페이지 URL
        applicant_s3_keys: 구직자 PDF S3 키 목록
        applicant_name: 구직자 이름 (선택)
        save_to_db: DB 저장 여부

    Returns:
        {
            "company": 회사 분석 결과,
            "applicant": 구직자 분석 결과,
            "matching": 비교 분석 결과
        }
    """
    start_time = time.time()

    # 체인 초기화
    company_chain = CompanyAnalysisChain(save_to_db=save_to_db)
    applicant_chain = ApplicantAnalysisChain(save_to_db=save_to_db)
    compare_chain = CultureFitCompareChain()

    try:
        # ========================================
        # Step 1: 병렬 실행 (회사 + 구직자)
        # ========================================
        company_result, applicant_result = await asyncio.gather(
            company_chain.run(company_url),
            applicant_chain.run_from_s3(applicant_s3_keys, candidate_name=applicant_name),
            return_exceptions=True  # 하나가 실패해도 다른 하나 완료
        )

        # 에러 체크
        if isinstance(company_result, Exception):
            raise company_result
        if isinstance(applicant_result, Exception):
            raise applicant_result

        # ========================================
        # Step 2: 순차 실행 (비교 분석)
        # ========================================
        matching_result = await compare_chain.run(
            company_culture=company_result,
            applicant_profile=applicant_result
        )

        elapsed_time = time.time() - start_time

        return {
            "company": company_result,
            "applicant": applicant_result,
            "matching": matching_result,
            "_meta": {
                "elapsed_seconds": round(elapsed_time, 2),
                "parallel_execution": True,
                "company_url": company_url,
                "applicant_files": len(applicant_s3_keys)
            }
        }

    finally:
        # 리소스 정리
        company_chain.close()
        applicant_chain.close()


async def run_company_analysis(
    company_url: str,
    save_to_db: bool = False
) -> dict[str, Any]:
    """
    회사 단독 분석

    Args:
        company_url: 회사 채용 페이지 URL
        save_to_db: DB 저장 여부

    Returns:
        회사 컬쳐핏 분석 결과
    """
    start_time = time.time()
    chain = CompanyAnalysisChain(save_to_db=save_to_db)

    try:
        result = await chain.run(company_url)
        elapsed_time = time.time() - start_time

        return {
            "company": result,
            "_meta": {
                "elapsed_seconds": round(elapsed_time, 2),
                "company_url": company_url
            }
        }
    finally:
        chain.close()


async def run_applicant_analysis(
    s3_keys: list[str],
    applicant_name: Optional[str] = None,
    save_to_db: bool = False
) -> dict[str, Any]:
    """
    구직자 단독 분석

    Args:
        s3_keys: 구직자 PDF S3 키 목록
        applicant_name: 구직자 이름 (선택)
        save_to_db: DB 저장 여부

    Returns:
        구직자 프로필 분석 결과
    """
    start_time = time.time()
    chain = ApplicantAnalysisChain(save_to_db=save_to_db)

    try:
        result = await chain.run_from_s3(s3_keys, candidate_name=applicant_name)
        elapsed_time = time.time() - start_time

        return {
            "applicant": result,
            "_meta": {
                "elapsed_seconds": round(elapsed_time, 2),
                "files_count": len(s3_keys)
            }
        }
    finally:
        chain.close()
