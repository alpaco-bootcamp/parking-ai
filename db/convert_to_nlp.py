import json
import pymongo
from typing import List, Dict, Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from common.data import MONGO_URI, DB_NAME


# Pydantic 모델 정의
class FullDocumentModel(BaseModel):
    """전체 문서 형태의 자연어 변환 데이터 모델"""
    id: str = Field(..., alias="_id")  # ...: 필수필드, MongoDB: _id로 저장/조회
    product_name: str
    full_content: str

    # _id, id 호환 가능
    class Config:
        populate_by_name = True
        validate_by_name = True


class ChunkModel(BaseModel):
    """청크 단위의 자연어 변환 데이터 모델"""
    # basic_info: 기본정보(상품명, 은행, 금리, 유형, 가입방식)
    # product_guide: 가입정보(대상, 방법, 한도)
    # rate_structure: 금리구간(예치금액별 차등금리)
    # preferential_intro: 우대조건 개요(intro정보)
    # condition_N: 우대조건 개별분리

    product_code: str
    product_name: str
    chunk_type: str  # basic_info, product_guide, rate_structure, preferential_intro, condition_N
    chunk_index: int
    content: str


class ParkingProductNLPConverter:
    def __init__(self, mongo_uri: str, db_name: str):
        """
        MongoDB 연결 초기화
        """
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.products_details = self.db['product_details']
        self.nlp_full = self.db['products_nlp_full']
        self.nlp_chunks = self.db['products_nlp_chunks']

    def convert_to_full_document(self, product: Dict[str, Any]) -> FullDocumentModel:
        """
        통장 정보를 마크다운 형태의 전체 문서로 변환

        Args:
            product: products_details 컬렉션의 단일 문서

        Returns:
            FullDocumentModel: 전체 문서 형태의 자연어 변환 데이터
        """
        product_name = product.get('product_name', '알 수 없는 상품')
        company_name = product.get('company_name', '알 수 없는 은행')
        basic_rate = product.get('interest_rate', 0)
        prime_rate = product.get('prime_interest_rate', 0)
        rate_type = product.get('rate_type', '일반형') # 변동금리..
        categories = product.get('categories', [])

        # 마크다운 헤더
        content = f"## {product_name}\n"
        content += f"### 은행: {company_name}\n"
        content += f"### 기본 금리: {basic_rate}%\n"
        content += f"### 최고 우대금리: {prime_rate}%\n"
        content += f"### 금리 유형: {rate_type}\n"
        content += f"### 가입 방식: {', '.join(categories) if categories else '없음'}\n"


        # 상품 가이드 정보
        if 'product_guide' in product:
            guide = product['product_guide']
            if guide.get('target_customer'):
                content += f"### 가입대상: {guide['target_customer']}\n"
            if guide.get('signup_method'):
                content += f"### 가입방법: {guide['signup_method']}\n"
            if guide.get('amount_limit'):
                content += f"### 가입한도: {guide['amount_limit']}\n"

        interest_guide = product['interest_guide']

        # 금리 구간 정보 (basic_rate_info)
        rate_info = interest_guide.get('basic_rate_info', [])
        if rate_info:
            content += "### 금리 구간:\n"
            for info in rate_info:
                # 형태 1: condition과 rate가 있는 경우
                if 'condition' in info and 'rate' in info:
                    content += f"  - {info['condition']}: {info['rate']}\n"
                # 형태 2: text로 통합된 경우
                elif 'text' in info:
                    text_desc = info['text'].replace('\n', ' ').strip()
                    content += f"  - {text_desc}\n"

        # 우대조건 (preferential_details에)
        # preferential_details에 conditions가 있는지 확인
        preferential_details = interest_guide.get('preferential_details', {})
        conditions = preferential_details.get('conditions', [])

        if conditions:
            content += "### 우대조건:\n"

            # intro가 있으면 먼저 추가
            intro = preferential_details.get('intro', '')
            if intro:
                content += f"  - {intro}\n"

            # 각 조건들 추가 (index 활용)
            for condition in conditions:
                condition_index = condition.get('index', '')
                desc = condition.get('description', '')
                if condition_index and desc:
                    content += f"  {condition_index}. {desc}\n"
                elif desc:  # index가 없는 경우
                    content += f"  - {desc}\n"
        else:
            content += "### 우대조건: 없음\n"


        content += "---\n"

        return FullDocumentModel(
            _id=product.get('_id', ''),
            product_name=product_name,
            full_content=content
        )

    def convert_to_chunks(self, product: Dict[str, Any]) -> List[ChunkModel]:
        """
        통장 정보를 기능별 청크로 분할

        Args:
            product: products_details 컬렉션의 단일 문서

        Returns:
            List[ChunkModel]: 청크 단위의 자연어 변환 데이터 리스트
        """
        chunks = []
        product_id = product.get('_id', '')
        product_name = product.get('product_name', '알 수 없는 상품')
        company_name = product.get('company_name', '알 수 없는 은행')

        # 청크 1: 기본 정보
        basic_rate = product.get('interest_rate', 0)
        prime_rate = product.get('prime_interest_rate', 0)
        basic_content = f"{product_name}은 {company_name}의 파킹통장으로 기본금리 {basic_rate}%, 최고우대금리 {prime_rate}%를 제공합니다."

        chunks.append(ChunkModel(
            product_id=product_id,
            product_name=product_name,
            chunk_type='basic_info',
            chunk_index=1,
            content=basic_content
        ))

        chunk_index = 2

        # 청크 2-N: 우대조건별 분할
        if 'interest_guide' in product and 'preferential_details' in product['interest_guide']:
            conditions = product['interest_guide']['preferential_details'].get('conditions', [])
            for i, condition in enumerate(conditions):
                desc = condition.get('description', '').replace('\n', ' ').strip()
                # 긴 설명은 핵심 내용만 추출
                if len(desc) > 150:
                    desc = desc[:150] + "..."

                condition_content = f"{product_name}의 우대조건: {desc}"
                chunks.append(ChunkModel(
                    product_id=product_id,
                    product_name=product_name,
                    chunk_type=f'condition_{i + 1}',
                    chunk_index=chunk_index,
                    content=condition_content
                ))
                chunk_index += 1

        # 청크 N+1: 가입 정보
        if 'product_guide' in product:
            guide = product['product_guide']
            signup_parts = []

            if guide.get('target_customer'):
                signup_parts.append(f"대상: {guide['target_customer']}")
            if guide.get('signup_method'):
                signup_parts.append(f"방법: {guide['signup_method']}")
            if guide.get('amount_limit'):
                signup_parts.append(f"한도: {guide['amount_limit']}")

            if signup_parts:
                signup_content = f"{product_name} 가입정보 - " + ", ".join(signup_parts)
                chunks.append(ChunkModel(
                    product_id=product_id,
                    product_name=product_name,
                    chunk_type='signup_info',
                    chunk_index=chunk_index,
                    content=signup_content
                ))

        return chunks

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
        all_chunks = []

        for i, product in enumerate(products, 1):
            print(f"처리 중: {i}/{len(products)} - {product.get('product_name', 'Unknown')}")

            # Full Document 변환
            full_doc_model = self.convert_to_full_document(product)
            # Pydantic 모델을 dict로 변환하고 created_at 추가
            full_doc_dict = full_doc_model.model_dump(by_alias=True)
            full_doc_dict['created_at'] = datetime.now()
            full_documents.append(full_doc_dict)

            # Chunks 변환
            chunk_models = self.convert_to_chunks(product)
            for chunk_model in chunk_models:
                # Pydantic 모델을 dict로 변환하고 created_at 추가
                chunk_dict = chunk_model.model_dump()
                chunk_dict['created_at'] = datetime.now()
                all_chunks.append(chunk_dict)

        # MongoDB에 저장
        print("\n💾 Full Documents 저장 중...")
        if full_documents:
            self.nlp_full.insert_many(full_documents)
            print(f"✅ {len(full_documents)}개 전체 문서 저장 완료")

        print("\n💾 Chunks 저장 중...")
        if all_chunks:
            self.nlp_chunks.insert_many(all_chunks)
            print(f"✅ {len(all_chunks)}개 청크 저장 완료")

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
            # 평균 문서 길이
            pipeline = [
                {"$project": {"content_length": {"$strLenCP": "$full_content"}}},
                {"$group": {"_id": None, "avg_length": {"$avg": "$content_length"}}}
            ]
            result = list(self.nlp_full.aggregate(pipeline))
            if result:
                print(f"평균 문서 길이: {result[0]['avg_length']:.0f} 글자")

        # Chunks 통계
        chunk_count = self.nlp_chunks.count_documents({})
        print(f"총 청크 수: {chunk_count}")

        if chunk_count > 0:
            # 청크 타입별 분포
            pipeline = [
                {"$group": {"_id": "$chunk_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
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
            print("내용:")
            print(doc['full_content'])
            print("-" * 40)

        # Chunks 샘플
        print("\n🧩 Chunks 샘플:")
        for chunk in self.nlp_chunks.find().limit(limit):
            print(f"\n상품: {chunk['product_name']} | 타입: {chunk['chunk_type']}")
            print(f"내용: {chunk['content']}")
            print("-" * 40)


def main():
    """
    메인 실행 함수
    """
    try:
        converter = ParkingProductNLPConverter(MONGO_URI, DB_NAME)
        # print("🚀 파킹통장 자연어 변환 시작")
        # converter.process_and_save()
        #
        # print("\n미리보기를 확인하시겠습니까? (y/n): ", end="")
        # choice = input().lower()
        # if choice == 'y':
        #     converter.sample_preview()

        # print("\n✅ 변환 완료!")

        # 데이터만 반환하는 함수 사용 예제
        print("\n🔧 데이터 반환 함수 테스트...")
        products = list(converter.products_details.find().limit(10))

        for product in products:
            # Full Documents 변환 테스트
            full_doc = converter.convert_to_full_document(product)
            print(f"Full Document 변환 완료: {full_doc.full_content}")
            print('===')
            # Chunks 변환 테스트
            chunks = converter.convert_to_chunks(product)
            print(f"Chunks 변환 완료: {chunks}")
            print('=' * 30)

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()