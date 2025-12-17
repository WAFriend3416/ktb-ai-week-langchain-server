# LangChain 파이프라인 구축 계획

## 📌 범위 명시
> **본 태스크는 LangChain 파이프라인 구축에만 한정됩니다.**
> - FastAPI 엔드포인트, 프론트엔드, 배포 등은 본 태스크 범위 외
> - 프롬프트 내용은 AI 팀원들이 별도 작성 (플레이스홀더로 구현)

---

## 🎯 목표
컬쳐핏 분석을 위한 LangChain 파이프라인 구축
- 회사 정보 수집 → 컬쳐핏 분석 → 결과 저장
- 구직자 이력서 분석
- 회사-구직자 컬쳐핏 비교

---

## ⚙️ 기술 스택
| 항목 | 선택 |
|------|------|
| LLM | Google Gemini |
| Framework | LangChain |
| DB | MongoDB |
| 데이터 수집 | **Gemini 모델이 URL 접근** (현재) / Playwright·ChromeDevTools 에이전트 (추후 확장) |
| 출력 형식 | JSON |

---

## 📊 기존 JSON 스키마 (구직자 분석용)

> **참고 파일:**
> - `developer_profile_fixed_schema_key01.json` - 스키마 정의
> - `user_profile_choi_sungmin01.json` - 실제 데이터 예시

### 구직자 프로필 구조 (요약)
```json
{
  "schema_version": "1.0",
  "profile_meta": { "candidate_name", "primary_role", "seniority", "years_experience", "..." },
  "user_info_fields": {
    "basic_profile": { "summary", "evidence[]" },
    "technical_capability": { "stack", "ops_deploy_experience", "..." },
    "project_behavior_data": { "projects[]" },
    "collaboration_experience": { "..." },
    "growth_tendency": { "..." },
    "work_environment_signals": { "..." },
    "verification_needed_areas": { "..." }
  },
  "scoring_axes": {
    "scoring_policy": { "scale": "0-4", "meaning", "unknown_handling" },
    "technical_fit_user": { "score", "summary", "confidence", "evidence[]", "subsignals" },
    "execution_style_user": { "..." },
    "collaboration_style_user": { "..." },
    "ownership_user": { "..." },
    "growth_orientation_user": { "..." },
    "work_expectation_user": { "..." }
  },
  "extraction_quality": { "unknown_policy_applied", "notes" }
}
```

> ⚠️ **데이터 모델 유연성**: 프롬프트에 따라 스키마가 자주 변경될 예정
> → 고정 Pydantic 모델 대신 **동적 JSON 스키마 로딩** 방식 채택

---

## 📁 프로젝트 구조

```
ktb-ai-week/
├── langchain_pipeline/
│   ├── __init__.py
│   ├── config.py                 # 설정 (API 키, MongoDB 연결)
│   ├── schemas/                  # JSON 스키마 (동적 로딩)
│   │   ├── applicant_schema.json     # 구직자 분석 스키마 (기존 파일 활용)
│   │   └── company_schema.json       # 회사 분석 스키마 (AI 팀원 작성 예정)
│   ├── prompts/                  # 프롬프트 템플릿 (AI 팀원 작성용)
│   │   ├── __init__.py
│   │   ├── company_data_collect.py    # 회사 데이터 수집 프롬프트
│   │   ├── company_culture_analyze.py # 회사 컬쳐핏 분석 프롬프트
│   │   ├── applicant_analyze.py       # 구직자 분석 프롬프트
│   │   └── culture_compare.py         # 컬쳐핏 비교 프롬프트
│   ├── chains/                   # LangChain 체인
│   │   ├── __init__.py
│   │   ├── company_chain.py      # 회사 분석 체인
│   │   ├── applicant_chain.py    # 구직자 분석 체인
│   │   └── compare_chain.py      # 비교 체인
│   ├── scrapers/                 # 웹 데이터 수집 (확장 가능 구조)
│   │   ├── __init__.py
│   │   ├── base_scraper.py       # 추상 베이스 클래스
│   │   ├── gemini_scraper.py     # Gemini 모델 기반 (현재)
│   │   └── browser_scraper.py    # Playwright/ChromeDevTools (추후)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── schema_loader.py      # JSON 스키마 동적 로딩
│   │   └── db_handler.py         # MongoDB 핸들러
│   └── main.py                   # 파이프라인 실행 진입점
├── tests/
│   └── test_chains.py
├── requirements.txt
└── .env.example
```

---

## 🔗 파이프라인 흐름

### 1. 회사 컬쳐핏 분석 파이프라인
```
[입력: 채용공고 URL, 회사 페이지 URL]
         ↓
    (GeminiScraper) ← Gemini 모델이 URL 직접 접근
         ↓                추후: Playwright/ChromeDevTools 에이전트로 확장
[텍스트 추출]
         ↓
    (company_data_collect 프롬프트) ← AI 팀원 작성
         ↓
[JSON: 수집된 회사 데이터] ← company_schema.json 기반
         ↓
    (company_culture_analyze 프롬프트) ← AI 팀원 작성
         ↓
[JSON: 회사 컬쳐핏 분석 결과]
         ↓
    (MongoDB 저장)
```

