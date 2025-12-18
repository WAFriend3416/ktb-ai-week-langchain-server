"""
회사 컬쳐핏 분석 체인

파이프라인 흐름:
URL 입력 → 스크래핑 → 데이터 수집 → 컬쳐핏 분석 → MongoDB 저장
"""

import json
from typing import Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from langchain_pipeline.config import GOOGLE_API_KEY
from langchain_pipeline.scrapers.gemini_scraper import GeminiScraper
from langchain_pipeline.utils.schema_loader import get_schema_for_prompt
from langchain_pipeline.utils.db_handler import DatabaseHandler
from langchain_pipeline.prompts import company_data_collect, company_culture_analyze


class CompanyAnalysisChain:
    """회사 컬쳐핏 분석 체인"""

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
        self.scraper = GeminiScraper(model_name=model_name)
        self.save_to_db = save_to_db
        self.db = DatabaseHandler() if save_to_db else None

        # 프롬프트 템플릿 설정
        self._setup_prompts()

    def _setup_prompts(self):
        """프롬프트 템플릿 초기화"""
        # 데이터 수집 프롬프트
        self.collect_prompt = ChatPromptTemplate.from_messages([
            ("system", company_data_collect.SYSTEM_MESSAGE),
            ("human", company_data_collect.HUMAN_MESSAGE_TEMPLATE),
        ])

        # 컬쳐핏 분석 프롬프트
        self.analyze_prompt = ChatPromptTemplate.from_messages([
            ("system", company_culture_analyze.SYSTEM_MESSAGE),
            ("human", company_culture_analyze.HUMAN_MESSAGE_TEMPLATE),
        ])

        # JSON 파서
        self.json_parser = JsonOutputParser()

    async def scrape_urls(self, urls: list[str]) -> str:
        """
        URL들에서 텍스트 추출

        Args:
            urls: 스크래핑할 URL 리스트

        Returns:
            결합된 스크래핑 결과 텍스트
        """
        results = await self.scraper.scrape_multiple(urls)
        contents = []

        for result in results:
            if result.success:
                contents.append(f"=== {result.url} ===\n{result.content}")
            else:
                contents.append(f"=== {result.url} (실패) ===\n{result.error_message}")

        return "\n\n".join(contents)

    async def collect_company_data(self, scraped_content: str) -> dict[str, Any]:
        """
        스크래핑 결과에서 회사 데이터 수집

        Args:
            scraped_content: 스크래핑된 텍스트

        Returns:
            구조화된 회사 데이터
        """
        schema = get_schema_for_prompt("company_schema")

        chain = self.collect_prompt | self.llm | self.json_parser

        result = await chain.ainvoke({
            "scraped_content": scraped_content,
            "output_schema": schema,
        })

        return result

    async def analyze_culture(self, company_data: dict[str, Any]) -> dict[str, Any]:
        """
        회사 데이터 기반 컬쳐핏 분석

        Args:
            company_data: 수집된 회사 데이터

        Returns:
            컬쳐핏 분석 결과
        """
        schema = get_schema_for_prompt("company_schema")

        chain = self.analyze_prompt | self.llm | self.json_parser

        result = await chain.ainvoke({
            "company_data": json.dumps(company_data, ensure_ascii=False, indent=2),
            "output_schema": schema,
        })

        return result

    async def run(
        self,
        urls: list[str],
        company_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        전체 파이프라인 실행

        Args:
            urls: 회사 관련 URL 리스트 (채용공고, 회사 페이지 등)
            company_name: 회사명 (옵션, 없으면 분석 결과에서 추출)

        Returns:
            최종 분석 결과
        """
        # 1. URL 스크래핑
        scraped_content = await self.scrape_urls(urls)

        # 2. 회사 데이터 수집
        company_data = await self.collect_company_data(scraped_content)

        # 3. 컬쳐핏 분석
        culture_analysis = await self.analyze_culture(company_data)

        # 결과 통합
        result = {
            "source_urls": urls,
            "company_data": company_data,
            "culture_analysis": culture_analysis,
        }

        # 4. DB 저장 (옵션)
        if self.save_to_db and self.db:
            doc_id = self.db.save_company_profile(result)
            result["_id"] = doc_id

        return result

    def close(self):
        """리소스 정리"""
        if self.db:
            self.db.close()
