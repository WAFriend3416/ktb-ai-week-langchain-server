"""
설정 관리 모듈

환경변수 로딩 및 전역 설정 관리
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 경로
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Google Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# MongoDB 설정
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "culturefit")

# AWS S3 설정
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
S3_REGION = os.getenv("S3_REGION", "ap-northeast-2")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# 스키마 경로
SCHEMAS_DIR = BASE_DIR / "schemas"

# 컬렉션 이름
COLLECTIONS = {
    "companies": "company_profiles",
    "applicants": "applicant_profiles",
    "comparisons": "culture_comparisons",
}


def validate_config(require_s3: bool = False) -> dict:
    """
    설정 유효성 검사

    Args:
        require_s3: S3 설정 필수 여부 (구직자 분석 시 True)
    """
    errors = []
    warnings = []

    if not GOOGLE_API_KEY:
        errors.append("GOOGLE_API_KEY가 설정되지 않았습니다.")

    # S3 설정 검사
    if require_s3:
        if not S3_BUCKET_NAME:
            errors.append("S3_BUCKET_NAME이 설정되지 않았습니다.")
    else:
        if not S3_BUCKET_NAME:
            warnings.append("S3_BUCKET_NAME이 설정되지 않았습니다. (구직자 분석 시 필요)")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "config": {
            "google_api_key": "***" if GOOGLE_API_KEY else "NOT SET",
            "mongodb_uri": MONGODB_URI,
            "mongodb_db_name": MONGODB_DB_NAME,
            "s3_bucket_name": S3_BUCKET_NAME or "NOT SET",
            "s3_region": S3_REGION,
            "schemas_dir": str(SCHEMAS_DIR),
        }
    }
