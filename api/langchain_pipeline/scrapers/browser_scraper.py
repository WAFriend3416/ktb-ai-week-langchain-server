"""
Playwright 기반 웹 스크래퍼 (헤드리스)

브라우저 창 없이 백그라운드에서 웹페이지 텍스트 추출
"""

import asyncio
import re
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page

from api.langchain_pipeline.scrapers.base_scraper import BaseScraper, ScrapeResult


class BrowserScraper(BaseScraper):
    """
    Playwright 헤드리스 스크래퍼

    JavaScript 렌더링이 필요한 SPA 페이지도 처리 가능
    """

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Args:
            headless: 헤드리스 모드 (기본 True, 브라우저 창 안 뜸)
            timeout: 페이지 로드 타임아웃 (ms)
        """
        self.headless = headless
        self.timeout = timeout
        self._browser: Optional[Browser] = None
        self._playwright = None

    async def start(self):
        """브라우저 시작"""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless
            )

    async def close(self):
        """브라우저 종료"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def scrape(self, url: str) -> ScrapeResult:
        """
        단일 URL 스크래핑

        Args:
            url: 스크래핑할 URL

        Returns:
            ScrapeResult: 스크래핑 결과
        """
        await self.start()

        page: Optional[Page] = None
        try:
            page = await self._browser.new_page()

            # 페이지 로드 (networkidle 대신 load 사용 - SPA 사이트 타임아웃 방지)
            await page.goto(url, wait_until="load", timeout=self.timeout)

            # 추가 대기 (동적 콘텐츠 로딩)
            await asyncio.sleep(2)

            # 본문 텍스트 추출
            content = await page.evaluate("""
                () => {
                    // 불필요한 요소 제거
                    const selectorsToRemove = [
                        'script', 'style', 'noscript', 'iframe',
                        'nav', 'footer', 'header',
                        '[role="navigation"]', '[role="banner"]',
                        '.cookie-banner', '.popup', '.modal'
                    ];

                    selectorsToRemove.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => el.remove());
                    });

                    return document.body.innerText || '';
                }
            """)

            content = self._clean_text(content)

            return ScrapeResult(
                url=url,
                content=content,
                success=True,
            )

        except Exception as e:
            return ScrapeResult(
                url=url,
                content="",
                success=False,
                error_message=str(e),
            )

        finally:
            if page:
                await page.close()

    async def scrape_multiple(self, urls: list[str]) -> list[ScrapeResult]:
        """여러 URL 순차 스크래핑"""
        results = []
        for url in urls:
            result = await self.scrape(url)
            results.append(result)
        return results

    def _clean_text(self, text: str) -> str:
        """텍스트 정리"""
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\t+', ' ', text)

        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(line for line in lines if line)

        return text.strip()


# 편의 함수
async def scrape_url(url: str) -> ScrapeResult:
    """단일 URL 스크래핑"""
    scraper = BrowserScraper()
    try:
        return await scraper.scrape(url)
    finally:
        await scraper.close()


async def scrape_urls(urls: list[str]) -> list[ScrapeResult]:
    """여러 URL 스크래핑"""
    scraper = BrowserScraper()
    try:
        return await scraper.scrape_multiple(urls)
    finally:
        await scraper.close()


if __name__ == "__main__":
    import sys

    async def main():
        url = sys.argv[1] if len(sys.argv) > 1 else "https://toss.im/career/culture"
        print(f"Scraping: {url}\n")

        result = await scrape_url(url)

        if result.success:
            print(f"Content: {len(result.content)} chars")
            print(f"\n{result.content[:1500]}...")
        else:
            print(f"Error: {result.error_message}")

    asyncio.run(main())
