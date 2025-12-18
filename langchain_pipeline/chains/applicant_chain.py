"""
구직자 분석 체인

파이프라인 흐름:
이력서/포트폴리오 텍스트 → 프로필 분석 → JSON 출력 (+ 선택적 DB 저장)
"""

import json
from typing import Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from langchain_pipeline.config import GOOGLE_API_KEY
from langchain_pipeline.utils.schema_loader import get_schema_for_prompt
from langchain_pipeline.utils.db_handler import DatabaseHandler
from langchain_pipeline.prompts import applicant_analyze


class ApplicantAnalysisChain:
    """구직자 분석 체인"""

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
        self.analyze_prompt = ChatPromptTemplate.from_messages([
            ("system", applicant_analyze.SYSTEM_MESSAGE),
            ("human", applicant_analyze.HUMAN_MESSAGE_TEMPLATE),
        ])

        self.json_parser = JsonOutputParser()

    async def analyze(self, resume_text: str) -> dict[str, Any]:
        """
        이력서/포트폴리오 분석

        Args:
            resume_text: 이력서 또는 포트폴리오 텍스트

        Returns:
            구직자 프로필 분석 결과 (JSON)
        """
        schema = get_schema_for_prompt("applicant_schema")

        chain = self.analyze_prompt | self.llm | self.json_parser

        result = await chain.ainvoke({
            "resume_text": resume_text,
            "output_schema": schema,
        })

        return result

    async def run(
        self,
        resume_text: str,
        candidate_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        전체 파이프라인 실행

        Args:
            resume_text: 이력서/포트폴리오 텍스트
            candidate_name: 구직자명 (옵션, 없으면 분석 결과에서 추출)

        Returns:
            최종 분석 결과
        """
        # 1. 프로필 분석
        profile = await self.analyze(resume_text)

        # 2. DB 저장 (옵션)
        if self.save_to_db and self.db:
            doc_id = self.db.save_applicant_profile(profile)
            profile["_id"] = doc_id

        return profile

    async def run_from_file(self, file_path: str) -> dict[str, Any]:
        """
        파일에서 이력서 로드 후 분석

        Args:
            file_path: 이력서 파일 경로 (txt, md 등)

        Returns:
            분석 결과
        """
        with open(file_path, "r", encoding="utf-8") as f:
            resume_text = f.read()

        return await self.run(resume_text)

    def close(self):
        """리소스 정리"""
        if self.db:
            self.db.close()
