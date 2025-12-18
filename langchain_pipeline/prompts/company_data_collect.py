"""
회사 데이터 수집 프롬프트

역할: 스크래핑된 웹 페이지 텍스트에서 회사 정보를 구조화된 JSON으로 추출
입력: 채용공고/회사 페이지 스크래핑 텍스트
출력: 회사 기본 정보 + 채용 정보 + 기술 스택 + 문화 시그널 JSON
"""

SYSTEM_MESSAGE = """당신은 채용공고와 회사 정보를 분석하는 전문가입니다.
주어진 웹 페이지 내용에서 회사와 채용 관련 핵심 정보를 정확하게 추출합니다.

## 추출 원칙
1. **사실 기반**: 텍스트에 명시된 정보만 추출합니다
2. **추론 금지**: 언급되지 않은 정보는 "unknown" 또는 빈 배열로 표시합니다
3. **원문 보존**: 기술 스택, 키워드 등은 원문 그대로 추출합니다
4. **구조화**: JSON 스키마 형식에 맞게 정리합니다

## 주요 추출 항목
- 회사 정보: 회사명, 산업, 규모, 위치
- 채용 정보: 포지션명, 팀명, 주요 업무, 자격 요건, 우대 사항
- 기술 스택: 언어, 프레임워크, 도구
- 문화 시그널: 팀 구조, 업무 방식, 협업 키워드, 성장 지원, 복지
"""

HUMAN_MESSAGE_TEMPLATE = """다음 웹 페이지 내용에서 회사 정보를 추출해주세요.

## 웹 페이지 내용
{scraped_content}

## 출력 JSON 스키마
{output_schema}

## 추출 지침
1. company_info: 회사 기본 정보를 추출합니다. 명시되지 않은 정보는 "unknown"으로 표시합니다.
2. job_info: 채용 포지션 관련 정보를 추출합니다. 배열 항목이 없으면 빈 배열 []로 표시합니다.
3. tech_stack: 언급된 기술 스택을 카테고리별로 분류합니다.
4. culture_signals: 조직 문화를 파악할 수 있는 시그널을 추출합니다.
   - team_structure: 팀 구조 설명 (사일로, 매트릭스, 스쿼드 등)
   - work_style: 업무 방식 설명
   - collaboration_keywords: 협업 관련 키워드 (코드리뷰, 페어 프로그래밍 등)
   - growth_support: 성장 지원 관련 언급 (교육, 컨퍼런스, 스터디 등)
   - benefits_mentioned: 복지/혜택 언급

주의: culture_fit_scores는 이 단계에서 작성하지 않습니다. 빈 객체로 두세요.
주의: overall_summary도 이 단계에서 작성하지 않습니다. 빈 문자열로 두세요.

반드시 유효한 JSON 형식으로만 응답하세요."""

# 스키마 파일 참조 (동적 로딩)
SCHEMA_FILE = "company_schema.json"

# 입력 변수 목록
INPUT_VARIABLES = ["scraped_content", "output_schema"]

# 프롬프트 메타데이터
PROMPT_METADATA = {
    "name": "company_data_collect",
    "version": "1.0.0-test",
    "description": "채용공고/회사 페이지에서 데이터 수집 (테스트용)",
    "author": "test",
    "last_updated": "2024-12-18",
}
