"""
컬쳐핏 비교 체인

파이프라인 흐름:
회사 컬쳐핏 JSON + 구직자 컬쳐핏 JSON → 비교 분석 → 매칭 점수 출력
"""

import json
from typing import Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from langchain_pipeline.config import GOOGLE_API_KEY
from langchain_pipeline.utils.db_handler import DatabaseHandler
from langchain_pipeline.prompts import culture_compare


class CultureCompareChain:
    """컬쳐핏 비교 체인"""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.0,
        save_to_db: bool = True
    ):
        """
        Args:
            model_name: Gemini 모델명
            temperature: 생성 온도
            save_to_db: DB 저장 여부
        """
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=GOOGLE_API_KEY,
            temperature=temperature,
        )
        self.save_to_db = save_to_db
        self.db = DatabaseHandler() if save_to_db else None

        # 프롬프트 템플릿 설정
        self._setup_prompts()

    def _setup_prompts(self):
        """프롬프트 템플릿 초기화"""
        self.compare_prompt = ChatPromptTemplate.from_messages([
            ("system", culture_compare.SYSTEM_MESSAGE),
            ("human", culture_compare.HUMAN_MESSAGE_TEMPLATE),
        ])

        self.json_parser = JsonOutputParser()

    async def compare(
        self,
        company_culture: dict[str, Any],
        applicant_profile: dict[str, Any]
    ) -> dict[str, Any]:
        """
        회사-구직자 컬쳐핏 비교

        Args:
            company_culture: 회사 컬쳐핏 분석 결과
            applicant_profile: 구직자 프로필 분석 결과

        Returns:
            비교 분석 결과 (매칭 점수, 강점/약점 등)
        """
        chain = self.compare_prompt | self.llm | self.json_parser

        result = await chain.ainvoke({
            "company_culture": json.dumps(company_culture, ensure_ascii=False, indent=2),
            "applicant_profile": json.dumps(applicant_profile, ensure_ascii=False, indent=2),
        })

        return result

    async def run(
        self,
        company_culture: dict[str, Any],
        applicant_profile: dict[str, Any],
        company_name: Optional[str] = None,
        applicant_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        전체 비교 파이프라인 실행

        Args:
            company_culture: 회사 컬쳐핏 분석 결과
            applicant_profile: 구직자 프로필 분석 결과
            company_name: 회사명 (메타데이터용)
            applicant_name: 구직자명 (메타데이터용)

        Returns:
            최종 비교 결과
        """
        # 1. 비교 분석
        comparison = await self.compare(company_culture, applicant_profile)

        # 메타데이터 추가
        result = {
            "company_name": company_name or company_culture.get("company_meta", {}).get("company_name", "unknown"),
            "applicant_name": applicant_name or applicant_profile.get("profile_meta", {}).get("candidate_name", "unknown"),
            "comparison_result": comparison,
        }

        # 2. DB 저장 (옵션)
        if self.save_to_db and self.db:
            doc_id = self.db.save_comparison_result(result)
            result["_id"] = doc_id

        return result

    async def run_from_db(
        self,
        company_name: str,
        applicant_name: str
    ) -> dict[str, Any]:
        """
        DB에서 프로필 로드 후 비교

        Args:
            company_name: 회사명
            applicant_name: 구직자명

        Returns:
            비교 결과

        Raises:
            ValueError: 프로필을 찾을 수 없는 경우
        """
        if not self.db:
            raise ValueError("DB 핸들러가 초기화되지 않았습니다.")

        company_profile = self.db.get_company_profile(company_name)
        if not company_profile:
            raise ValueError(f"회사 프로필을 찾을 수 없습니다: {company_name}")

        applicant_profile = self.db.get_applicant_profile(applicant_name)
        if not applicant_profile:
            raise ValueError(f"구직자 프로필을 찾을 수 없습니다: {applicant_name}")

        return await self.run(
            company_culture=company_profile.get("culture_analysis", company_profile),
            applicant_profile=applicant_profile,
            company_name=company_name,
            applicant_name=applicant_name
        )

    def close(self):
        """리소스 정리"""
        if self.db:
            self.db.close()
