"""
구직자 분석 체인

파이프라인 흐름:
1. 텍스트 기반: 이력서 텍스트 → 프로필 분석 → JSON 출력
2. S3 PDF 기반: S3 PDF → Gemini Files API → 프로필 분석 → JSON 출력
3. 로컬 PDF 기반: 로컬 PDF들 → Gemini Files API → 통합 분석 → JSON 출력

S3/로컬 PDF 연동 시 google-genai SDK를 직접 사용합니다 (PDF multimodal 지원)
"""

import json
from typing import Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from langchain_pipeline.config import (
    GOOGLE_API_KEY,
    S3_BUCKET_NAME,
    S3_REGION,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
)
from langchain_pipeline.utils.schema_loader import get_schema_for_prompt
from langchain_pipeline.utils.db_handler import DatabaseHandler
from langchain_pipeline.prompts import applicant_analyze


class ApplicantAnalysisChain:
    """
    구직자 분석 체인

    두 가지 분석 모드 지원:
    1. run(): 텍스트 기반 분석 (기존 방식)
    2. run_from_s3(): S3 PDF 기반 분석 (Gemini multimodal)
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.0,
        save_to_db: bool = True
    ):
        """
        Args:
            model_name: Gemini 모델명
            temperature: 생성 온도
            save_to_db: DB 저장 여부
        """
        self.model_name = model_name
        self.temperature = temperature

        # LangChain LLM (텍스트 기반 분석용)
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=GOOGLE_API_KEY,
            temperature=temperature,
        )

        self.save_to_db = save_to_db
        self.db = DatabaseHandler() if save_to_db else None

        # PDF 로더 (지연 초기화)
        self._s3_loader = None
        self._local_loader = None
        self._uploaded_file = None
        self._uploaded_files: list = []  # 여러 파일 추적용

        # 프롬프트 템플릿 설정
        self._setup_prompts()

    def _setup_prompts(self):
        """프롬프트 템플릿 초기화"""
        self.analyze_prompt = ChatPromptTemplate.from_messages([
            ("system", applicant_analyze.SYSTEM_MESSAGE),
            ("human", applicant_analyze.HUMAN_MESSAGE_TEMPLATE),
        ])

        self.json_parser = JsonOutputParser()

    def _get_s3_loader(self):
        """S3 PDF 로더 지연 초기화"""
        if self._s3_loader is None:
            from langchain_pipeline.loaders.s3_pdf_loader import S3PDFLoader

            self._s3_loader = S3PDFLoader(
                bucket_name=S3_BUCKET_NAME,
                gemini_api_key=GOOGLE_API_KEY,
                aws_region=S3_REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID or None,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY or None,
            )

        return self._s3_loader

    def _get_local_loader(self):
        """로컬 PDF 로더 지연 초기화"""
        if self._local_loader is None:
            from langchain_pipeline.loaders.local_pdf_loader import LocalPDFLoader

            self._local_loader = LocalPDFLoader(
                gemini_api_key=GOOGLE_API_KEY
            )

        return self._local_loader

    async def analyze(self, resume_text: str) -> dict[str, Any]:
        """
        이력서/포트폴리오 텍스트 분석 (LangChain 사용)

        Args:
            resume_text: 이력서 또는 포트폴리오 텍스트

        Returns:
            구직자 프로필 분석 결과 (JSON)
        """
        schema = get_schema_for_prompt("applicant_schema")

        chain = self.analyze_prompt | self.llm | self.json_parser

        result = await chain.ainvoke({
            "resume_text": resume_text,
            "output_schema": schema,
        })

        return result

    async def analyze_pdf(self, s3_key: str) -> dict[str, Any]:
        """
        S3의 PDF 파일 분석 (Gemini Files API 직접 사용)

        Args:
            s3_key: S3 객체 키 (예: "{token}/resume.pdf")

        Returns:
            구직자 프로필 분석 결과 (JSON)
        """
        from google import genai
        from google.genai import types

        loader = self._get_s3_loader()

        try:
            # 1. S3 → Gemini 업로드
            self._uploaded_file = loader.load_from_s3(s3_key)

            if self._uploaded_file.state != 'ACTIVE':
                raise Exception(f"파일 처리 실패: {self._uploaded_file.state}")

            # 2. 스키마 로드 (Gemini 직접 사용이므로 이스케이프 불필요)
            schema = get_schema_for_prompt("applicant_schema", escape_braces=False)

            # 3. 프롬프트 구성
            prompt = f"""{applicant_analyze.SYSTEM_MESSAGE}

