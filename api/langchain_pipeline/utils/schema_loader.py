"""
JSON 스키마 동적 로딩 유틸리티

프롬프트 변경에 유연하게 대응하기 위해
JSON 스키마를 외부 파일에서 동적으로 로딩
"""

import json
from pathlib import Path
from typing import Any

from langchain_pipeline.config import SCHEMAS_DIR


def load_schema(schema_name: str) -> dict[str, Any]:
    """
    스키마 파일 로딩

    Args:
        schema_name: 스키마 파일명 (확장자 포함/미포함 모두 가능)
                    예: "applicant_schema" 또는 "applicant_schema.json"

    Returns:
        스키마 딕셔너리

    Raises:
        FileNotFoundError: 스키마 파일이 없을 경우
        json.JSONDecodeError: JSON 파싱 실패 시
    """
    # 확장자 없으면 추가
    if not schema_name.endswith(".json"):
        schema_name = f"{schema_name}.json"

    schema_path = SCHEMAS_DIR / schema_name

    if not schema_path.exists():
        raise FileNotFoundError(f"스키마 파일을 찾을 수 없습니다: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def schema_to_string(schema: dict[str, Any], indent: int = 2) -> str:
    """
    스키마를 문자열로 변환 (프롬프트 주입용)

    Args:
        schema: 스키마 딕셔너리
        indent: 들여쓰기 크기

    Returns:
        JSON 문자열
    """
    return json.dumps(schema, ensure_ascii=False, indent=indent)


def get_schema_for_prompt(schema_name: str, escape_braces: bool = True) -> str:
    """
    프롬프트에 주입할 스키마 문자열 반환

    Args:
        schema_name: 스키마 파일명
        escape_braces: LangChain 템플릿용 중괄호 이스케이프 여부

    Returns:
        프롬프트용 스키마 문자열
    """
    schema = load_schema(schema_name)
    schema_str = schema_to_string(schema)

    # LangChain ChatPromptTemplate에서 {} 를 변수로 해석하지 않도록 이스케이프
    if escape_braces:
        schema_str = schema_str.replace("{", "{{").replace("}", "}}")

    return schema_str


def list_available_schemas() -> list[str]:
    """
    사용 가능한 스키마 목록 반환

    Returns:
        스키마 파일명 리스트
    """
    if not SCHEMAS_DIR.exists():
        return []

    return [f.name for f in SCHEMAS_DIR.glob("*.json")]
