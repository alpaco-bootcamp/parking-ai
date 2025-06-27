import pymongo
from pydantic import BaseModel, Field

"""
Tool 1: ConditionExtractorTool 스키마
역할: 우대조건 및 금리정보 청크 데이터 추출
"""

class ChunkData(BaseModel):
    """개별 청크 데이터"""
    chunk_type: str = Field(description="청크 타입 (basic_rate_info, preferential_details)")
    chunk_index: int = Field(description="청크 인덱스 (2, 3)")
    content_natural: str = Field(description="자연어 청크 내용")


class ExtractedProduct(BaseModel):
    """우대조건 및 금리정보 데이터"""
    product_code: str = Field(description="상품 코드")
    product_name: str = Field(description="상품명")
    chunks: list[ChunkData] = Field(description="우대조건 및 금리정보 청크 목록")

class ConditionExtractorResult(BaseModel):
    """ConditionExtractorTool 결과"""
    products: list[ExtractedProduct] = Field(description="우대조건 및 금리정보 청크 데이터 목록")
    total_products: int = Field(description="조회된 상품 수")
    total_chunks: int = Field(description="추출된 총 청크 수")
    success: bool = Field(description="추출 성공 여부")


"""
Tool 2: PatternAnalyzerTool 스키
역할: LLM 기반 우대조건 패턴 분석 및 RAG 쿼리 생성
"""


class AnalysisPattern(BaseModel):
    """분석된 패턴 (금리정보 + 우대조건 통합)"""
    pattern_name: str = Field(description="패턴 이름 (예: 금리_기본금리, 우대_마케팅동의)")
    pattern_type: str = Field(description="패턴 타입 (rate_info 또는 preferential_condition)")
    frequency: int = Field(description="해당 패턴 빈도수")
    affected_banks: list[str] = Field(description="해당 패턴을 사용하는 은행 목록")
    standard_keyword: str = Field(description="표준화된 키워드")


class PatternAnalysisOutput(BaseModel):
    """LLM 출력 파싱용 스키마"""
    patterns: list[AnalysisPattern] = Field(description="분석된 패턴 목록")
    rag_queries: list[str] = Field(description="RAG 검색용 쿼리 목록")


class PatternAnalyzerResult(BaseModel):
    """PatternAnalyzerTool 결과"""
    analysis_patterns: list[AnalysisPattern] = Field(description="분석된 패턴 목록 (금리정보 + 우대조건)")
    rag_queries: list[str] = Field(description="RAG 검색용 쿼리 목록")
    total_patterns: int = Field(description="총 패턴 수")
    analysis_success: bool = Field(description="분석 성공 여부")