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

# 스키마 경로
SCHEMAS_DIR = BASE_DIR / "schemas"

# 컬렉션 이름
COLLECTIONS = {
    "companies": "company_profiles",
    "applicants": "applicant_profiles",
    "comparisons": "culture_comparisons",
}


def validate_config() -> dict:
    """설정 유효성 검사"""
    errors = []

    if not GOOGLE_API_KEY:
        errors.append("GOOGLE_API_KEY가 설정되지 않았습니다.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "config": {
            "google_api_key": "***" if GOOGLE_API_KEY else "NOT SET",
            "mongodb_uri": MONGODB_URI,
            "mongodb_db_name": MONGODB_DB_NAME,
            "schemas_dir": str(SCHEMAS_DIR),
        }
    }
