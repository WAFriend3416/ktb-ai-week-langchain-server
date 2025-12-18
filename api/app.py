"""
FastAPI Application Entry Point

컬쳐핏 분석 API 서버 메인 애플리케이션
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import culture_fit_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 로직"""
    # Startup
    print("🚀 Culture-Fit Analysis API Server Starting...")
    yield
    # Shutdown
    print("👋 Culture-Fit Analysis API Server Shutting Down...")


app = FastAPI(
    title="Culture-Fit Analysis API",
    description="""
## AI 기반 컬쳐핏 매칭 서비스 API

개발자 취준생과 회사 간 컬쳐핏을 AI로 분석/매칭하는 서비스

### 주요 기능
- **회사 분석**: 채용 페이지 URL → 컬쳐핏 분석
- **구직자 분석**: 이력서/포트폴리오 PDF → 프로필 분석
- **컬쳐핏 매칭**: 회사 + 구직자 → 매칭 점수

### 처리 방식
- 회사 분석 + 구직자 분석: **병렬 실행** (asyncio.gather)
- 비교 분석: 순차 실행 (둘 다 완료 후)
    """,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 설정 (프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(culture_fit_router)


@app.get("/", tags=["root"])
async def root():
    """API 루트 엔드포인트"""
    return {
        "service": "Culture-Fit Analysis API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/culture-fit/health",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", tags=["root"])
async def health():
    """루트 헬스체크"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# 직접 실행 시 (개발용)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
