# 프로젝트: AI 기반 컬쳐핏 매칭 서비스

## 한 줄 요약
개발자 취준생과 회사 간 컬쳐핏을 AI로 분석/매칭하는 서비스

## 현재 작업 범위
**LangChain 파이프라인 구축에만 한정** (FastAPI, 프론트엔드 제외)

## 기술 스택
- LLM: Google Gemini
- Framework: LangChain
- DB: MongoDB
- Backend: FastAPI (추후)

## 핵심 파이프라인 3개
1. **회사 분석**: URL 입력 → Gemini 스크래핑 → 컬쳐핏 분석 → MongoDB 저장
2. **구직자 분석**: 이력서 텍스트 → 프로필 분석 → JSON 출력
3. **컬쳐핏 비교**: 회사 JSON + 구직자 JSON → 매칭 점수

## 주요 파일
| 파일 | 설명 |
|------|------|
| `기획서.md` | 전체 서비스 기획 |
| `랭체인 기획안.md` | 파이프라인 요구사항 |
| `PLAN_랭체인_파이프라인.md` | 구현 계획 (상세) |
| `developer_profile_fixed_schema_key01.json` | 구직자 분석 JSON 스키마 |
| `user_profile_choi_sungmin01.json` | 스키마 적용 예시 데이터 |

## 핵심 설계 원칙
- **프롬프트는 AI 팀원이 별도 작성** → 플레이스홀더로 구현
- **JSON 스키마 동적 로딩** → 프롬프트 변경에 유연하게 대응
- **웹 스크래퍼 Strategy 패턴** → Gemini(현재) / Playwright(추후) 확장 가능

## 프로젝트 구조
```
langchain_pipeline/
├── config.py          # 환경설정
├── schemas/           # JSON 스키마 (동적 로딩)
├── prompts/           # 프롬프트 템플릿
├── chains/            # LangChain 체인
├── scrapers/          # 웹 스크래퍼 (확장 가능)
├── utils/             # 유틸리티
└── main.py            # 진입점
```

## 환경변수
```
GOOGLE_API_KEY=
MONGODB_URI=
MONGODB_DB_NAME=
```
