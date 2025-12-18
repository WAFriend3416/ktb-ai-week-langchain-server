"""
Gemini 모델 기반 웹 스크래퍼

Gemini 모델이 URL에 직접 접근하여 데이터 추출
- 채용공고 페이지에서 필요한 정보 추출
- 회사 소개 페이지에서 인재상/문화 정보 추출
"""

from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from langchain_pipeline.config import GOOGLE_API_KEY
from langchain_pipeline.scrapers.base_scraper import BaseScraper, ScrapeResult


class GeminiScraper(BaseScraper):
    """Gemini 모델 기반 웹 스크래퍼"""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.0
    ):
        """
        Args:
            model_name: Gemini 모델명
            temperature: 생성 온도 (0.0 = 결정적)
        """
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=GOOGLE_API_KEY,
            temperature=temperature,
        )

        # 스크래핑용 시스템 프롬프트
        self.scrape_prompt = """당신은 웹 페이지에서 정보를 추출하는 전문가입니다.
주어진 URL의 웹 페이지 내용을 분석하여 다음 정보를 추출해주세요:

1. 페이지의 주요 텍스트 내용
2. 회사/조직 관련 정보 (있다면)
3. 채용 관련 정보 (있다면)
4. 인재상/문화 관련 정보 (있다면)

URL: {url}

추출된 내용을 구조화된 텍스트로 반환해주세요."""

    async def scrape(self, url: str) -> ScrapeResult:
        """
        단일 URL 스크래핑

        Args:
            url: 스크래핑할 URL

        Returns:
            ScrapeResult: 스크래핑 결과
        """
        if not self.validate_url(url):
            return ScrapeResult(
                url=url,
                content="",
                success=False,
                error_message="유효하지 않은 URL입니다."
            )

        try:
            prompt = self.scrape_prompt.format(url=url)
            message = HumanMessage(content=prompt)
            response = await self.llm.ainvoke([message])

            return ScrapeResult(
                url=url,
                content=response.content,
                success=True,
                metadata={"model": self.llm.model}
            )

        except Exception as e:
            return ScrapeResult(
                url=url,
                content="",
                success=False,
                error_message=str(e)
            )

    async def scrape_multiple(self, urls: list[str]) -> list[ScrapeResult]:
        """
        여러 URL 스크래핑

        Args:
            urls: URL 리스트

        Returns:
            스크래핑 결과 리스트
        """
        results = []
        for url in urls:
            result = await self.scrape(url)
            results.append(result)
        return results

    async def scrape_with_custom_prompt(
        self,
        url: str,
        custom_prompt: str
    ) -> ScrapeResult:
        """
        커스텀 프롬프트로 스크래핑

        Args:
            url: 스크래핑할 URL
            custom_prompt: 사용자 정의 프롬프트 (URL 변수 포함)

        Returns:
            ScrapeResult: 스크래핑 결과
        """
        if not self.validate_url(url):
            return ScrapeResult(
                url=url,
                content="",
                success=False,
                error_message="유효하지 않은 URL입니다."
            )

        try:
            prompt = custom_prompt.format(url=url)
            message = HumanMessage(content=prompt)
            response = await self.llm.ainvoke([message])

            return ScrapeResult(
                url=url,
                content=response.content,
                success=True,
                metadata={"model": self.llm.model, "custom_prompt": True}
            )

        except Exception as e:
            return ScrapeResult(
                url=url,
                content="",
                success=False,
                error_message=str(e)
            )
