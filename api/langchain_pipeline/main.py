"""
LangChain 파이프라인 메인 진입점

사용 예시:
    # 회사 분석
    python -m langchain_pipeline.main company --urls "https://example.com/jobs"

    # 구직자 분석
    python -m langchain_pipeline.main applicant --file resume.txt

    # 컬쳐핏 비교
    python -m langchain_pipeline.main compare --company "회사명" --applicant "구직자명"
"""

import asyncio
import argparse
import json
from typing import Optional

from api.langchain_pipeline.config import validate_config
from api.langchain_pipeline.chains.company_chain import CompanyAnalysisChain
from api.langchain_pipeline.chains.applicant_chain import ApplicantAnalysisChain
from api.langchain_pipeline.chains.compare_chain import CultureCompareChain


def print_json(data: dict, indent: int = 2):
    """JSON 예쁘게 출력"""
    print(json.dumps(data, ensure_ascii=False, indent=indent))


async def analyze_company(urls: list[str], save_to_db: bool = True):
    """회사 분석 실행"""
    print(f"🏢 회사 분석 시작...")
    print(f"   URLs: {urls}")

    chain = CompanyAnalysisChain(save_to_db=save_to_db)
    try:
        result = await chain.run(urls)
        print("\n✅ 분석 완료!")
        print_json(result)
        return result
    finally:
        chain.close()


async def analyze_applicant(
    resume_text: Optional[str] = None,
    file_path: Optional[str] = None,
    save_to_db: bool = True
):
    """구직자 분석 실행"""
    print(f"👤 구직자 분석 시작...")

    chain = ApplicantAnalysisChain(save_to_db=save_to_db)
    try:
        if file_path:
            print(f"   파일: {file_path}")
            result = await chain.run_from_file(file_path)
        elif resume_text:
            result = await chain.run(resume_text)
        else:
            raise ValueError("resume_text 또는 file_path 중 하나를 제공해야 합니다.")

        print("\n✅ 분석 완료!")
        print_json(result)
        return result
    finally:
        chain.close()


async def compare_culture(
    company_name: str,
    applicant_name: str,
    save_to_db: bool = True
):
    """컬쳐핏 비교 실행 (DB에서 로드)"""
    print(f"🔄 컬쳐핏 비교 시작...")
    print(f"   회사: {company_name}")
    print(f"   구직자: {applicant_name}")

    chain = CultureCompareChain(save_to_db=save_to_db)
    try:
        result = await chain.run_from_db(company_name, applicant_name)
        print("\n✅ 비교 완료!")
        print_json(result)
        return result
    finally:
        chain.close()


async def compare_culture_direct(
    company_culture: dict,
    applicant_profile: dict,
    save_to_db: bool = True
):
    """컬쳐핏 비교 실행 (직접 데이터 제공)"""
    print(f"🔄 컬쳐핏 비교 시작...")

    chain = CultureCompareChain(save_to_db=save_to_db)
    try:
        result = await chain.run(company_culture, applicant_profile)
        print("\n✅ 비교 완료!")
        print_json(result)
        return result
    finally:
        chain.close()


def main():
    """CLI 메인 함수"""
    parser = argparse.ArgumentParser(
        description="LangChain 컬쳐핏 분석 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 설정 검증
  python -m langchain_pipeline.main config

  # 회사 분석
  python -m langchain_pipeline.main company --urls "https://example.com/jobs"

  # 구직자 분석 (파일)
  python -m langchain_pipeline.main applicant --file resume.txt

  # 컬쳐핏 비교 (DB에서)
  python -m langchain_pipeline.main compare --company "회사명" --applicant "구직자명"
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="실행할 명령")

    # config 명령
    subparsers.add_parser("config", help="설정 검증")

    # company 명령
    company_parser = subparsers.add_parser("company", help="회사 분석")
    company_parser.add_argument("--urls", nargs="+", required=True, help="분석할 URL들")
    company_parser.add_argument("--no-db", action="store_true", help="DB 저장 안함")

    # applicant 명령
    applicant_parser = subparsers.add_parser("applicant", help="구직자 분석")
    applicant_parser.add_argument("--file", help="이력서 파일 경로")
    applicant_parser.add_argument("--text", help="이력서 텍스트 직접 입력")
    applicant_parser.add_argument("--no-db", action="store_true", help="DB 저장 안함")

    # compare 명령
    compare_parser = subparsers.add_parser("compare", help="컬쳐핏 비교")
    compare_parser.add_argument("--company", required=True, help="회사명")
    compare_parser.add_argument("--applicant", required=True, help="구직자명")
    compare_parser.add_argument("--no-db", action="store_true", help="DB 저장 안함")

    args = parser.parse_args()

    if args.command == "config":
        result = validate_config()
        print("📋 설정 검증 결과:")
        print_json(result)

    elif args.command == "company":
        asyncio.run(analyze_company(
            urls=args.urls,
            save_to_db=not args.no_db
        ))

    elif args.command == "applicant":
        asyncio.run(analyze_applicant(
            resume_text=args.text,
            file_path=args.file,
            save_to_db=not args.no_db
        ))

    elif args.command == "compare":
        asyncio.run(compare_culture(
            company_name=args.company,
            applicant_name=args.applicant,
            save_to_db=not args.no_db
        ))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
