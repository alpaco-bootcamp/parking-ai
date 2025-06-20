import json
import pymongo
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from pydantic import BaseModel, Field

from common.data import MONGO_URI, DB_NAME


# Pydantic 모델 정의
class FullDocumentModel(BaseModel):
    """전체 문서 형태의 자연어 변환 데이터 모델"""

    id: str = Field(..., alias="_id")  # ...: 필수필드, MongoDB: _id로 저장/조회
    product_code: str
    product_name: str
    content_natural: str  # 벡터 검색용(문장형)
    content_structured: str  # llm 분석용(구조화)

    # _id, id 호환 가능
    class Config:
        populate_by_name = True
        validate_by_name = True


class ChunkModel(BaseModel):
    """청크 단위의 자연어 변환 데이터 모델 (product 정보 제외)"""

    # basic_info: 기본정보(상품명, 은행, 금리, 유형, 가입방식)
    # product_guide: 가입정보(대상, 방법, 한도)
    # basic_rate_info: 기본 금리(예치금액별, 기간별 차등금리)
    # preferential_intro: 우대조건 개요(intro정보)
    chunk_type: (
        str  # basic_info, product_guide, rate_structure, preferential_conditions
    )
    chunk_index: int
    content_natural: str  # 벡터 검색용(문장형)
    content_structured: str  # llm 분석용(구조화)


class ProductChunksModel(BaseModel):
    """상품별 청크 데이터 모델"""

    product_code: str
    product_name: str
    chunks: list[ChunkModel]