다음 PDF 문서(이력서/포트폴리오)를 분석해주세요.

## 출력 JSON 스키마
{schema}

{applicant_analyze.HUMAN_MESSAGE_TEMPLATE.replace("{resume_text}", "[첨부된 PDF 문서 참조]").replace("{output_schema}", "")}

반드시 유효한 JSON 형식으로만 응답하세요."""

            # 4. Gemini에 PDF + 프롬프트 전송
            client = genai.Client(api_key=GOOGLE_API_KEY)

            # URI 문자열이 아닌 types.Part.from_uri()로 변환해야 Gemini가 PDF를 인식함
            pdf_part = types.Part.from_uri(
                file_uri=self._uploaded_file.uri,
                mime_type="application/pdf"
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=[pdf_part, prompt]
            )

            # 5. JSON 파싱
            response_text = response.text

            # JSON 블록 추출 (```json ... ``` 형식 처리)
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            result = json.loads(response_text)

            return result

        finally:
            # 6. 정리: Gemini에서 파일 삭제
            if self._uploaded_file:
                loader.delete_file(self._uploaded_file)
                self._uploaded_file = None

    async def analyze_local_pdfs(self, file_paths: list[str]) -> dict[str, Any]:
        """
        로컬 PDF 파일들 통합 분석 (Gemini Files API 직접 사용)

        여러 PDF(이력서, 포트폴리오, 자기소개서)를 하나의 Gemini 요청으로 통합 분석

        Args:
            file_paths: 로컬 PDF 파일 경로 리스트

        Returns:
            구직자 프로필 분석 결과 (JSON)
        """
        from google import genai
        from google.genai import types
        from pathlib import Path

        loader = self._get_local_loader()

        try:
            # 1. 모든 PDF를 Gemini에 업로드
            self._uploaded_files = loader.load_files(file_paths)

            # 업로드 상태 확인
            for uploaded_file in self._uploaded_files:
                if uploaded_file.state != 'ACTIVE':
                    raise Exception(f"파일 처리 실패: {uploaded_file.display_name} - {uploaded_file.state}")

            # 2. 스키마 로드 (Gemini 직접 사용이므로 이스케이프 불필요)
            schema = get_schema_for_prompt("applicant_schema", escape_braces=False)

            # 3. 파일 목록 설명 생성
            file_descriptions = []
            for i, uploaded_file in enumerate(self._uploaded_files, 1):
                filename = uploaded_file.display_name
                # 파일명에서 문서 유형 추측
                if "이력서" in filename or "resume" in filename.lower():
                    doc_type = "이력서 (Resume)"
                elif "포트폴리오" in filename or "portfolio" in filename.lower():
                    doc_type = "포트폴리오 (Portfolio)"
                elif "자기소개서" in filename or "essay" in filename.lower() or "자소서" in filename:
                    doc_type = "자기소개서 (Personal Statement)"
                else:
                    doc_type = "기타 문서"
                file_descriptions.append(f"{i}. {filename} - {doc_type}")

            files_summary = "\n".join(file_descriptions)

            # 4. 프롬프트 구성
            prompt = f"""{applicant_analyze.SYSTEM_MESSAGE}

Analyze the following attached PDF documents for this candidate:

{files_summary}

