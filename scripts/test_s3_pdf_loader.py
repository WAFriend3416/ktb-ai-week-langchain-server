#!/usr/bin/env python3
"""
S3 PDF 로더 테스트 스크립트

사용법:
    # S3 설정 확인
    python scripts/test_s3_pdf_loader.py --check-config

    # S3에서 PDF 로드 테스트 (실제 S3 파일 필요)
    python scripts/test_s3_pdf_loader.py --load-pdf --s3-key "test123/resume.pdf"

    # 구직자 분석 E2E 테스트 (S3 PDF)
    python scripts/test_s3_pdf_loader.py --analyze --s3-key "test123/resume.pdf" -o result.json

필수 환경변수 (.env):
    GOOGLE_API_KEY=xxx
    S3_BUCKET_NAME=xxx
    S3_REGION=ap-northeast-2
    AWS_ACCESS_KEY_ID=xxx (또는 IAM Role)
    AWS_SECRET_ACCESS_KEY=xxx (또는 IAM Role)
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


def check_config():
    """설정 확인"""
    from langchain_pipeline.config import validate_config

    print("\n" + "=" * 60)
    print("🔧 S3 PDF 로더 설정 확인")
    print("=" * 60)

    result = validate_config(require_s3=True)

    print("\n📋 설정 값:")
    for key, value in result["config"].items():
        print(f"   {key}: {value}")

    if result["errors"]:
        print("\n❌ 오류:")
        for error in result["errors"]:
            print(f"   - {error}")

    if result.get("warnings"):
        print("\n⚠️ 경고:")
        for warning in result["warnings"]:
            print(f"   - {warning}")

    if result["valid"]:
        print("\n✅ 설정이 유효합니다!")
    else:
        print("\n❌ 설정에 문제가 있습니다. .env 파일을 확인하세요.")

    return result["valid"]


def test_load_pdf(s3_key: str):
    """S3 PDF 로드 테스트"""
    from langchain_pipeline.loaders.s3_pdf_loader import S3PDFLoader
    from langchain_pipeline.config import (
        S3_BUCKET_NAME, S3_REGION, GOOGLE_API_KEY,
        AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
    )

    print("\n" + "=" * 60)
    print("📄 S3 PDF 로드 테스트")
    print("=" * 60)

    loader = S3PDFLoader(
        bucket_name=S3_BUCKET_NAME,
        gemini_api_key=GOOGLE_API_KEY,
        aws_region=S3_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY or None,
    )

    print(f"\n📍 S3 Key: {s3_key}")
    print(f"📦 Bucket: {S3_BUCKET_NAME}")

    try:
        gemini_file = loader.load_from_s3(s3_key)

        print(f"\n✅ Gemini 업로드 성공!")
        print(f"   Name: {gemini_file.name}")
        print(f"   URI: {gemini_file.uri}")
        print(f"   State: {gemini_file.state}")
        print(f"   Display Name: {gemini_file.display_name}")

        # 정리
        loader.delete_file(gemini_file)
        print(f"\n🗑️ Gemini 파일 삭제됨")

        return gemini_file

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        return None


async def test_analyze(s3_key: str, output_file: str = None):
    """구직자 분석 E2E 테스트"""
    from langchain_pipeline.chains.applicant_chain import ApplicantAnalysisChain

    print("\n" + "=" * 60)
    print("🎯 구직자 분석 E2E 테스트 (S3 PDF)")
    print("=" * 60)

    chain = ApplicantAnalysisChain(save_to_db=False)

    try:
        print(f"\n📍 S3 Key: {s3_key}")
        print("⏳ 분석 중... (S3 다운로드 → Gemini 업로드 → 분석)")

        result = await chain.run_from_s3(s3_key)

        print("\n✅ 분석 완료!")

        # 요약 출력
        meta = result.get("profile_meta", {})
        print(f"\n📋 프로필 요약:")
        print(f"   이름: {meta.get('candidate_name', 'N/A')}")
        print(f"   역할: {meta.get('primary_role', 'N/A')}")
        print(f"   연차: {meta.get('years_experience', 'N/A')}")

        # 점수 출력
        axes = result.get("scoring_axes", {})
        print(f"\n📊 컬쳐핏 점수:")
        for key in ['technical_fit_user', 'execution_style_user', 'collaboration_style_user',
                    'ownership_user', 'growth_orientation_user', 'work_expectation_user']:
            score_data = axes.get(key, {})
            score = score_data.get('score', 'N/A')
            print(f"   - {key}: {score}/4")

        # 파일 저장 (옵션)
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"\n💾 결과 저장됨: {output_path}")

        return result

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        chain.close()


def main():
    parser = argparse.ArgumentParser(description="S3 PDF 로더 테스트")

    # 모드 선택
    parser.add_argument("--check-config", action="store_true", help="설정 확인")
    parser.add_argument("--load-pdf", action="store_true", help="S3 PDF 로드 테스트")
    parser.add_argument("--analyze", action="store_true", help="구직자 분석 E2E 테스트")

    # 파라미터
    parser.add_argument("--s3-key", help="S3 객체 키 (예: token/resume.pdf)")
    parser.add_argument("--output", "-o", help="결과 저장 파일 경로")

    args = parser.parse_args()

    # 기본 동작: 설정 확인
    if not any([args.check_config, args.load_pdf, args.analyze]):
        args.check_config = True

    if args.check_config:
        check_config()

    if args.load_pdf:
        if not args.s3_key:
            print("❌ --load-pdf에는 --s3-key가 필요합니다")
            sys.exit(1)
        test_load_pdf(args.s3_key)

    if args.analyze:
        if not args.s3_key:
            print("❌ --analyze에는 --s3-key가 필요합니다")
            sys.exit(1)
        asyncio.run(test_analyze(args.s3_key, args.output))


if __name__ == "__main__":
    main()