class ParkingProductNLPConverter:
    def __init__(self, mongo_uri: str, db_name: str):
        """
        MongoDB 연결 초기화
        """
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.products_details = self.db["product_details"]
        self.nlp_full = self.db["products_nlp_full"]
        self.nlp_chunks = self.db["products_nlp_chunks"]

    # START: 공통 함수들
    # 컨벤션 규칙: private method는 앞에 '_'추가
    @staticmethod
    def _extract_basic_info(product: dict[str, Any]) -> dict[str, Any]:
        """상품 기본 정보 추출"""
        return {
            "product_name": product.get("product_name", "알 수 없는 상품"),
            "company_name": product.get("company_name", "알 수 없는 은행"),
            "basic_rate": product.get("interest_rate", 0),
            "prime_rate": product.get("prime_interest_rate", 0),
            "rate_type": product.get("interest_guide", {}).get("rate_type", "일반형"),
            "categories": product.get("categories", []),
            "product_code": product.get("product_code", product.get("_id", "")),
        }

    @staticmethod
    def _extract_product_guide_info(product: dict[str, Any]) -> dict[str, str]:
        """상품 가이드 정보 추출"""
        guide = product.get("product_guide", {})
        return {
            "target_customer": guide.get("target_customer", ""),
            "signup_method": guide.get("signup_method", ""),
            "amount_limit": guide.get("amount_limit", ""),
        }

    @staticmethod
    def _extract_basic_rate_info(product: dict[str, Any]) -> list[dict[str, str]]:
        """기본 금리 정보 추출"""
        interest_guide = product.get("interest_guide", {})
        return interest_guide.get("basic_rate_info", [])

    @staticmethod
    def _extract_preferential_details_info(product: dict[str, Any]) -> dict[str, Any]:
        """우대조건 정보 추출"""
        interest_guide = product.get("interest_guide", {})
        preferential_details = interest_guide.get("preferential_details", {})
        return {
            "intro": preferential_details.get("intro", ""),
            "conditions": preferential_details.get("conditions", []),
        }

    # 청크별 텍스트 생성 함수들 (구조화, 자연어 튜플 반환)
    @staticmethod
    def _generate_basic_info_content(basic_info: dict) -> tuple[str, str]:
        """기본 정보 텍스트 생성 (구조화, 자연어)"""
        # 구조화된 텍스트
        structured = f"### 상품명: {basic_info['product_name']}\n"
        structured += f"### 은행: {basic_info['company_name']}\n"
        structured += f"### 기본 금리: {basic_info['basic_rate']}%\n"
        structured += f"### 최고 우대금리: {basic_info['prime_rate']}%\n"
        structured += f"### 금리 유형: {basic_info['rate_type']}\n"
        structured += f"### 가입 방식: {', '.join(basic_info['categories']) if basic_info['categories'] else '없음'}\n"

        # 자연어 텍스트
        natural = f"{basic_info['product_name']}은 {basic_info['company_name']}의 {basic_info['rate_type']} 파킹통장으로 "
        natural += f"기본금리 {basic_info['basic_rate']}%, 최고우대금리 {basic_info['prime_rate']}%를 제공합니다."
        if basic_info["categories"]:
            natural += f" 가입방식은 {', '.join(basic_info['categories'])}입니다."

        return structured, natural

    @staticmethod
    def _generate_product_guide_content(guide_info: dict) -> tuple[str, str]:
        """상품 가이드 텍스트 생성 (구조화, 자연어)"""
        if not any(guide_info.values()):
            return "### 가입정보: 없음\n", "가입정보는 없습니다."

        # 구조화된 텍스트
        structured = "### 가입정보\n"
        if guide_info["target_customer"]:
            structured += f"- 가입대상: {guide_info['target_customer']}\n"
        if guide_info["signup_method"]:
            structured += f"- 가입방법: {guide_info['signup_method']}\n"
        if guide_info["amount_limit"]:
            structured += f"- 가입한도: {guide_info['amount_limit']}\n"

        # 자연어 텍스트
        guide_parts = []
        if guide_info["target_customer"]:
            guide_parts.append(f"가입대상: {guide_info['target_customer']}")
        if guide_info["signup_method"]:
            guide_parts.append(f"가입방법: {guide_info['signup_method']}")
        if guide_info["amount_limit"]:
            guide_parts.append(f"가입한도: {guide_info['amount_limit']}")

        natural = "가입정보 - " + ", ".join(guide_parts)

        return structured, natural

    @staticmethod
    def _generate_basic_rate_content(rate_info: list) -> tuple[str, str]:
        """기본 금리 텍스트 생성 (구조화, 자연어)"""
        if not rate_info:
            return "### 금리 구간: 없음\n", "금리구간 정보는 없습니다."

        # 구조화된 텍스트
        structured = "### 금리 구간\n"
        for info in rate_info:
            if "condition" in info and "rate" in info:
                structured += f"- {info['condition']}: {info['rate']}\n"
            elif "text" in info:
                text_desc = info["text"].replace("\n", " ").strip()
                structured += f"- {text_desc}\n"

        # 자연어 텍스트
        rate_parts = []
        for info in rate_info:
            if "condition" in info and "rate" in info:
                rate_parts.append(f"{info['condition']}: {info['rate']}")
            elif "text" in info:
                rate_parts.append(info["text"].replace("\n", " ").strip())

        natural = "금리정보 - " + ", ".join(rate_parts)

        return structured, natural

    @staticmethod
    def _generate_preferential_details_content(
        preferential_info: dict,
    ) -> tuple[str, str]:
        """우대조건 텍스트 생성 (구조화, 자연어)"""
        intro = preferential_info["intro"]
        conditions = preferential_info["conditions"]

        # 우대조건이 없는 경우
        if not intro and not conditions:
            return "### 우대조건: 없음\n", "우대조건은 없습니다."

        # 구조화된 텍스트
        structured = "### 우대조건\n"
        if intro:
            structured += f"#### 개요\n- {intro}\n"

        if conditions:
            structured += "#### 세부조건\n"
            for condition in conditions:
                condition_idx = condition.get("index", "")
                desc = condition.get("description", "")
                if condition_idx and desc:
                    structured += f"{condition_idx}. {desc}\n"
                elif desc:
                    structured += f"- {desc}\n"

        # 자연어 텍스트
        natural = "우대조건"
        if intro:
            natural += f" - 개요: {intro}"

        if conditions:
            natural += " - 세부조건: "
            condition_parts = []
            for condition in conditions:
                desc = condition.get("description", "").replace("\n", " ").strip()
                condition_idx = condition.get("index", "")
                if desc:
                    if condition_idx:
                        condition_parts.append(f"{condition_idx}.: {desc}")
                    else:
                        condition_parts.append(desc)
            natural += " / ".join(condition_parts)

        return structured, natural

    # END: 공통 함수들

    def convert_to_full_document(self, product: dict[str, Any]) -> FullDocumentModel:
        """
        통장 정보를 마크다운 형태의 전체 문서로 변환 (구조화 + 자연어 모두 생성)

        Args:
            product: products_details 컬렉션의 단일 문서

        Returns:
            FullDocumentModel: 전체 문서 형태의 자연어 변환 데이터
        """
        # 공통 함수로 데이터 추출
        basic_info = self._extract_basic_info(product)
        guide_info = self._extract_product_guide_info(product)
        rate_info = self._extract_basic_rate_info(product)
        preferential_info = self._extract_preferential_details_info(product)

        # 각 섹션별 텍스트 생성
        basic_structured, basic_natural = self._generate_basic_info_content(basic_info)
        guide_structured, guide_natural = self._generate_product_guide_content(
            guide_info
        )
        rate_structured, rate_natural = self._generate_basic_rate_content(rate_info)
        pref_structured, pref_natural = self._generate_preferential_details_content(
            preferential_info
        )

        # 전체 구조화된 텍스트 조합
        structured_content = f"## {basic_info['product_name']}\n"
        structured_content += basic_structured
        structured_content += guide_structured
        structured_content += rate_structured
        structured_content += pref_structured
        structured_content += "---\n"

        # 전체 자연어 텍스트 조합 (상품명 중복 최소화)
        natural_content = (
            f"{basic_natural} {guide_natural} {rate_natural} {pref_natural}"
        )

        return FullDocumentModel(
            _id=product.get("_id", ""),
            product_code=basic_info["product_code"],
            product_name=basic_info["product_name"],
            content_natural=natural_content.strip(),  # 벡터 검색용
            content_structured=structured_content,  # LLM 분석용
        )

    def convert_to_chunks(self, product: dict[str, Any]) -> ProductChunksModel:
        """
        통장 정보를 기능별 청크로 분할하여 상품별 구조로 반환

        Args:
            product: products_details 컬렉션의 단일 문서

        Returns:
            ProductChunksModel: 상품 정보와 청크 리스트가 포함된 데이터
        """
        # 공통 함수로 데이터 추출
        basic_info = self._extract_basic_info(product)
        guide_info = self._extract_product_guide_info(product)
        rate_info = self._extract_basic_rate_info(product)
        preferential_info = self._extract_preferential_details_info(product)

        chunks = []
        chunk_index = 1
        product_name = basic_info["product_name"]

        # 청크 1: 기본 정보
        basic_structured, basic_natural = self._generate_basic_info_content(basic_info)
        chunks.append(
            ChunkModel(
                chunk_type="basic_info",
                chunk_index=chunk_index,
                content_structured=basic_structured,
                content_natural=basic_natural,  # 기본정보는 상품명이 이미 포함됨
            )
        )
        chunk_index += 1

        # 청크 2: 상품 가이드 정보
        guide_structured, guide_natural = self._generate_product_guide_content(
            guide_info
        )
        # 상품명이 없는 경우 추가
        if not guide_natural.startswith(product_name):
            guide_structured = f"##{product_name}\n {guide_structured}"
            guide_natural = f"{product_name} {guide_natural}"

        chunks.append(
            ChunkModel(
                chunk_type="product_guide",
                chunk_index=chunk_index,
                content_structured=guide_structured,
                content_natural=guide_natural,
            )
        )
        chunk_index += 1

        # 청크 3: 기본 금리 정보
        rate_structured, rate_natural = self._generate_basic_rate_content(rate_info)
        # 상품명이 없는 경우 추가
        if not rate_natural.startswith(product_name):
            rate_structured = f"##{product_name}\n {rate_structured}"
            rate_natural = f"{product_name}의 {rate_natural}"

        chunks.append(
            ChunkModel(
                chunk_type="basic_rate_info",
                chunk_index=chunk_index,
                content_structured=rate_structured,
                content_natural=rate_natural,
            )
        )
        chunk_index += 1

        # 청크 4: 우대조건 정보
        pref_structured, pref_natural = self._generate_preferential_details_content(
            preferential_info
        )
        # 상품명이 없는 경우 추가
        if not pref_natural.startswith(product_name):
            if pref_natural.startswith("우대조건"):
                pref_structured = f"##{product_name}\n {pref_structured}"
                pref_natural = f"{product_name}의 {pref_natural}"
            else:
                pref_structured = f"##{product_name}\n {pref_structured}"
                pref_natural = f"{product_name} {pref_natural}"

        chunks.append(
            ChunkModel(
                chunk_type="preferential_details",
                chunk_index=chunk_index,
                content_structured=pref_structured,
                content_natural=pref_natural,
            )
        )

        return ProductChunksModel(
            product_code=basic_info["product_code"],
            product_name=basic_info["product_name"],
            chunks=chunks,
        )

    def process_and_save(self):
        """
        products_details에서 데이터를 읽어 자연어로 변환하여 저장
        """
        # 기존 NLP 컬렉션 초기화
        self.nlp_full.drop()
        self.nlp_chunks.drop()

        print("📊 products_details에서 데이터 읽는 중...")
        products = list(self.products_details.find())
        print(f"총 {len(products)}개 상품 발견")

        full_documents = []
        chunk_documents = []  # 변경: all_chunks -> chunk_documents

        for i, product in enumerate(products, 1):
            print(
                f"처리 중: {i}/{len(products)} - {product.get('product_name', 'Unknown')}"
            )

            # Full Document 변환
            full_doc_model = self.convert_to_full_document(product)
            # Pydantic 모델을 dict로 변환하고 created_at 추가
            full_doc_dict = full_doc_model.model_dump(by_alias=True)
            full_doc_dict["created_at"] = datetime.now()
            full_documents.append(full_doc_dict)

            # Chunks 변환 - ProductChunksModel 전체를 하나의 문서로 저장
            product_chunks_model = self.convert_to_chunks(product)
            # ProductChunksModel을 dict로 변환하고 created_at 추가
            chunk_doc_dict = product_chunks_model.model_dump()
            chunk_doc_dict["created_at"] = datetime.now()
            chunk_documents.append(chunk_doc_dict)

        # MongoDB에 저장
        print("\n💾 Full Documents 저장 중...")
        if full_documents:
            self.nlp_full.insert_many(full_documents)
            print(f"✅ {len(full_documents)}개 전체 문서 저장 완료")

        print("\n💾 Chunk Documents 저장 중...")
        if chunk_documents:
            self.nlp_chunks.insert_many(chunk_documents)
            print(f"✅ {len(chunk_documents)}개 청크 문서 저장 완료")

        # 통계 출력
        self.print_statistics()

    def print_statistics(self):
        """
        변환 결과 통계 출력
        """
        print("\n📈 변환 결과 통계")
        print("=" * 50)

        # Full Documents 통계
        full_count = self.nlp_full.count_documents({})
        print(f"전체 문서 수: {full_count}")

        if full_count > 0:
            # 평균 문서 길이 (content_natural 기준)
            pipeline = [
                {"$project": {"content_length": {"$strLenCP": "$content_natural"}}},
                {"$group": {"_id": None, "avg_length": {"$avg": "$content_length"}}},
            ]
            result = list(self.nlp_full.aggregate(pipeline))
            if result:
                print(f"평균 문서 길이 (자연어): {result[0]['avg_length']:.0f} 글자")

        # Chunk Documents 통계
        chunk_doc_count = self.nlp_chunks.count_documents({})
        print(f"청크 문서 수: {chunk_doc_count}")

        if chunk_doc_count > 0:
            # 상품당 평균 청크 개수
            pipeline = [
                {"$project": {"chunks_count": {"$size": "$chunks"}}},
                {"$group": {"_id": None, "avg_chunks": {"$avg": "$chunks_count"}}},
            ]
            result = list(self.nlp_chunks.aggregate(pipeline))
            if result:
                print(f"상품당 평균 청크 개수: {result[0]['avg_chunks']:.1f}개")

            # 청크 타입별 분포
            pipeline = [
                {"$unwind": "$chunks"},
                {"$group": {"_id": "$chunks.chunk_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
            chunk_stats = list(self.nlp_chunks.aggregate(pipeline))
            print("청크 타입별 분포:")
            for stat in chunk_stats:
                print(f"  - {stat['_id']}: {stat['count']}개")

        print("=" * 50)

    def sample_preview(self, limit: int = 3):
        """
        변환 결과 샘플 미리보기
        """
        print(f"\n🔍 변환 결과 미리보기 (상위 {limit}개)")
        print("=" * 80)

        # Full Document 샘플
        print("📄 Full Document 샘플:")
        for doc in self.nlp_full.find().limit(limit):
            print(f"\n상품명: {doc['product_name']}")
            print("자연어 내용:")
            print(
                doc["content_natural"][:200] + "..."
                if len(doc["content_natural"]) > 200
                else doc["content_natural"]
            )
            print("-" * 40)

        # Chunk Documents 샘플
        print("\n🧩 Chunk Documents 샘플:")
        for chunk_doc in self.nlp_chunks.find().limit(limit):
            print(
                f"\n상품: {chunk_doc['product_name']} | 상품코드: {chunk_doc['product_code']}"
            )
            print(f"청크 개수: {len(chunk_doc['chunks'])}개")

            # 각 청크 미리보기
            for chunk in chunk_doc["chunks"]:
                print(
                    f"  - {chunk['chunk_type']} (#{chunk['chunk_index']}): {chunk['content_natural'][:100] + '...' if len(chunk['content_natural']) > 100 else chunk['content_natural']}"
                )
            print("-" * 40)


def main():
    """
    메인 실행 함수
    """
    try:
        converter = ParkingProductNLPConverter(MONGO_URI, DB_NAME)
        print("🚀 파킹통장 자연어 변환 시작")
        converter.process_and_save()
        print("\n🚀 파킹통장 자연어 저장 완료!")

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
