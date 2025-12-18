"""
S3 PDF 로더 + Gemini Files API 연동

역할: S3에서 PDF 다운로드 → Gemini에 업로드 → 분석 가능 상태로 반환

사용법:
    loader = S3PDFLoader(bucket_name="my-bucket", gemini_api_key="...")
    gemini_file = loader.load_from_s3("token123/resume.pdf")
    # gemini_file.uri를 Gemini generate_content에 전달
"""

import io
import time
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from google import genai
from google.genai import types


@dataclass
class GeminiFile:
    """Gemini에 업로드된 파일 정보"""
    name: str           # Gemini 파일 ID (예: "files/abc123")
    uri: str            # Gemini 파일 URI
    display_name: str   # 원본 파일명
    state: str          # PROCESSING | ACTIVE | FAILED
    size_bytes: Optional[int] = None


@dataclass
class S3DownloadResult:
    """S3 다운로드 결과"""
    success: bool
    data: Optional[bytes] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None
    error_message: Optional[str] = None


class S3PDFLoader:
    """
    S3 → Gemini PDF 로더

    S3에 저장된 PDF를 다운로드하여 Gemini Files API로 업로드합니다.
    업로드된 파일은 Gemini의 multimodal 분석에 사용할 수 있습니다.
    """

    def __init__(
        self,
        bucket_name: str,
        gemini_api_key: str,
        aws_region: str = "ap-northeast-2",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """
        Args:
            bucket_name: S3 버킷명
            gemini_api_key: Gemini API 키
            aws_region: AWS 리전 (기본: 서울)
            aws_access_key_id: AWS Access Key (없으면 환경변수/IAM Role 사용)
            aws_secret_access_key: AWS Secret Key (없으면 환경변수/IAM Role 사용)
        """
        self.bucket_name = bucket_name

        # S3 클라이언트 초기화
        s3_kwargs = {"region_name": aws_region}
        if aws_access_key_id and aws_secret_access_key:
            s3_kwargs["aws_access_key_id"] = aws_access_key_id
            s3_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.s3_client = boto3.client('s3', **s3_kwargs)

        # Gemini 클라이언트 초기화
        self.genai_client = genai.Client(api_key=gemini_api_key)

    def _download_from_s3(self, s3_key: str) -> S3DownloadResult:
        """
        S3에서 파일 다운로드

        Args:
            s3_key: S3 객체 키 (예: "{token}/resume.pdf")

        Returns:
            S3DownloadResult: 다운로드 결과
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            pdf_bytes = response['Body'].read()
            content_type = response.get('ContentType', 'application/pdf')
            filename = s3_key.split('/')[-1]

            return S3DownloadResult(
                success=True,
                data=pdf_bytes,
                filename=filename,
                content_type=content_type
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return S3DownloadResult(
                    success=False,
                    error_message=f"S3에서 파일을 찾을 수 없습니다: {s3_key}"
                )
            elif error_code == 'AccessDenied':
                return S3DownloadResult(
                    success=False,
                    error_message=f"S3 접근 권한이 없습니다: {s3_key}"
                )
            else:
                return S3DownloadResult(
                    success=False,
                    error_message=f"S3 오류: {error_code} - {e.response['Error']['Message']}"
                )
        except Exception as e:
            return S3DownloadResult(
                success=False,
                error_message=f"다운로드 실패: {str(e)}"
            )

    def _upload_to_gemini(
        self,
        pdf_bytes: bytes,
        filename: str,
        wait_for_processing: bool = True,
        max_wait_seconds: int = 60
    ) -> GeminiFile:
        """
        Gemini Files API로 PDF 업로드

        Args:
            pdf_bytes: PDF 파일 바이트
            filename: 파일명
            wait_for_processing: 처리 완료까지 대기 여부
            max_wait_seconds: 최대 대기 시간 (초)

        Returns:
            GeminiFile: 업로드된 파일 정보
        """
        # BytesIO로 파일 객체 생성
        file_obj = io.BytesIO(pdf_bytes)
        file_obj.name = filename  # Gemini가 파일명 인식하도록

        # Gemini에 업로드
        uploaded_file = self.genai_client.files.upload(
            file=file_obj,
            config=types.UploadFileConfig(
                display_name=filename,
                mime_type='application/pdf'
            )
        )

        # 처리 완료 대기
        if wait_for_processing:
            elapsed = 0
            while uploaded_file.state == 'PROCESSING' and elapsed < max_wait_seconds:
                time.sleep(2)
                elapsed += 2
                uploaded_file = self.genai_client.files.get(name=uploaded_file.name)

        return GeminiFile(
            name=uploaded_file.name,
            uri=uploaded_file.uri,
            display_name=filename,
            state=uploaded_file.state,
            size_bytes=getattr(uploaded_file, 'size_bytes', None)
        )

    def load_from_s3(
        self,
        s3_key: str,
        wait_for_processing: bool = True,
        max_wait_seconds: int = 60
    ) -> GeminiFile:
        """
        S3에서 PDF 다운로드 → Gemini에 업로드

        Args:
            s3_key: S3 객체 키 (예: "{token}/resume.pdf")
            wait_for_processing: Gemini 처리 완료까지 대기 여부
            max_wait_seconds: 최대 대기 시간 (초)

        Returns:
            GeminiFile: Gemini에 업로드된 파일 정보

        Raises:
            Exception: S3 다운로드 또는 Gemini 업로드 실패 시
        """
        # 1. S3에서 다운로드
        download_result = self._download_from_s3(s3_key)

        if not download_result.success:
            raise Exception(download_result.error_message)

        # 2. Gemini에 업로드
        gemini_file = self._upload_to_gemini(
            pdf_bytes=download_result.data,
            filename=download_result.filename,
            wait_for_processing=wait_for_processing,
            max_wait_seconds=max_wait_seconds
        )

        return gemini_file

    def load_from_bytes(
        self,
        pdf_bytes: bytes,
        filename: str,
        wait_for_processing: bool = True
    ) -> GeminiFile:
        """
        바이트 데이터에서 직접 Gemini로 업로드 (FastAPI UploadFile용)

        Args:
            pdf_bytes: PDF 파일 바이트
            filename: 파일명
            wait_for_processing: 처리 완료까지 대기

        Returns:
            GeminiFile: 업로드된 파일 정보
        """
        return self._upload_to_gemini(
            pdf_bytes=pdf_bytes,
            filename=filename,
            wait_for_processing=wait_for_processing
        )

    def delete_file(self, gemini_file: GeminiFile) -> bool:
        """
        Gemini에서 파일 삭제 (정리용)

        Args:
            gemini_file: 삭제할 파일 정보

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            self.genai_client.files.delete(name=gemini_file.name)
            return True
        except Exception:
            return False

