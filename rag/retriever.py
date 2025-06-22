"""
RAG 검색 시스템 구현

이 모듈은 Pinecone 벡터스토어를 활용하여 파킹통장 데이터를 검색하고,
full 벡터스토어와 chunks 벡터스토어의 검색 품질을 비교하는 기능을 제공합니다.

주요 기능:
- Full 문서 검색 및 LLM 응답
- Chunks 문서 검색 및 LLM 응답
- page_content vs content_structured 비교
"""

from dataclasses import dataclass
from enum import Enum

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

from common.enums import DocumentTypeEnum
from rag.embedding_processor import ProductsEmbeddingProcessor
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

@dataclass
class ContentTypeEnum(str, Enum):
    """LLM에 전달할 컨텐츠 타입"""

    PAGE_CONTENT = "page_content"  # 벡터화된 자연어 텍스트 (기본 LangChain 방식)
    CONTENT_STRUCTURED = "content_structured"  # 구조화된 메타데이터 텍스트

class ParkingRetriever:
    """파킹통장 RAG 검색 시스템"""

    def __init__(self):
        """검색 시스템 초기화"""
        self.embedding_processor = ProductsEmbeddingProcessor()
        self.embeddings = self.embedding_processor.embeddings

        # LLM 초기화
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

        # 벡터스토어 로드
        self.full_vector_store = None
        self.chunks_vector_store = None

        # 테스트 쿼리 정의
        self.test_queries = [
            {
                "query": "7% 고금리 파킹통장 찾고 있어요. 우대금리도 가능해요",
                "expected_chunks": ["basic_rate_info", "preferential_details"],
                "description": "고금리 조건 검색 테스트",
            },
            {
                "query": "비대면으로 가입할 수 있는 통장이 있나요?",
                "expected_chunks": ["product_guide", "preferential_details"],
                "description": "가입 방법 검색 테스트",
            },
            {
                "query": "마케팅 수신 동의하면 우대금리 받을 수 있는 곳은?",
                "expected_chunks": ["preferential_details"],
                "description": "우대조건 검색 테스트",
            },
            # {
            #     "query": "OK저축은행 파킹통장 금리가 어떻게 되나요?",
            #     "expected_chunks": ["basic_info", "basic_rate_info"],
            #     "description": "특정 은행 상품 검색 테스트",
            # },
            # {
            #     "query": "1000만원 넣을 수 있는 파킹통장 추천해주세요",
            #     "expected_chunks": ["product_guide", "basic_rate_info"],
            #     "description": "예치 한도 기반 검색 테스트",
            # },
        ]

        print("✅ ParkingRetriever 초기화 완료")

    def load_vector_stores(self):
        """벡터스토어 지연 로딩"""
        if self.full_vector_store is None:
            self.full_vector_store = self.embedding_processor.load_vector_store(
                DocumentTypeEnum.FULL
            )
        if self.chunks_vector_store is None:
            self.chunks_vector_store = self.embedding_processor.load_vector_store(
                DocumentTypeEnum.CHUNKS
            )

    def llm_with_full(
        self, query: str, k: int = 5, use_structured: bool = False
    ) -> str:
        """
        Full 벡터스토어로 검색하여 LLM 응답 생성

        Args:
            query: 검색 쿼리
            k: 검색할 문서 수
            use_structured: True면 content_structured, False면 page_content 사용

        Returns:
            str: LLM 응답
        """
        self.load_vector_stores()

        print(f"📖 Full 벡터스토어 검색 중... (k={k})")

        # 1. 벡터 검색
        docs_with_scores = self.full_vector_store.similarity_search_with_score(
            query, k=k
        )

        # 2. content_structured 사용하는 경우 page_content 교체
        if use_structured:
            docs = []
            for doc, score in docs_with_scores:
                structured_content = doc.metadata.get(
                    "content_structured", doc.page_content
                )
                new_doc = Document(
                    page_content=structured_content, metadata=doc.metadata
                )
                docs.append(new_doc)
            content_type = ContentTypeEnum.CONTENT_STRUCTURED
        else:
            docs = [doc for doc, score in docs_with_scores]
            content_type = ContentTypeEnum.PAGE_CONTENT

        # 3. LLM 응답 생성
        return self.generate_llm_response(query, docs, content_type, "Full")

    def llm_with_chunks(
        self, query: str, k: int = 10, use_structured: bool = False
    ) -> str:
        """
        Chunks 벡터스토어로 검색하여 LLM 응답 생성

        Args:
            query: 검색 쿼리
            k: 검색할 문서 수
            use_structured: True면 content_structured, False면 page_content 사용

        Returns:
            str: LLM 응답
        """
        self.load_vector_stores()

        print(f"📝 Chunks 벡터스토어 검색 중... (k={k})")

        # 1. 벡터 검색
        docs_with_scores = self.chunks_vector_store.similarity_search_with_score(
            query, k=k
        )

        # 2. content_structured 사용하는 경우 page_content 교체
        if use_structured:
            docs = []
            for doc, score in docs_with_scores:
                structured_content = doc.metadata.get(
                    "content_structured", doc.page_content
                )
                new_doc = Document(
                    page_content=structured_content, metadata=doc.metadata
                )
                docs.append(new_doc)
            content_type = ContentTypeEnum.CONTENT_STRUCTURED
        else:
            docs = [doc for doc, score in docs_with_scores]
            content_type = ContentTypeEnum.PAGE_CONTENT

        # 3. LLM 응답 생성
        return self.generate_llm_response(query, docs, content_type, "Chunks")

    @staticmethod
    def _format_docs(documents: list[Document]) -> str:
        """
        Document 리스트를 LLM 입력용 텍스트로 포맷팅

        Args:
            documents: LangChain Document 객체 리스트

        Returns:
            str: 포맷팅된 문서 텍스트
        """
        return "\n\n".join([doc.page_content for doc in documents])

    def generate_llm_response(
        self,
        query: str,
        documents: list[Document],
        content_type: ContentTypeEnum,
        doc_source: str,
    ) -> str:
        """
        LCEL 방식으로 LLM 응답 생성

        Args:
            query: 사용자 질의
            documents: LangChain Document 객체 리스트
            content_type: 컨텐츠 타입
            doc_source: 문서 소스 (Full 또는 Chunks)

        Returns:
            str: LLM이 생성한 파킹통장 추천 전략
        """


        # 프롬프트 템플릿 정의
        prompt_template = ChatPromptTemplate.from_template(
            """당신은 파킹통장 전문가입니다. 주어진 검색 결과를 바탕으로 사용자의 질의에 대해 적절한 파킹통장을 추천해주세요.

    **검색 방식**: {doc_source} 벡터스토어
    **컨텐츠 타입**: {content_type}
    **사용자 질의**: {query}

    **검색된 파킹통장 정보**:
    {context}

    **응답 요구사항**:
    1. 질의에 가장 적합한 파킹통장 2-3개를 추천하세요
    2. 각 상품의 주요 특징과 장점을 설명하세요  
    3. 금리 정보와 우대조건을 포함하세요
    4. 간결하고 이해하기 쉽게 작성하세요

    **추천 파킹통장**:"""
        )

        # Context 데이터 생성하여 출력
        context_data = self._format_docs(documents)
        print(f"\n📄 검색된 Context 데이터:")
        print("-" * 60)
        print(context_data)
        print("-" * 60)

        # LCEL 체인 구성
        chain = (
            {
                "context": RunnableLambda(lambda x: x["documents"]) | RunnableLambda(self._format_docs),  # documents → format_docs
                "query": lambda x: x["query"],
                "doc_source": lambda x: x["doc_source"],
                "content_type": lambda x: x["content_type"],
            }
            | prompt_template
            | self.llm
            | StrOutputParser()  # 문자열 출력으로 파싱
        )

        try:
            # 체인 실행
            response = chain.invoke(
                {
                    "documents": documents,
                    "query": query,
                    "doc_source": doc_source,
                    "content_type": content_type.value,
                }
            )
            return response # 문자열
        except Exception as e:
            return f"[{doc_source} - {content_type.value} 기반 응답 생성 중 오류 발생: {e}]"

    def run_comparison_test(self, query: str, k_full: int = 5, k_chunks: int = 10):
        """
        단일 쿼리에 대한 4가지 방식 비교 테스트
        • Full 벡터스토어 + page_content (자연어 검색 결과)
        • Full 벡터스토어 + content_structured (구조화된 검색 결과)
        • Chunks 벡터스토어 + page_content (청크별 자연어 검색 결과)
        • Chunks 벡터스토어 + content_structured (청크별 구조화된 검색 결과)

        Args:
            query: 테스트할 쿼리
            k_full: Full 검색 문서 수
            k_chunks: Chunks 검색 문서 수
        """
        print(f"\n🔍 비교 테스트: '{query}'")
        print("=" * 80)

        # 1. Full + page_content
        print("\n1️⃣ Full 벡터스토어 + page_content")
        print("-" * 40)
        full_page_answer = self.llm_with_full(query, k=k_full, use_structured=False)
        print(f'🔥Full + page_content답변: \n {full_page_answer}')

        # 2. Full + content_structured
        print("\n2️⃣ Full 벡터스토어 + content_structured")
        print("-" * 40)
        full_structured_answer = self.llm_with_full(
            query, k=k_full, use_structured=True
        )
        print(f'🔥Full + content_structured답변: \n {full_structured_answer}')

        # 3. Chunks + page_content
        print("\n3️⃣ Chunks 벡터스토어 + page_content")
        print("-" * 40)
        chunks_page_answer = self.llm_with_chunks(
            query, k=k_chunks, use_structured=False
        )
        print(f'🔥Chunks + page_content답변: \n {chunks_page_answer}')

        # 4. Chunks + content_structured
        print("\n4️⃣ Chunks 벡터스토어 + content_structured")
        print("-" * 40)
        chunks_structured_answer = self.llm_with_chunks(
            query, k=k_chunks, use_structured=True
        )
        print(f'🔥Chunks + content_structured답변: \n {chunks_structured_answer}')

    def run_all_tests(self):
        """모든 테스트 쿼리에 대해 비교 테스트 실행"""
        print("🚀 파킹통장 검색 품질 비교 테스트 시작")
        print("=" * 80)

        for i, test_case in enumerate(self.test_queries, 1):
            print(f"\n[테스트 {i}/{len(self.test_queries)}] {test_case['description']}")
            self.run_comparison_test(test_case["query"])

            if i < len(self.test_queries):
                print("\n" + "=" * 80)


if __name__ == "__main__":
    # 사용 예시
    retriever = ParkingRetriever()

    # 전체 테스트 실행
    retriever.run_all_tests()

    # 특정 쿼리만 테스트하려면:
    # retriever.run_comparison_test("7% 고금리 파킹통장 찾고 있어요")

    # 개별 함수 사용하려면:
    # full_answer = retriever.llm_with_full("고금리 파킹통장", k=3, use_structured=True)
    # chunks_answer = retriever.llm_with_chunks("고금리 파킹통장", k=8, use_structured=False)