## Output JSON Schema
{schema}

Instructions:
- Integrate information from ALL provided documents (resume, portfolio, essay)
- Use doc_id in evidence to specify which document the quote is from
- Score each axis based on combined evidence from all documents
- If information is not explicitly stated in any document, mark as "unknown"

Output MUST be valid JSON only. No markdown, no explanations."""

            # 5. Gemini에 모든 PDF + 프롬프트 전송
            client = genai.Client(api_key=GOOGLE_API_KEY)

            # contents 배열 구성: [파일1 Part, 파일2 Part, ..., 프롬프트]
            # URI 문자열이 아닌 types.Part.from_uri()로 변환해야 Gemini가 PDF를 인식함
            contents = [
                types.Part.from_uri(file_uri=uploaded_file.uri, mime_type="application/pdf")
                for uploaded_file in self._uploaded_files
            ]
            contents.append(prompt)

            response = client.models.generate_content(
                model=self.model_name,
                contents=contents
            )

            # 6. JSON 파싱
            response_text = response.text

            # JSON 블록 추출
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            result = json.loads(response_text)

            return result

        finally:
            # 7. 정리: Gemini에서 모든 파일 삭제
            if self._uploaded_files:
                loader.delete_files(self._uploaded_files)
                self._uploaded_files = []

    async def run_from_local_pdfs(
        self,
        file_paths: list[str],
        candidate_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        로컬 PDF 기반 파이프라인 실행

        여러 PDF(이력서, 포트폴리오, 자기소개서)를 통합 분석

        Args:
            file_paths: 로컬 PDF 파일 경로 리스트
            candidate_name: 구직자명 (옵션)

        Returns:
            최종 분석 결과
        """
        from pathlib import Path

        # 1. PDF 통합 분석
        profile = await self.analyze_local_pdfs(file_paths)

        # 2. 소스 정보 추가
        profile["_source"] = {
            "type": "local_pdfs",
            "files": [Path(p).name for p in file_paths],
        }

        # 3. DB 저장 (옵션)
        if self.save_to_db and self.db:
            doc_id = self.db.save_applicant_profile(profile)
            profile["_id"] = doc_id

        return profile

    async def run(
        self,
        resume_text: str,
        candidate_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        텍스트 기반 파이프라인 실행

        Args:
            resume_text: 이력서/포트폴리오 텍스트
            candidate_name: 구직자명 (옵션, 없으면 분석 결과에서 추출)

        Returns:
            최종 분석 결과
        """
        # 1. 프로필 분석
        profile = await self.analyze(resume_text)

        # 2. DB 저장 (옵션)
        if self.save_to_db and self.db:
            doc_id = self.db.save_applicant_profile(profile)
            profile["_id"] = doc_id

        return profile

    async def run_from_s3(
        self,
        s3_key: str,
        candidate_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        S3 PDF 기반 파이프라인 실행

        Args:
            s3_key: S3 객체 키 (예: "{token}/resume.pdf")
            candidate_name: 구직자명 (옵션)

        Returns:
            최종 분석 결과
        """
        # 1. PDF 분석
        profile = await self.analyze_pdf(s3_key)

        # 2. 소스 정보 추가
        profile["_source"] = {
            "type": "s3_pdf",
            "s3_key": s3_key,
        }

        # 3. DB 저장 (옵션)
        if self.save_to_db and self.db:
            doc_id = self.db.save_applicant_profile(profile)
            profile["_id"] = doc_id

        return profile

    async def run_from_file(self, file_path: str) -> dict[str, Any]:
        """
        로컬 파일에서 이력서 로드 후 분석

        Args:
            file_path: 이력서 파일 경로 (txt, md 등)

        Returns:
            분석 결과
        """
        with open(file_path, "r", encoding="utf-8") as f:
            resume_text = f.read()

        return await self.run(resume_text)

    def close(self):
        """리소스 정리"""
        if self.db:
            self.db.close()
