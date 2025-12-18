"""
LangChain 체인 테스트

주의: 실제 API 호출이 필요한 통합 테스트입니다.
GOOGLE_API_KEY 환경변수가 설정되어 있어야 합니다.
"""

import pytest
import asyncio
import json
from pathlib import Path

# 프로젝트 루트를 path에 추가
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_pipeline.config import validate_config, SCHEMAS_DIR
from langchain_pipeline.utils.schema_loader import (
    load_schema,
    get_schema_for_prompt,
    list_available_schemas
)


class TestConfig:
    """설정 테스트"""

    def test_validate_config(self):
        """설정 검증 테스트"""
        result = validate_config()
        assert "valid" in result
        assert "errors" in result
        assert "config" in result

    def test_schemas_dir_exists(self):
        """스키마 디렉토리 존재 확인"""
        assert SCHEMAS_DIR.exists()


class TestSchemaLoader:
    """스키마 로더 테스트"""

    def test_list_available_schemas(self):
        """스키마 목록 조회"""
        schemas = list_available_schemas()
        assert isinstance(schemas, list)
        assert "applicant_schema.json" in schemas

    def test_load_applicant_schema(self):
        """구직자 스키마 로딩"""
        schema = load_schema("applicant_schema")
        assert "schema_version" in schema
        assert "profile_meta" in schema
        assert "scoring_axes" in schema

    def test_load_company_schema(self):
        """회사 스키마 로딩"""
        schema = load_schema("company_schema")
        assert "schema_version" in schema

    def test_get_schema_for_prompt(self):
        """프롬프트용 스키마 문자열 반환"""
        schema_str = get_schema_for_prompt("applicant_schema")
        assert isinstance(schema_str, str)
        assert "schema_version" in schema_str

    def test_load_nonexistent_schema(self):
        """존재하지 않는 스키마 로딩 시 예외"""
        with pytest.raises(FileNotFoundError):
            load_schema("nonexistent_schema")


class TestPromptTemplates:
    """프롬프트 템플릿 테스트"""

    def test_company_data_collect_prompt(self):
        """회사 데이터 수집 프롬프트 로딩"""
        from langchain_pipeline.prompts import company_data_collect

        assert hasattr(company_data_collect, "SYSTEM_MESSAGE")
        assert hasattr(company_data_collect, "HUMAN_MESSAGE_TEMPLATE")
        assert hasattr(company_data_collect, "INPUT_VARIABLES")

    def test_applicant_analyze_prompt(self):
        """구직자 분석 프롬프트 로딩"""
        from langchain_pipeline.prompts import applicant_analyze

        assert hasattr(applicant_analyze, "SYSTEM_MESSAGE")
        assert hasattr(applicant_analyze, "HUMAN_MESSAGE_TEMPLATE")
        assert "resume_text" in applicant_analyze.INPUT_VARIABLES

    def test_culture_compare_prompt(self):
        """컬쳐핏 비교 프롬프트 로딩"""
        from langchain_pipeline.prompts import culture_compare

        assert hasattr(culture_compare, "SYSTEM_MESSAGE")
        assert hasattr(culture_compare, "HUMAN_MESSAGE_TEMPLATE")
        assert "company_culture" in culture_compare.INPUT_VARIABLES
        assert "applicant_profile" in culture_compare.INPUT_VARIABLES


class TestScrapers:
    """스크래퍼 테스트"""

    def test_base_scraper_url_validation(self):
        """URL 유효성 검사"""
        from langchain_pipeline.scrapers.base_scraper import BaseScraper

        # BaseScraper는 추상 클래스이므로 임시 구현
        class TestScraper(BaseScraper):
            async def scrape(self, url):
                pass
            async def scrape_multiple(self, urls):
                pass

        scraper = TestScraper()
        assert scraper.validate_url("https://example.com")
        assert scraper.validate_url("http://example.com")
        assert not scraper.validate_url("ftp://example.com")
        assert not scraper.validate_url("invalid-url")

    def test_browser_scraper_not_implemented(self):
        """BrowserScraper 미구현 확인"""
        from langchain_pipeline.scrapers.browser_scraper import BrowserScraper

        scraper = BrowserScraper()
        with pytest.raises(NotImplementedError):
            asyncio.run(scraper.scrape("https://example.com"))


# =====================================================
# 통합 테스트 (API 키 필요)
# pytest -m integration 으로 실행
# =====================================================

@pytest.mark.integration
class TestIntegration:
    """통합 테스트 (실제 API 호출)"""

    @pytest.fixture
    def check_api_key(self):
        """API 키 확인"""
        result = validate_config()
        if not result["valid"]:
            pytest.skip("GOOGLE_API_KEY가 설정되지 않았습니다.")

    @pytest.mark.asyncio
    async def test_gemini_scraper(self, check_api_key):
        """Gemini 스크래퍼 테스트"""
        from langchain_pipeline.scrapers.gemini_scraper import GeminiScraper

        scraper = GeminiScraper()
        result = await scraper.scrape("https://www.google.com")

        assert result.url == "https://www.google.com"
        # 성공/실패 여부는 네트워크 상태에 따라 다를 수 있음


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
