"""
파킹통장 데이터 벡터화 및 Pinecone 저장 모듈

본 모듈은 MongoDB에 저장된 자연어 변환 데이터를 OpenAI 임베딩으로 벡터화하여
별도의 Pinecone 벡터스토어에 저장하는 기능을 제공합니다.

주요 기능:
- content_natural 벡터화, content_structured 메타데이터 저장
"""

import os
from enum import Enum

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from common.enums import DocumentTypeEnum
from db.save_db import get_all_documents

load_dotenv()

# 설정 상수
EMBEDDING_MODEL = "text-embedding-3-small"

class ProductsEmbeddingProcessor:
    """파킹통장 상품 임베딩 처리 클래스"""

    def __init__(self):
        """
        임베딩 프로세서 초기화

        OpenAI 임베딩과 환경변수에서 인덱스명을 설정합니다.
        """

        # OpenAI 임베딩 초기화
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

        # 환경변수에서 인덱스명 로드
        self.full_index_name = os.getenv("INDEX_NAME_FULL")
        self.chunks_index_name = os.getenv("INDEX_NAME_CHUNKS")

        print("✅ 입베딩 프로세스 초기화 완료")

    @staticmethod
    def _load_documents(collection_name: str) -> list[dict]:
        """
        컬렉션에서 문서 데이터 로드

        Returns:
            list[dict]: 전체 문서 데이터 리스트
        """
        print(f"📂 {collection_name}데이터 로드 중..")
        documents = list(get_all_documents(collection_name))
        print(f"✅ {len(documents)}개 문서 로드 완료")
        return documents

    @staticmethod
    def _convert_langchain_documents(
        documents: list[dict], doc_type: DocumentTypeEnum
    ) -> list[Document]:
        """
        MongoDB에서 가져온 파킹통장 데이터를 LangChain Document 형태로 변환

        이 함수는 products_nlp_full 또는 products_nlp_chunks 컬렉션의 데이터를
        LangChain의 Document 객체로 변환합니다. 각 타입에 따라 다른 메타데이터 구조와
        content 처리 방식을 적용합니다.

        Args:
            documents: MongoDB에서 조회한 문서 데이터 리스트
            doc_type (DocumentTypeEnum): 문서 타입 Enum. 'full' 또는 'chunks' 중 하나를 지정

        Returns:
            list[Document]: LangChain Document 객체 리스트
        """

        langchain_documents = []
        total_chunks = 0

        for doc in documents:
            product_code = doc.get("product_code", "")
            product_name = doc.get("product_name", "")

            # 공통 메타데이터 구성
            metadata = {
                "product_code": product_code,
                "product_name": product_name,
                "doc_type": doc_type,
                "text": ",",  # 실제 문서 내용
                "content_structured": "",  # LLM요청용 문서 내용
            }

            # full Type인 경우
            if doc_type == DocumentTypeEnum.FULL:
                content_natural = doc.get("content_natural", "")  # 벡터 검색용
                content_structured = doc.get("content_structured", "")  # llm 요청용
                if not content_natural:
                    print(
                        f"⚠️ {doc.get('product_name', 'Unknown')} - content_natural이 비어있음"
                    )
                    continue

                # Full 메타데이터 구성
                metadata.update(
                    {"text": content_natural, "content_structured": content_structured}
                )

                # LangChain Document 생성
                document = Document(page_content=content_natural, metadata=metadata)

                langchain_documents.append(document)

            # chunks인 경우
            if doc_type == DocumentTypeEnum.CHUNKS:
                chunks = doc.get("chunks", [])

                if not chunks:
                    print(f"⚠️ {product_name} - 청크가 비어있음")
                    continue

                # 청크 데이터 순회
                for chunk in chunks:
                    total_chunks += 1

                    content_natural = chunk.get("content_natural", "")  # 벡터 검색용
                    content_structured = chunk.get(
                        "content_structured", ""
                    )  # llm 요청용

                    if not content_natural:
                        print(
                            f"⚠️ {doc.get('product_name', 'Unknown')} - content_natural이 비어있음"
                        )
                        continue

                    # 📌 자연어 존재하는 경우
                    # Chunks 메타데이터 구성
                    metadata.update(
                        {
                            "text": content_natural,
                            "content_structured": content_structured,
                            "chunk_type": chunk.get("chunk_type", ""),
                            "chunk_index": chunk.get("chunk_index", 0),
                        }
                    )

                    # LangChain Document 생성
                    document = Document(page_content=content_natural, metadata=metadata)
                    langchain_documents.append(document)


            print(f'📀 {doc_type} metatdata: {metadata}')
            print(f"  ✓ {product_name} - Document 생성 완료")

        print(f"📊 총 {total_chunks}개 청크 Document 생성 완료")
        return langchain_documents

    def process_vector_store(self, documents: list[dict], doc_type: DocumentTypeEnum) -> None:
        """
    데이터를 벡터화하여 Pinecone에 저장합니다.

    Args:
        documents (list[dict]): 컬렉션에서 로드한 데이터
        doc_type (DocumentTypeEnum): 문서 타입 Enum. 'full' 또는 'chunks' 중 하나를 지정
    """

        print(f"\n🔄 전체 문서 벡터화 시작 ({len(documents)}개)")

        # LangChain Document 형태로 변환
        documents = self._convert_langchain_documents(documents, doc_type)
        index_name = self.full_index_name if doc_type == DocumentTypeEnum.FULL else self.chunks_index_name

        if not documents:
            print(f"❌ {doc_type}: 처리할 문서가 없습니다")
            return

        # PineconeVectorStore로 벡터화 및 저장
        print(f"\n💾 {len(documents)}개 문서를 {index_name}에 벡터화 및 저장 중...")

        vector_store = PineconeVectorStore.from_documents(
            documents=documents,
            embedding=self.embeddings,
            index_name=index_name
        )

        print(f"✅ 전체 문서 벡터 저장 완료 ({len(documents)}개)")

    def load_vector_store(self, doc_type: DocumentTypeEnum) -> PineconeVectorStore:
        """
                doc_type에 맞는 PineconeVectorStore 객체를 반환

                Args:
                    doc_type (DocumentTypeEnum): 문서 타입 Enum. 'full' 또는 'chunks' 중 하나를 지정

                Returns:
                    PineconeVectorStore: 지정된 인덱스의 벡터스토어 객체
                """
        print(f"🔌 {doc_type} 벡터스토어 연결 중...")

        index_name = self.full_index_name if doc_type == DocumentTypeEnum.FULL else self.chunks_index_name
        vector_store = PineconeVectorStore(embedding=self.embeddings, index_name=index_name)

        print(f"✅ {doc_type} 벡터스토어 연결 완료")
        print('index_name: ', index_name)
        print('doc_type: ', doc_type)
        return vector_store



    def process_all_data(self) -> None:
        """
        전체 데이터 로드 및 벡터화 처리 메인 함수

        MongoDB에서 데이터를 로드하고 두 개의 Pinecone 인덱스에 각각 저장합니다.
        """

        try:
            print("🚀 파킹통장 데이터 벡터화 시작")
            print("=" * 60)

            # 1. 전체 문서 처리
            # full_documents = self._load_documents('products_nlp_full')
            # self.process_vector_store(documents=full_documents, doc_type=DocumentTypeEnum.FULL)

            # 2. 청크 문서 처리
            chunks_documents = self._load_documents('products_nlp_chunks')
            self.process_vector_store(documents=chunks_documents, doc_type=DocumentTypeEnum.CHUNKS)

        except Exception as e:
            print(f'⚠️ 벡터스토어 처리중 오류 {e}')


if __name__ == "__main__":
    embedding_processor = ProductsEmbeddingProcessor()
    # 벡터화 및 저장
    # embedding_processor.process_all_data()

    # 벡터스토어 불러오기
    # full_vector_store = embedding_processor.load_vector_store(DocumentTypeEnum.FULL)
    chunk_vector_store = embedding_processor.load_vector_store(DocumentTypeEnum.CHUNKS)
    # print(f"chunk_vector_store: {full_vector_store}")
