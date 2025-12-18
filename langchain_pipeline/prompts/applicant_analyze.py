"""
구직자 분석 프롬프트

[AI 팀원 작성 영역]
- 이력서/포트폴리오를 분석하여 구직자 프로필 생성
- 입력: 이력서/포트폴리오 텍스트
- 출력: 구직자 컬쳐핏 분석 JSON (developer_profile 스키마)
"""

# =====================================================
# AI 팀원 작성 영역 - 아래 내용을 수정해주세요
# =====================================================

SYSTEM_MESSAGE = """당신은 개발자 이력서와 포트폴리오를 분석하는 전문가입니다.
제공된 문서에서 구직자의 기술 역량, 협업 스타일, 성장 성향을 분석합니다.

[AI 팀원 TODO: 시스템 메시지 상세 작성]
- 분석해야 할 항목 (기술 역량, 프로젝트 경험, 협업 경험 등)
- 점수 산정 기준 (0-4 스케일)
- evidence 추출 방법
- unknown 처리 정책
"""

HUMAN_MESSAGE_TEMPLATE = """다음 이력서/포트폴리오를 분석해주세요.

## 구직자 문서
{resume_text}

## 출력 형식 (JSON)
{output_schema}

[AI 팀원 TODO: 분석 지시사항 작성]
- 각 scoring_axes 항목별 분석 기준
- subsignals 점수 산정 방법
- 문서에 없는 정보 처리 (unknown, needs_followup_questions)
"""

# 스키마 파일 참조 (동적 로딩)
SCHEMA_FILE = "applicant_schema.json"

# =====================================================
# 설정 (수정 가능)
# =====================================================

# 입력 변수 목록
INPUT_VARIABLES = ["resume_text", "output_schema"]

# 프롬프트 메타데이터
PROMPT_METADATA = {
    "name": "applicant_analyze",
    "version": "1.0.0",
    "description": "이력서/포트폴리오 기반 구직자 프로필 분석",
    "author": "[AI 팀원 이름]",
    "last_updated": "[날짜]",
}
