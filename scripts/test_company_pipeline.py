#!/usr/bin/env python3
"""
회사 컬쳐핏 파이프라인 E2E 테스트 스크립트

사용법:
    python scripts/test_company_pipeline.py "https://example.com/jobs/123"
    python scripts/test_company_pipeline.py "https://example.com/jobs/123" --output result.json
    python scripts/test_company_pipeline.py "https://example.com/jobs/123" --verbose

파이프라인 흐름:
    1. URL 스크래핑 (Jina Reader)
    2. 회사 데이터 수집 (company_data_collect 프롬프트)
    3. 컬쳐핏 분석 (company_culture_analyze 프롬프트)
    4. 결과 JSON 출력
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from langchain_pipeline.chains.company_chain import CompanyAnalysisChain


async def run_pipeline(url: str, verbose: bool = False) -> dict:
    """
    회사 컬쳐핏 분석 파이프라인 실행

    Args:
        url: 채용공고 URL
        verbose: 상세 출력 여부

    Returns:
        분석 결과 딕셔너리
    """
    print("\n" + "=" * 60)
    print("🚀 회사 컬쳐핏 파이프라인 E2E 테스트")
    print("=" * 60)
    print(f"\n📍 입력 URL: {url}\n")

    # 체인 초기화 (DB 저장 비활성화)
    chain = CompanyAnalysisChain(save_to_db=False)

    try:
        # === Step 1: 스크래핑 ===
        print("-" * 40)
        print("📡 Step 1: 웹 스크래핑 (Jina Reader)")
        print("-" * 40)

        scraped_content = await chain.scrape_urls([url])

        if verbose:
            print(f"\n스크래핑 결과 (처음 1000자):\n{scraped_content[:1000]}...")
        else:
            print(f"✅ 스크래핑 완료 ({len(scraped_content):,} chars)")

        # === Step 2: 데이터 수집 ===
        print("\n" + "-" * 40)
        print("📋 Step 2: 회사 데이터 수집")
        print("-" * 40)

        company_data = await chain.collect_company_data(scraped_content)

        print(f"✅ 데이터 수집 완료")
        if verbose:
            print(f"\n수집된 데이터:\n{json.dumps(company_data, ensure_ascii=False, indent=2)}")
        else:
            # 요약 정보만 출력
            print(f"   - 회사명: {company_data.get('company_info', {}).get('company_name', 'N/A')}")
            print(f"   - 포지션: {company_data.get('job_info', {}).get('position_title', 'N/A')}")
            tech = company_data.get('tech_stack', {})
            tech_count = len(tech.get('languages', [])) + len(tech.get('frameworks', [])) + len(tech.get('tools', []))
            print(f"   - 기술스택: {tech_count}개 항목")

        # === Step 3: 컬쳐핏 분석 ===
        print("\n" + "-" * 40)
        print("🎯 Step 3: 컬쳐핏 분석")
        print("-" * 40)

        culture_analysis = await chain.analyze_culture(company_data)

        print(f"✅ 컬쳐핏 분석 완료")

        # 점수 요약 출력
        scores = culture_analysis.get('culture_fit_scores', {})
        print("\n📊 컬쳐핏 점수 (0-4):")
        for key in ['tech_culture', 'collaboration_style', 'growth_environment',
                    'work_life_balance', 'ownership_expectation']:
            score_data = scores.get(key, {})
            score = score_data.get('score', 'N/A')
            print(f"   - {key}: {score}")

        # 결과 통합
        result = {
            "source_url": url,
            "company_data": company_data,
            "culture_analysis": culture_analysis,
        }

        return result

    finally:
        chain.close()


def print_final_result(result: dict, verbose: bool = False):
    """최종 결과 출력"""
    print("\n" + "=" * 60)
    print("📄 최종 결과")
    print("=" * 60)

    culture = result.get('culture_analysis', {})

    # 전체 요약
    overall = culture.get('overall_summary', '')
    if overall:
        print(f"\n📝 전체 요약:\n{overall}")

    # 점수 상세
    scores = culture.get('culture_fit_scores', {})

    print("\n📊 컬쳐핏 점수 상세:")
    for key in ['tech_culture', 'collaboration_style', 'growth_environment',
                'work_life_balance', 'ownership_expectation']:
        score_data = scores.get(key, {})
        score = score_data.get('score', 'N/A')
        summary = score_data.get('summary', '')
        evidence = score_data.get('evidence', [])

        print(f"\n   [{key}] 점수: {score}/4")
        if summary:
            print(f"   요약: {summary}")
        if evidence and verbose:
            print(f"   근거: {evidence[:2]}")  # 최대 2개만

    if verbose:
        print("\n" + "-" * 40)
        print("전체 JSON 결과:")
        print("-" * 40)
        print(json.dumps(result, ensure_ascii=False, indent=2))


async def main():
    parser = argparse.ArgumentParser(description="회사 컬쳐핏 파이프라인 E2E 테스트")
    parser.add_argument("url", help="채용공고 URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 출력")
    parser.add_argument("--output", "-o", help="결과를 저장할 JSON 파일 경로")

    args = parser.parse_args()

    try:
        result = await run_pipeline(args.url, verbose=args.verbose)

        print_final_result(result, verbose=args.verbose)

        # 파일 저장 (옵션)
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"\n✅ 결과 저장됨: {output_path}")

        print("\n" + "=" * 60)
        print("✅ E2E 테스트 완료!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
