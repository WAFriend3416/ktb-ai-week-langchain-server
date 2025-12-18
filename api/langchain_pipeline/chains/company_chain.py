"""
회사 컬쳐핏 분석 체인

파이프라인 흐름:
채용공고 URL → Playwright 스크래핑 → 회사 매칭 → 추가 URL 스크래핑 →
데이터 수집 → 컬쳐핏 분석 → MongoDB 저장

지원 회사: 현대오토에버, 업스테이지, 토스
"""

import json
import re
from typing import Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


def parse_json_with_markdown(text: str) -> dict:
    """마크다운 코드블록이 포함된 JSON 파싱"""
    # AIMessage인 경우 content 추출
    if hasattr(text, 'content'):
        text = text.content

    text = str(text).strip()

    # ```json ... ``` 또는 ``` ... ``` 제거
    if "```json" in text:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            text = match.group(1)
    elif "```" in text:
        match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            text = match.group(1)

    return json.loads(text)

from api.langchain_pipeline.config import (
    GOOGLE_API_KEY,
    COMPANY_KEYWORDS,
    match_company,
    get_company_sources,
)
from api.langchain_pipeline.scrapers.browser_scraper import BrowserScraper
from api.langchain_pipeline.utils.schema_loader import get_schema_for_prompt
from api.langchain_pipeline.utils.db_handler import DatabaseHandler
from api.langchain_pipeline.prompts import company_data_collect, company_culture_analyze


class UnsupportedCompanyError(Exception):
    """지원하지 않는 회사 에러"""
    pass


class CompanyAnalysisChain:
    """회사 컬쳐핏 분석 체인"""

    SUPPORTED_COMPANIES = list(COMPANY_KEYWORDS.keys())

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
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
        self.scraper = BrowserScraper(headless=True)
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

        chain = self.collect_prompt | self.llm

        response = await chain.ainvoke({
            "scraped_content": scraped_content,
            "output_schema": schema,
        })

        return parse_json_with_markdown(response)

    async def analyze_culture(self, company_data: dict[str, Any]) -> dict[str, Any]:
        """
        회사 데이터 기반 컬쳐핏 분석

        Args:
            company_data: 수집된 회사 데이터

        Returns:
            컬쳐핏 분석 결과
        """
        schema = get_schema_for_prompt("company_schema")

        chain = self.analyze_prompt | self.llm

        response = await chain.ainvoke({
            "company_data": json.dumps(company_data, ensure_ascii=False, indent=2),
            "output_schema": schema,
        })

        return parse_json_with_markdown(response)

    async def run(
        self,
        job_posting_url: str,
    ) -> dict[str, Any]:
        """
        전체 파이프라인 실행

        Args:
            job_posting_url: 채용공고 URL

        Returns:
            최종 분석 결과

        Raises:
            UnsupportedCompanyError: 지원하지 않는 회사인 경우
        """
        print(f"📍 채용공고 URL: {job_posting_url}")

        # 1. 채용공고 스크래핑
        print("🔄 채용공고 스크래핑 중...")
        job_result = await self.scraper.scrape(job_posting_url)

        if not job_result.success:
            raise Exception(f"채용공고 스크래핑 실패: {job_result.error_message}")

        job_content = job_result.content

        # 2. 회사 매칭
        company_name = match_company(job_content)

        if company_name is None:
            await self.scraper.close()
            raise UnsupportedCompanyError(
                f"지원하지 않는 회사입니다. 지원 회사: {', '.join(self.SUPPORTED_COMPANIES)}"
            )

        print(f"🏢 회사 매칭: {company_name}")

        # 3. 추가 URL 스크래핑
        additional_urls = get_company_sources(company_name)
        print(f"📄 추가 소스 {len(additional_urls)}개 스크래핑 중...")

        all_contents = [f"=== 채용공고: {job_posting_url} ===\n{job_content}"]

        for url in additional_urls:
            print(f"   - {url}")
            result = await self.scraper.scrape(url)
            if result.success:
                all_contents.append(f"=== {url} ===\n{result.content}")
            else:
                print(f"     ⚠️ 실패: {result.error_message}")

        await self.scraper.close()

        # 4. 전체 텍스트 결합
        scraped_content = "\n\n".join(all_contents)
        print(f"📝 총 텍스트 길이: {len(scraped_content)} chars")

        # 5. 회사 데이터 수집
        print("🔍 회사 데이터 수집 중...")
        company_data = await self.collect_company_data(scraped_content)

        # 6. 컬쳐핏 분석
        print("📊 컬쳐핏 분석 중...")
        culture_analysis = await self.analyze_culture(company_data)

        # 결과: 컬쳐핏 분석 결과만 반환 (중복 제거)
        # culture_analysis에 메타 정보 추가
        result = culture_analysis
        result["_meta"] = {
            "company_name": company_name,
            "job_posting_url": job_posting_url,
            "source_urls": [job_posting_url] + additional_urls,
        }

        # 7. DB 저장 (옵션)
        if self.save_to_db and self.db:
            doc_id = self.db.save_company_profile(result)
            result["_id"] = doc_id
            print(f"💾 DB 저장 완료: {doc_id}")

        print("✅ 분석 완료!")
        return result

    def close(self):
        """리소스 정리"""
        if self.db:
            self.db.close()
