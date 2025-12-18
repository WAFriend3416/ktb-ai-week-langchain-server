# LangChain 파이프라인 개발 현황 가이드

> **작성일**: 2024-12-18
> **버전**: v1.0.0
> **상태**: 파이프라인 구조 완성 (프롬프트 작성 대기)

---

## 📊 개발 진행 현황

| Phase | 상태 | 설명 |
|-------|------|------|
| Phase 1 | ✅ 완료 | 기반 구조 설정 |
| Phase 2 | ✅ 완료 | 스키마 및 유틸리티 구현 |
| Phase 3 | ✅ 완료 | 웹 스크래퍼 구현 |
| Phase 4 | ✅ 완료 | 프롬프트 템플릿 구조 |
| Phase 5 | ✅ 완료 | LangChain 체인 구현 |
| Phase 6 | ✅ 완료 | 통합 및 테스트 |

---

## 🗂️ 프로젝트 구조

```
ktb-ai-week/
│
├── 📄 문서
│   ├── CLAUDE.md                    # Claude Code 컨텍스트
│   ├── PLAN_랭체인_파이프라인.md    # 구현 계획 (상세)
│   ├── GUIDE_개발현황.md            # 👈 현재 문서
│   ├── 기획서.md                    # 서비스 전체 기획
│   └── 랭체인 기획안.md             # 파이프라인 요구사항
│
├── 📊 데이터
│   ├── developer_profile_fixed_schema_key01.json  # 구직자 스키마 정의
│   └── user_profile_choi_sungmin01.json           # 스키마 예시 데이터
│
├── 📦 langchain_pipeline/           # 메인 패키지
│   ├── __init__.py
│   ├── config.py                    # 설정 관리
│   ├── main.py                      # CLI 진입점
│   │
│   ├── schemas/                     # JSON 스키마
│   │   ├── applicant_schema.json    # 구직자 분석 스키마 ✅
│   │   └── company_schema.json      # 회사 분석 스키마 (플레이스홀더)
│   │
│   ├── prompts/                     # 프롬프트 템플릿 ⏳ AI 팀원 작성 필요
│   │   ├── company_data_collect.py  # 회사 데이터 수집
│   │   ├── company_culture_analyze.py # 회사 컬쳐핏 분석
│   │   ├── applicant_analyze.py     # 구직자 분석
│   │   └── culture_compare.py       # 컬쳐핏 비교
│   │
│   ├── chains/                      # LangChain 체인
│   │   ├── company_chain.py         # 회사 분석 체인
│   │   ├── applicant_chain.py       # 구직자 분석 체인
│   │   └── compare_chain.py         # 비교 체인
│   │
│   ├── scrapers/                    # 웹 스크래퍼
│   │   ├── base_scraper.py          # 추상 베이스
│   │   ├── gemini_scraper.py        # Gemini 기반 ✅
│   │   └── browser_scraper.py       # Playwright (추후)
│   │
│   └── utils/                       # 유틸리티
│       ├── schema_loader.py         # 스키마 로딩
│       └── db_handler.py            # MongoDB 핸들러
│
├── tests/                           # 테스트
│   └── test_chains.py
│
├── requirements.txt                 # 의존성
├── .env.example                     # 환경변수 예시
└── .gitignore
```

---

## 🔧 환경 설정 방법

### 1. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정
```bash
cp .env.example .env
# .env 파일 편집하여 API 키 입력
```

**.env 파일 내용:**
```
GOOGLE_API_KEY=your_gemini_api_key_here
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=culturefit
```

### 4. 설정 검증
```bash
python -m langchain_pipeline.main config
```

---

## 🚀 사용 방법

### CLI 명령어

#### 회사 분석
```bash
python -m langchain_pipeline.main company --urls "https://company.com/careers" "https://company.com/about"
```

#### 구직자 분석
```bash
# 파일에서
python -m langchain_pipeline.main applicant --file resume.txt

# 텍스트 직접 입력
python -m langchain_pipeline.main applicant --text "이력서 내용..."
```

#### 컬쳐핏 비교
```bash
python -m langchain_pipeline.main compare --company "회사명" --applicant "구직자명"
```

### Python 코드에서 사용

