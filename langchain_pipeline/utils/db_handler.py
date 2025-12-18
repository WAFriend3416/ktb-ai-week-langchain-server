"""
MongoDB 데이터베이스 핸들러

회사/구직자 프로필 및 비교 결과 저장/조회
"""

from datetime import datetime
from typing import Any, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from langchain_pipeline.config import MONGODB_URI, MONGODB_DB_NAME, COLLECTIONS


class DatabaseHandler:
    """MongoDB 데이터베이스 핸들러"""

    def __init__(
        self,
        uri: str = MONGODB_URI,
        db_name: str = MONGODB_DB_NAME
    ):
        """
        Args:
            uri: MongoDB 연결 URI
            db_name: 데이터베이스 이름
        """
        self.client: MongoClient = MongoClient(uri)
        self.db: Database = self.client[db_name]

    def _get_collection(self, collection_key: str) -> Collection:
        """컬렉션 객체 반환"""
        collection_name = COLLECTIONS.get(collection_key, collection_key)
        return self.db[collection_name]

    # ===== 회사 프로필 =====
    def save_company_profile(self, profile: dict[str, Any]) -> str:
        """
        회사 프로필 저장

        Args:
            profile: 회사 컬쳐핏 분석 결과

        Returns:
            저장된 문서의 ID
        """
        profile["created_at"] = datetime.utcnow()
        profile["updated_at"] = datetime.utcnow()

        collection = self._get_collection("companies")
        result = collection.insert_one(profile)
        return str(result.inserted_id)

    def get_company_profile(self, company_name: str) -> Optional[dict[str, Any]]:
        """회사 프로필 조회 (이름으로)"""
        collection = self._get_collection("companies")
        return collection.find_one({"company_meta.company_name": company_name})

    def find_similar_companies(self, company_name: str) -> list[dict[str, Any]]:
        """유사 회사명 검색"""
        collection = self._get_collection("companies")
        return list(collection.find({
            "company_meta.company_name": {"$regex": company_name, "$options": "i"}
        }))

    # ===== 구직자 프로필 =====
    def save_applicant_profile(self, profile: dict[str, Any]) -> str:
        """
        구직자 프로필 저장

        Args:
            profile: 구직자 분석 결과

        Returns:
            저장된 문서의 ID
        """
        profile["created_at"] = datetime.utcnow()
        profile["updated_at"] = datetime.utcnow()

        collection = self._get_collection("applicants")
        result = collection.insert_one(profile)
        return str(result.inserted_id)

    def get_applicant_profile(self, candidate_name: str) -> Optional[dict[str, Any]]:
        """구직자 프로필 조회 (이름으로)"""
        collection = self._get_collection("applicants")
        return collection.find_one({"profile_meta.candidate_name": candidate_name})

    # ===== 비교 결과 =====
    def save_comparison_result(self, result: dict[str, Any]) -> str:
        """
        컬쳐핏 비교 결과 저장

        Args:
            result: 비교 분석 결과

        Returns:
            저장된 문서의 ID
        """
        result["created_at"] = datetime.utcnow()

        collection = self._get_collection("comparisons")
        insert_result = collection.insert_one(result)
        return str(insert_result.inserted_id)

    def get_comparisons_by_applicant(self, candidate_name: str) -> list[dict[str, Any]]:
        """특정 구직자의 모든 비교 결과 조회"""
        collection = self._get_collection("comparisons")
        return list(collection.find({"applicant_name": candidate_name}))

    def get_comparisons_by_company(self, company_name: str) -> list[dict[str, Any]]:
        """특정 회사의 모든 비교 결과 조회"""
        collection = self._get_collection("comparisons")
        return list(collection.find({"company_name": company_name}))

    # ===== 유틸리티 =====
    def close(self):
        """연결 종료"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
