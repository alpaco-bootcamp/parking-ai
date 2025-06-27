import pymongo
from pydantic import BaseModel, Field

class ChunkData(BaseModel):
    """개별 청크 데이터"""
    chunk_type: str = Field(description="청크 타입 (basic_rate_info, preferential_details)")
    chunk_index: int = Field(description="청크 타입 (basic_rate_info, preferential_details)")
    content_natural: str = Field(description="자연어 청크 내용")


class RateConditionChunk(BaseModel):
    """우대조건 및 금리정보 청크 데이터"""
    product_code: str = Field(description="상품 코드")
    product_name: str = Field(description="상품명")
    chunks: list[ChunkData] = Field(description="우대조건 및 금리정보 청크 목록")


class ConditionExtractorResult(BaseModel):
    """ConditionExtractorTool 결과"""
    rate_condition_chunks: list[RateConditionChunk] = Field(description="우대조건 및 금리정보 청크 데이터 목록")
    total_products: int = Field(description="조회된 상품 수")
    total_chunks: int = Field(description="추출된 총 청크 수")
    success: bool = Field(description="추출 성공 여부")