### 2. 구직자 분석 파이프라인
```
[입력: 이력서/포트폴리오 텍스트]
         ↓
    (applicant_analyze 프롬프트) ← AI 팀원 작성
         ↓
[JSON: 구직자 컬쳐핏 분석 결과] ← developer_profile_fixed_schema_key01.json 스키마 사용
```

### 3. 컬쳐핏 비교 파이프라인
```
[입력: 회사 컬쳐핏 JSON + 구직자 컬쳐핏 JSON]
         ↓
    (culture_compare 프롬프트) ← AI 팀원 작성
         ↓
[JSON: 매칭 결과 및 점수]
```

---

## 📋 구현 단계

### Phase 1: 기반 구조 설정
- [ ] 프로젝트 폴더 구조 생성
- [ ] requirements.txt 작성
- [ ] config.py - 환경변수 및 설정 관리
- [ ] .env.example 생성

### Phase 2: 스키마 및 유틸리티 구현
- [ ] schemas/ 폴더 구성
  - 기존 `developer_profile_fixed_schema_key01.json` → `applicant_schema.json`으로 복사
  - `company_schema.json` 플레이스홀더 생성 (AI 팀원 작성 예정)
- [ ] schema_loader.py - JSON 스키마 동적 로딩 유틸
- [ ] db_handler.py - MongoDB CRUD 작업

### Phase 3: 웹 스크래퍼 구현 (확장 가능 구조)
- [ ] base_scraper.py - 추상 베이스 클래스 (Strategy 패턴)
- [ ] gemini_scraper.py - Gemini 모델 기반 웹 접근 (현재 구현)
- [ ] browser_scraper.py - Playwright/ChromeDevTools 인터페이스 (추후 구현용 스텁)

### Phase 4: 프롬프트 템플릿 구조
- [ ] 각 프롬프트 파일에 플레이스홀더 구조 생성
- [ ] AI 팀원들이 채울 수 있도록 명확한 인터페이스 정의
- [ ] JSON 스키마 연동 방식 정의

### Phase 5: LangChain 체인 구현
- [ ] company_chain.py - 회사 분석 체인 (수집 → 분석 → 저장)
- [ ] applicant_chain.py - 구직자 분석 체인
- [ ] compare_chain.py - 비교 체인

### Phase 6: 통합 및 테스트
- [ ] main.py - 전체 파이프라인 통합
- [ ] 기본 테스트 작성

---

## 🔧 프롬프트 템플릿 인터페이스 (AI 팀원용)

각 프롬프트 파일은 다음 구조를 따름:

```python
# prompts/applicant_analyze.py 예시

SYSTEM_MESSAGE = """
[AI 팀원이 작성할 시스템 메시지]
당신은 구직자의 이력서/포트폴리오를 분석하는 전문가입니다.
...
"""

HUMAN_MESSAGE_TEMPLATE = """
[AI 팀원이 작성할 사용자 메시지 템플릿]
입력 변수: {resume_text}
출력 형식: {output_schema}  ← JSON 스키마 동적 주입
"""

# 스키마 파일 참조
SCHEMA_FILE = "applicant_schema.json"
```

> **Note**: JSON 스키마는 `schemas/` 폴더에서 동적 로딩
> - 프롬프트에서 스키마를 직접 정의하지 않고 외부 파일 참조
> - 스키마 변경 시 프롬프트 코드 수정 불필요

---

## 🏗️ 웹 스크래퍼 확장 구조 (Strategy 패턴)

```python
# scrapers/base_scraper.py
from abc import ABC, abstractmethod

class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self, url: str) -> str:
        """URL에서 텍스트 추출"""
        pass

# scrapers/gemini_scraper.py (현재 구현)
class GeminiScraper(BaseScraper):
    """Gemini 모델이 URL에 직접 접근하여 데이터 추출"""
    async def scrape(self, url: str) -> str:
        # Gemini API로 URL 내용 추출
        ...

# scrapers/browser_scraper.py (추후 구현)
class BrowserScraper(BaseScraper):
    """Playwright/ChromeDevTools로 브라우저 제어"""
    async def scrape(self, url: str) -> str:
        # 추후 구현
        raise NotImplementedError("추후 Playwright/ChromeDevTools 연동 예정")
```

---

## 📦 주요 의존성

```
# LangChain
langchain>=0.1.0
langchain-google-genai>=1.0.0

# Database
pymongo>=4.0.0

# Utilities
python-dotenv>=1.0.0

# 추후 확장용 (현재 미설치)
# playwright>=1.40.0
# selenium>=4.15.0
```

---

## ⚠️ 참고사항

### 현재 구현 범위
- ✅ LangChain 파이프라인 구조
- ✅ Gemini 기반 웹 스크래핑
- ✅ JSON 스키마 동적 로딩
- ✅ MongoDB 저장

### 추후 확장 예정
- ⏳ Playwright/ChromeDevTools 에이전트 방식 웹 스크래핑
- ⏳ 회사 스키마 정의 (AI 팀원 작성)

### 환경변수 (.env)
```
GOOGLE_API_KEY=your_gemini_api_key
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=culturefit
```
