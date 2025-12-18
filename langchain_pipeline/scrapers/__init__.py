"""웹 스크래퍼 모듈"""

from langchain_pipeline.scrapers.base_scraper import BaseScraper, ScrapeResult
from langchain_pipeline.scrapers.jina_scraper import JinaScraper
from langchain_pipeline.scrapers.gemini_scraper import GeminiScraper
from langchain_pipeline.scrapers.browser_scraper import BrowserScraper

__all__ = [
    "BaseScraper",
    "ScrapeResult",
    "JinaScraper",
    "GeminiScraper",
    "BrowserScraper",
]
