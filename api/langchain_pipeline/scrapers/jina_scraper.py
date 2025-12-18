"""
Jina Reader 기반 웹 스크래퍼

Jina Reader API를 사용하여 웹 페이지 텍스트 추출
- SPA/동적 페이지 자동 처리 (JavaScript 렌더링 포함)
- 깔끔한 Markdown 포맷 출력
- API 키 없이 무료 사용 가능
"""

import asyncio
from typing import Optional

import httpx

from api.langchain_pipeline.scrapers.base_scraper import BaseScraper, ScrapeResult


# Jina Reader API 엔드포인트
JINA_READER_URL = "https://r.jina.ai/"


class JinaScraper(BaseScraper):
    """Jina Reader 기반 웹 스크래퍼"""

    def __init__(
        self,
        timeout: float = 60.0,
        with_image_caption: bool = False,  # 기본값 False (401 오류 방지)
        api_key: Optional[str] = None
    ):
        """
        Args:
            timeout: 요청 타임아웃 (초)
            with_image_caption: 이미지 캡셔닝 활성화 여부
            api_key: Jina API 키 (옵션, rate limit 향상용)
        """
        self.timeout = timeout
        self.with_image_caption = with_image_caption
        self.api_key = api_key

    def _get_headers(self) -> dict:
        """요청 헤더 생성"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        # 이미지 캡셔닝 활성화
        if self.with_image_caption:
            headers["x-with-generated-alt"] = "true"

        # API 키가 있으면 추가 (rate limit 향상)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

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

        jina_url = f"{JINA_READER_URL}{url}"

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            ) as client:
                response = await client.get(jina_url, headers=self._get_headers())
                response.raise_for_status()

                content = response.text

                return ScrapeResult(
                    url=url,
                    content=content,
                    success=True,
                    metadata={
                        "scraper": "jina_reader",
                        "content_length": len(content),
                        "with_image_caption": self.with_image_caption
                    }
                )

        except httpx.TimeoutException:
            return ScrapeResult(
                url=url,
                content="",
                success=False,
                error_message=f"요청 타임아웃 ({self.timeout}초)"
            )
        except httpx.HTTPStatusError as e:
            return ScrapeResult(
                url=url,
                content="",
                success=False,
                error_message=f"HTTP 오류: {e.response.status_code}"
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
        여러 URL 스크래핑 (순차 처리, rate limit 고려)

        Args:
            urls: URL 리스트

        Returns:
            스크래핑 결과 리스트
        """
        results = []

        for url in urls:
            result = await self.scrape(url)
            results.append(result)

            # Rate limit 고려: URL 간 1초 대기
            if len(urls) > 1:
                await asyncio.sleep(1.0)

        return results
