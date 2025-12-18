"""
Local PDF Loader + Gemini Files API

Load local PDF files and upload them to Gemini for multimodal analysis.

Usage:
    loader = LocalPDFLoader(gemini_api_key="...")
    gemini_files = loader.load_files([
        "user_profile/profile_P1/resume.pdf",
        "user_profile/profile_P1/portfolio.pdf",
        "user_profile/profile_P1/essay.pdf"
    ])
    # Use gemini_files in Gemini generate_content call
"""

import io
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types


@dataclass
class GeminiFile:
    """Gemini uploaded file info"""
    name: str           # Gemini file ID (e.g., "files/abc123")
    uri: str            # Gemini file URI
    display_name: str   # Original filename
    state: str          # PROCESSING | ACTIVE | FAILED
    size_bytes: Optional[int] = None


class LocalPDFLoader:
    """
    Local PDF → Gemini Files API Loader

    Reads local PDF files and uploads them to Gemini for multimodal analysis.
    """

    def __init__(self, gemini_api_key: str):
        """
        Args:
            gemini_api_key: Gemini API key
        """
        self.genai_client = genai.Client(api_key=gemini_api_key)

    def _upload_to_gemini(
        self,
        pdf_bytes: bytes,
        filename: str,
        wait_for_processing: bool = True,
        max_wait_seconds: int = 60
    ) -> GeminiFile:
        """
        Upload PDF to Gemini Files API

        Args:
            pdf_bytes: PDF file bytes
            filename: File name
            wait_for_processing: Wait for processing to complete
            max_wait_seconds: Maximum wait time (seconds)

        Returns:
            GeminiFile: Uploaded file info
        """
        file_obj = io.BytesIO(pdf_bytes)
        file_obj.name = filename

        uploaded_file = self.genai_client.files.upload(
            file=file_obj,
            config=types.UploadFileConfig(
                display_name=filename,
                mime_type='application/pdf'
            )
        )

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

    def load_file(
        self,
        file_path: str,
        wait_for_processing: bool = True,
        max_wait_seconds: int = 60
    ) -> GeminiFile:
        """
        Load a single local PDF file and upload to Gemini

        Args:
            file_path: Path to the local PDF file
            wait_for_processing: Wait for Gemini processing
            max_wait_seconds: Maximum wait time (seconds)

        Returns:
            GeminiFile: Uploaded file info

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a PDF
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() != '.pdf':
            raise ValueError(f"Not a PDF file: {file_path}")

        pdf_bytes = path.read_bytes()
        filename = path.name

        return self._upload_to_gemini(
            pdf_bytes=pdf_bytes,
            filename=filename,
            wait_for_processing=wait_for_processing,
            max_wait_seconds=max_wait_seconds
        )

    def load_files(
        self,
        file_paths: list[str],
        wait_for_processing: bool = True,
        max_wait_seconds: int = 60
    ) -> list[GeminiFile]:
        """
        Load multiple local PDF files and upload to Gemini

        Args:
            file_paths: List of paths to local PDF files
            wait_for_processing: Wait for Gemini processing
            max_wait_seconds: Maximum wait time per file (seconds)

        Returns:
            list[GeminiFile]: List of uploaded file info

        Raises:
            FileNotFoundError: If any file doesn't exist
            ValueError: If any file is not a PDF
        """
        gemini_files = []
        for file_path in file_paths:
            gemini_file = self.load_file(
                file_path=file_path,
                wait_for_processing=wait_for_processing,
                max_wait_seconds=max_wait_seconds
            )
            gemini_files.append(gemini_file)

        return gemini_files

    def load_from_bytes(
        self,
        pdf_bytes: bytes,
        filename: str,
        wait_for_processing: bool = True
    ) -> GeminiFile:
        """
        Upload PDF bytes directly to Gemini (for FastAPI UploadFile)

        Args:
            pdf_bytes: PDF file bytes
            filename: File name
            wait_for_processing: Wait for processing

        Returns:
            GeminiFile: Uploaded file info
        """
        return self._upload_to_gemini(
            pdf_bytes=pdf_bytes,
            filename=filename,
            wait_for_processing=wait_for_processing
        )

    def delete_file(self, gemini_file: GeminiFile) -> bool:
        """
        Delete file from Gemini (cleanup)

        Args:
            gemini_file: File to delete

        Returns:
            bool: Success status
        """
        try:
            self.genai_client.files.delete(name=gemini_file.name)
            return True
        except Exception:
            return False

    def delete_files(self, gemini_files: list[GeminiFile]) -> int:
        """
        Delete multiple files from Gemini

        Args:
            gemini_files: Files to delete

        Returns:
            int: Number of successfully deleted files
        """
        deleted_count = 0
        for gemini_file in gemini_files:
            if self.delete_file(gemini_file):
                deleted_count += 1
        return deleted_count
