from enum import Enum


class DocumentTypeEnum(str, Enum):
    """벡터화할 문서 타입을 구분하는 Enum"""

    FULL = "full"
    CHUNKS = "chunks"


class EmbeddingModelEnum(str, Enum):
    """임베딩 모델 타입을 구분하는 Enum"""

    TEXT_EMBEDDING_SMALL = "text-embedding-3-small"
    TEXT_EMBEDDING_LARGE = "text-embedding-3-large"
