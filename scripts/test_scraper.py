#!/usr/bin/env python3
"""
Jina Reader 기반 웹 스크래퍼 테스트 스크립트

사용법:
    python scripts/test_scraper.py "https://example.com/jobs/123"
    python scripts/test_scraper.py "https://example.com/jobs/123" --with-ocr
    python scripts/test_scraper.py "https://example.com/jobs/123" --output result.txt
"""

import argparse
import asyncio
import base64
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

import google.generativeai as genai
import os

# Gemini 설정
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Jina Reader API
JINA_READER_URL = "https://r.jina.ai/"


class JinaReaderScraper:
    """Jina Reader 기반 웹 스크래퍼"""

    def __init__(self, enable_ocr: bool = False):
        self.enable_ocr = enable_ocr
        self.client = httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )

        if enable_ocr and GOOGLE_API_KEY:
            genai.configure(api_key=GOOGLE_API_KEY)
            self.vision_model = genai.GenerativeModel("gemini-2.0-flash-exp")
        else:
            self.vision_model = None

    async def scrape(self, url: str) -> dict:
        """
        Jina Reader를 사용하여 URL에서 텍스트 추출

        Returns:
            {
                "url": str,
                "jina_text": str,
                "image_texts": list[dict],  # OCR 활성화 시
                "combined_text": str,
                "metadata": dict
            }
        """
        print(f"\n🔍 스크래핑 시작: {url}")

        # 1. Jina Reader로 텍스트 추출
        jina_url = f"{JINA_READER_URL}{url}"
        print(f"📡 Jina Reader 호출 중...")

        try:
            response = await self.client.get(jina_url)
            response.raise_for_status()
            jina_text = response.text
            print(f"✅ Jina Reader 성공 ({len(jina_text):,} chars)")
        except Exception as e:
            return {"error": f"Jina Reader 실패: {e}", "url": url}

        # 2. 이미지 OCR (옵션)
        image_texts = []
        if self.enable_ocr and self.vision_model:
            print(f"🔄 이미지 OCR 진행 중...")
            image_texts = await self._extract_and_ocr_images(url)
            ocr_count = sum(1 for t in image_texts if t.get("text"))
            print(f"✅ OCR 완료: {ocr_count}개 이미지에서 텍스트 추출")

        # 3. 텍스트 통합
        combined_text = self._combine_texts(jina_text, image_texts)

        return {
            "url": url,
            "jina_text": jina_text,
            "image_texts": image_texts,
            "combined_text": combined_text,
            "metadata": {
                "jina_length": len(jina_text),
                "image_count": len(image_texts),
                "ocr_success_count": sum(1 for t in image_texts if t.get("text")),
                "combined_length": len(combined_text),
            }
        }

    async def _extract_and_ocr_images(self, url: str) -> list[dict]:
        """원본 페이지에서 이미지 추출 후 OCR"""
        results = []

        try:
            # 원본 페이지 HTML 가져오기
            response = await self.client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # 이미지 URL 추출
            image_urls = self._extract_image_urls(soup, url)
            print(f"📷 이미지 발견: {len(image_urls)}개")

            # 이미지 OCR
            for i, img_url in enumerate(image_urls[:10]):  # 최대 10개
                try:
                    print(f"  OCR [{i+1}/{min(len(image_urls), 10)}]: {img_url[:50]}...")

                    # 이미지 다운로드
                    if img_url.startswith("data:image"):
                        image_data = base64.b64decode(img_url.split(",")[1])
                    else:
                        img_response = await self.client.get(img_url)
                        img_response.raise_for_status()
                        image_data = img_response.content

                    # Gemini Vision OCR
                    text = await self._gemini_ocr(image_data)

                    results.append({
                        "url": img_url,
                        "text": text,
                        "success": bool(text)
                    })

                except Exception as e:
                    results.append({
                        "url": img_url,
                        "text": "",
                        "success": False,
                        "error": str(e)
                    })

        except Exception as e:
            print(f"⚠️ 이미지 추출 실패: {e}")

        return results

    def _extract_image_urls(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """이미지 URL 추출"""
        image_urls = []

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if not src:
                continue

            # 상대 경로를 절대 경로로
            full_url = urljoin(base_url, src)

            # 필터링: 너무 작은 이미지, 아이콘 등 제외
            if self._is_valid_image_url(full_url, img):
                image_urls.append(full_url)

        return list(set(image_urls))  # 중복 제거

    def _is_valid_image_url(self, url: str, img_tag) -> bool:
        """유효한 이미지인지 확인"""
        # 확장자 체크
        valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
        parsed = urlparse(url)

        # base64 이미지
        if url.startswith("data:image"):
            return True

        # 파일 확장자 또는 이미지 서비스 URL
        if not any(parsed.path.lower().endswith(ext) for ext in valid_extensions):
            if not any(x in url for x in ['image', 'img', 'photo', 'pic', 'cdn']):
                return False

        # 크기 체크 (너무 작은 이미지 제외)
        width = img_tag.get("width", "0")
        height = img_tag.get("height", "0")
        try:
            if int(width) < 100 or int(height) < 100:
                return False
        except (ValueError, TypeError):
            pass  # 크기 정보 없으면 일단 포함

        # 아이콘/로고 패턴 제외
        skip_patterns = ['icon', 'logo', 'avatar', 'emoji', 'button', 'arrow']
        url_lower = url.lower()
        if any(p in url_lower for p in skip_patterns):
            return False

        return True

    async def _gemini_ocr(self, image_data: bytes) -> str:
        """Gemini Vision으로 이미지에서 텍스트 추출"""
        try:
            image_part = {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_data).decode()
            }

            prompt = """이 이미지에서 모든 텍스트를 추출해주세요.

규칙:
- 이미지에 보이는 모든 텍스트를 그대로 추출
- 레이아웃/순서를 최대한 유지
- 텍스트가 없으면 빈 문자열 반환
- 설명이나 해석 없이 텍스트만 출력"""

            response = self.vision_model.generate_content([prompt, image_part])

            return response.text.strip() if response.text else ""

        except Exception as e:
            print(f"    ⚠️ OCR 오류: {e}")
            return ""

    def _combine_texts(self, jina_text: str, image_texts: list[dict]) -> str:
        """Jina Reader 텍스트와 이미지 OCR 텍스트 통합"""
        parts = [jina_text]

        ocr_texts = [t["text"] for t in image_texts if t.get("text")]
        if ocr_texts:
            parts.append("\n\n" + "=" * 50)
            parts.append("[이미지에서 추출된 텍스트]")
            parts.append("=" * 50 + "\n")
            parts.extend(ocr_texts)

        return "\n\n".join(parts)

    async def close(self):
        await self.client.aclose()


