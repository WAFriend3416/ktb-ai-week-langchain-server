"""
컬쳐핏 비교 프롬프트

[AI 팀원 작성 영역]
- 회사와 구직자의 컬쳐핏을 비교하여 매칭 점수 산출
- 입력: 회사 컬쳐핏 JSON + 구직자 컬쳐핏 JSON
- 출력: 매칭 결과 및 점수 JSON
"""

# =====================================================
# AI 팀원 작성 영역 - 아래 내용을 수정해주세요
# =====================================================

SYSTEM_MESSAGE = """당신은 회사와 구직자 간의 컬쳐핏을 비교 분석하는 전문가입니다.
양측의 프로필을 비교하여 적합도를 평가하고 매칭 점수를 산출합니다.

[AI 팀원 TODO: 시스템 메시지 상세 작성]
- 비교 분석 기준
- 매칭 점수 산정 방법
- 강점/약점 도출 방법
- 추천/비추천 판단 기준
"""

HUMAN_MESSAGE_TEMPLATE = """회사와 구직자의 컬쳐핏을 비교 분석해주세요.

## 회사 컬쳐핏 프로필
{company_culture}

## 구직자 컬쳐핏 프로필
{applicant_profile}

## 분석 요청사항
[AI 팀원 TODO: 비교 분석 지시사항 작성]
- 어떤 항목들을 비교할지
- 매칭 점수 산정 공식/기준
- 결과 출력 형식

## 출력 형식 (JSON)
{{
  "overall_match_score": "0-100 점수",
  "match_level": "excellent|good|moderate|low|poor",
  "category_scores": {{
    "technical_fit": {{ "score": 0, "analysis": "" }},
    "execution_style": {{ "score": 0, "analysis": "" }},
    "collaboration": {{ "score": 0, "analysis": "" }},
    "growth_orientation": {{ "score": 0, "analysis": "" }},
    "work_expectation": {{ "score": 0, "analysis": "" }}
  }},
  "strengths": ["매칭 강점 리스트"],
  "concerns": ["우려사항 리스트"],
  "recommendation": "종합 추천 의견",
  "interview_focus_areas": ["면접에서 확인할 사항"]
}}
"""

# 스키마 파일 참조 (비교 결과용 별도 스키마 - 필요시 생성)
SCHEMA_FILE = None  # 인라인 스키마 사용

# =====================================================
# 설정 (수정 가능)
# =====================================================

# 입력 변수 목록
INPUT_VARIABLES = ["company_culture", "applicant_profile"]

# 프롬프트 메타데이터
PROMPT_METADATA = {
    "name": "culture_compare",
    "version": "1.0.0",
    "description": "회사-구직자 컬쳐핏 비교 분석",
    "author": "[AI 팀원 이름]",
    "last_updated": "[날짜]",
}
