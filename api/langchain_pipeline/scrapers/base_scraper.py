"""
웹 스크래퍼 추상 베이스 클래스

Strategy 패턴으로 다양한 스크래핑 방식 지원
- JinaScraper: Jina Reader API (현재 기본, SPA/동적 페이지 지원)
- GeminiScraper: Gemini 모델이 직접 URL 접근
- BrowserScraper: Playwright/ChromeDevTools (추후 확장)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScrapeResult:
    """스크래핑 결과"""
    url: str
    content: str
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[dict] = None


class BaseScraper(ABC):
    """웹 스크래퍼 추상 베이스 클래스"""

    @abstractmethod
    async def scrape(self, url: str) -> ScrapeResult:
        """
        URL에서 텍스트 추출

        Args:
            url: 스크래핑할 URL

        Returns:
            ScrapeResult: 스크래핑 결과
        """
        pass

    @abstractmethod
    async def scrape_multiple(self, urls: list[str]) -> list[ScrapeResult]:
        """
        여러 URL에서 텍스트 추출

        Args:
            urls: 스크래핑할 URL 리스트

        Returns:
            스크래핑 결과 리스트
        """
        pass

    def validate_url(self, url: str) -> bool:
        """URL 유효성 검사"""
        return url.startswith(("http://", "https://"))