async def main():
    parser = argparse.ArgumentParser(description="Jina Reader 기반 웹 텍스트 추출")
    parser.add_argument("url", help="스크래핑할 URL")
    parser.add_argument("--with-ocr", action="store_true", help="이미지 OCR 활성화")
    parser.add_argument("--output", "-o", help="결과를 저장할 파일 경로")

    args = parser.parse_args()

    # OCR 사용 시 API 키 확인
    if args.with_ocr and not GOOGLE_API_KEY:
        print("⚠️ GOOGLE_API_KEY가 설정되지 않았습니다. OCR 없이 진행합니다.")
        args.with_ocr = False

    scraper = JinaReaderScraper(enable_ocr=args.with_ocr)

    try:
        result = await scraper.scrape(args.url)

        if "error" in result:
            print(f"\n❌ 오류: {result['error']}")
            return

        # 결과 출력
        print("\n" + "=" * 60)
        print("📄 추출 결과")
        print("=" * 60)
        print(f"\n📊 메타데이터:")
        print(f"   - Jina Reader 텍스트: {result['metadata']['jina_length']:,} chars")
        if args.with_ocr:
            print(f"   - 이미지 수: {result['metadata']['image_count']}개")
            print(f"   - OCR 성공: {result['metadata']['ocr_success_count']}개")
        print(f"   - 총 텍스트: {result['metadata']['combined_length']:,} chars")

        print("\n" + "-" * 60)
        print("📝 추출된 텍스트:")
        print("-" * 60)
        print(result["combined_text"][:5000])  # 처음 5000자만 출력

        if len(result["combined_text"]) > 5000:
            print(f"\n... (총 {len(result['combined_text']):,}자 중 5000자만 표시)")

        # 파일 저장 (옵션)
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(result["combined_text"], encoding="utf-8")
            print(f"\n✅ 결과 저장됨: {output_path}")

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