```python
import asyncio
from langchain_pipeline.chains.company_chain import CompanyAnalysisChain
from langchain_pipeline.chains.applicant_chain import ApplicantAnalysisChain
from langchain_pipeline.chains.compare_chain import CultureCompareChain

async def main():
    # 회사 분석
    company_chain = CompanyAnalysisChain()
    company_result = await company_chain.run(["https://example.com/jobs"])

    # 구직자 분석
    applicant_chain = ApplicantAnalysisChain()
    applicant_result = await applicant_chain.run("이력서 텍스트...")

    # 비교
    compare_chain = CultureCompareChain()
    comparison = await compare_chain.run(
        company_result["culture_analysis"],
        applicant_result
    )

    print(comparison)

asyncio.run(main())
```

---

## 👥 AI 팀원 작업 가이드

### 🎯 작업이 필요한 파일

#### 1. 프롬프트 파일 (4개)
각 파일에서 `[AI 팀원 TODO]` 표시된 부분을 작성해주세요.

| 파일 | 위치 | 역할 |
|------|------|------|
| `company_data_collect.py` | `prompts/` | 채용공고/회사페이지에서 데이터 추출 |
| `company_culture_analyze.py` | `prompts/` | 회사 데이터 → 컬쳐핏 분석 |
| `applicant_analyze.py` | `prompts/` | 이력서 → 구직자 프로필 분석 |
| `culture_compare.py` | `prompts/` | 회사+구직자 → 매칭 점수 |

#### 2. 회사 스키마 (선택)
- `schemas/company_schema.json`
- 현재 플레이스홀더로 되어 있음
- 필요시 구직자 스키마를 참고하여 상세화

### 📝 프롬프트 작성 형식

```python
# prompts/applicant_analyze.py 예시

SYSTEM_MESSAGE = """당신은 개발자 이력서를 분석하는 전문가입니다.

## 분석 기준
- 기술 역량: 사용 기술 스택, 프로젝트 경험의 깊이
- 협업 스타일: 코드 리뷰, 문서화, 팀 협업 경험
- 성장 성향: 새 기술 학습, 피드백 수용 태도
...

## 점수 체계 (0-4)
- 0: 명시적 증거 없음
- 1: 약하거나 간접적인 언급
- 2: 일부 증거 (제한된 범위)
- 3: 명확한 증거 (여러 사례)
- 4: 강력한 증거 (구체적 성과/지표 포함)
"""

HUMAN_MESSAGE_TEMPLATE = """다음 이력서를 분석해주세요.

## 이력서 내용
{resume_text}

## 출력 JSON 스키마
{output_schema}

## 분석 지침
1. 각 scoring_axes 항목별로 점수와 근거(evidence)를 작성
2. 문서에 명시되지 않은 정보는 "unknown"으로 표기
3. 추가 확인이 필요한 항목은 verification_needed_areas에 기재
"""
```

### ⚠️ 주의사항
- `{resume_text}`, `{output_schema}` 등 변수는 그대로 유지
- JSON 출력을 위해 스키마 형식을 명확히 지시
- 증거(evidence) 작성 시 원문 인용 포함하도록 지시

---

## 🧪 테스트 실행

```bash
# 전체 테스트
pytest tests/ -v

# 유닛 테스트만
pytest tests/ -v -m "not integration"

# 통합 테스트 (API 키 필요)
pytest tests/ -v -m integration
```

---

## 📝 Git 커밋 히스토리

```
da63fe4 feat: Phase 6 - 통합 및 테스트
b1215c1 feat: Phase 4 - 프롬프트 템플릿 구조 (AI 팀원용 플레이스홀더)
d1143fd feat: Phase 3 - 웹 스크래퍼 구현 (Strategy 패턴)
98bc4bb feat: Phase 2 - 스키마 및 유틸리티 구현
52195d1 feat: Phase 1 - 기반 구조 설정 완료
a6c225d v1: 프로젝트 초기 설정 및 LangChain 파이프라인 계획 수립
```

---

## 🔜 다음 단계

1. **[AI 팀원]** 프롬프트 내용 작성
2. **[AI 팀원]** 회사 스키마 상세화 (필요시)
3. **[개발팀]** 실제 데이터로 통합 테스트
4. **[개발팀]** FastAPI 엔드포인트 연동 (별도 태스크)

---

## 📞 문의

개발 관련 문의는 프로젝트 담당자에게 연락해주세요.
