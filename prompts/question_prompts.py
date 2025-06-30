"""
QuestionAgent용 프롬프트 템플릿 모음
LLM 기반 패턴 분석, 질문 생성, 응답 검증 등을 위한 구조화된 프롬프트 제공
"""

from pydantic import BaseModel, Field


class DataSection(BaseModel):
    """프롬프트 데이터 섹션 스키마"""

    title: str = Field(
        description="섹션 제목 (예: '금리정보 데이터', '우대조건 데이터')"
    )
    content: str = Field(
        description="섹션 내용 (예: '[토스뱅크] 기본금리 2.5%\\n[카카오뱅크] 우대금리 3.0%')"
    )


class QuestionPrompts:
    """QuestionAgent의 모든 프롬프트를 관리하는 클래스"""

    def pattern_analysis(
        self,
        rate_info_texts: list[str],
        preferential_texts: list[str],
        bank_names: list[str],
    ) -> str:
        """
        금리정보와 우대조건을 구분하여 패턴 분석 프롬프트 생성

        Args:
            rate_info_texts: 금리정보 텍스트 목록
            preferential_texts: 우대조건 텍스트 목록
            bank_names: 은행명 목록

        Returns:
            str: 구조화된 분석 프롬프트
        """

        # 금리정보 섹션 구성
        rate_info_section = self._format_data_section(
            title="금리정보 데이터",
            texts=rate_info_texts,
            empty_message="금리정보 데이터 없음",
        )

        # 우대조건 섹션 구성
        preferential_section = self._format_data_section(
            title="우대조건 데이터",
            texts=preferential_texts,
            empty_message="우대조건 데이터 없음",
        )

        # 은행명 목록
        bank_list = ", ".join(bank_names) if bank_names else "분석 대상 은행 없음"

        prompt = f"""
다음 파킹통장 데이터를 분석하여 금리정보와 우대조건의 공통 패턴을 추출해주세요.

=== {rate_info_section['title']} ===
{rate_info_section['content']}

=== {preferential_section['title']} ===  
{preferential_section['content']}

=== 분석 대상 은행 ===
{bank_list}

=== 분석 요구사항 ===
1. 금리정보와 우대조건을 구분하여 패턴 식별
2. 각 패턴의 표준 키워드 정의 (사용자 질문 생성에 활용)
3. 패턴별 빈도수 계산 (같은 패턴이 몇 개 상품에서 나타나는지)
4. 해당 패턴을 사용하는 은행 목록 정리
5. RAG 검색에 활용할 구체적인 쿼리 생성

=== 패턴 분류 기준 ===
**금리정보 패턴 (pattern_type: "rate_info")**:
- 기본금리, 우대금리, 특별금리, 만기별 금리 등
- 예시: "금리_기본금리", "금리_우대금리", "금리_특별혜택"

**우대조건 패턴 (pattern_type: "preferential_condition")**:
- 마케팅 동의, 앱 사용, 카드 실적, 자동이체, 급여이체, 신규가입 등
- 예시: "우대_마케팅동의", "우대_앱사용", "우대_카드실적"

=== 출력 형식 (JSON) ===
{{{{
  "patterns": [
    {{{{
      "pattern_name": "금리_기본금리",
      "pattern_type": "rate_info",
      "frequency": 8,
      "affected_banks": ["토스뱅크", "카카오뱅크", "하나은행"],
      "standard_keyword": "기본 금리 정보"
    }}}},
    {{{{
      "pattern_name": "우대_마케팅동의", 
      "pattern_type": "preferential_condition",
      "frequency": 12,
      "affected_banks": ["토스뱅크", "하나은행", "케이뱅크"],
      "standard_keyword": "마케팅 정보 수신 동의"
    }}}}
  ],
  "rag_queries": [
    "금리정보 기본금리 우대금리",
    "우대조건 마케팅 수신 동의",
    "우대조건 모바일 앱 사용 실적",
    "우대조건 카드 이용 실적",
    "파킹통장 자동이체 우대조건"
  ]
}}}}

=== 중요 지침 ===
- 패턴명은 "금리_" 또는 "우대_" 접두사로 명확히 구분
- standard_keyword는 사용자 질문 생성 시 활용되므로 명확하고 직관적으로 작성
- rag_queries는 실제 검색에 사용할 구체적인 키워드 조합으로 생성
- 빈도수는 실제 데이터에서 해당 패턴이 나타나는 횟수를 정확히 계산
- JSON 형식으로만 응답하고 추가 설명은 포함하지 마세요
"""

        return prompt

    @staticmethod
    def _format_data_section(
        title: str, texts: list[str], empty_message: str
    ) -> dict[str, str]:
        """
        데이터 섹션을 포맷팅하여 프롬프트에 삽입 가능한 형태로 변환

        Args:
            title: 섹션 제목
            texts: 표시할 텍스트 목록
            empty_message: 데이터가 없을 때 표시할 메시지

        Returns:
            dict: 제목과 내용이 포함된 딕셔너리
        """
        if not texts:
            content = empty_message
        else:
            # 텍스트가 너무 많은 경우 처음 20개만 표시하고 나머지는 생략 표시
            display_texts = texts[:20]
            content = "\n".join(display_texts)

            if len(texts) > 20:
                content += f"\n... (총 {len(texts)}개 중 20개만 표시)"

        return {"title": title, "content": content}

    @staticmethod
    def question_generation_with_rag(
            preferential_patterns: list,
            rag_context: str,
            affected_banks: list[str] = None
    ) -> str:
        """
        우대조건 패턴과 RAG 검색 결과를 기반으로 사용자 질문 생성 프롬프트

        Args:
            preferential_patterns: 우대조건 패턴 목록 (AnalysisPattern 객체들)
            rag_context: RAG 검색으로 수집된 실제 우대조건 사례 텍스트
            affected_banks: 패턴에 상응하는 은행 리스트

        Returns:
            str: 구조화된 질문 생성 프롬프트
        """

        bank_info, bank_context = '', ''

        # 은행 목록 처리
        if affected_banks:
            bank_info = f"적격 은행: {', '.join(affected_banks)}"
            bank_context = f"사용자는 다음 은행들 중에서 통장을 선택할 예정입니다: {', '.join(affected_banks)}"
        else:
            bank_info = "적격 은행: 정보 없음"
            bank_context = "은행 정보가 없습니다."

        # 패턴 요약 생성
        if preferential_patterns:
            pattern_summary = "\n".join(
                [
                    f"- {pattern.pattern_name}: {pattern.standard_keyword} (빈도: {pattern.frequency}, 은행: {', '.join(pattern.affected_banks[:3])})"
                    for pattern in preferential_patterns
                ]
            )
        else:
            pattern_summary = "분석된 우대조건 패턴이 없습니다."

        prompt = f"""
    당신은 파킹통장 우대조건을 분석하여 사용자에게 물어볼 질문을 생성하는 전문가입니다.

=== 적격 은행 정보 ===
{bank_info}

{bank_context}

=== 분석된 우대조건 패턴 ===
{pattern_summary}

=== 실제 우대조건 사례 (RAG 검색 결과) ===
{rag_context}

=== 질문 생성 요구사항 ===
1. 위 패턴과 실제 사례를 종합하여 사용자가 답변하기 쉬운 Yes/No 질문 생성
2. 질문은 일반인이 이해하기 쉬운 용어로 작성
3. 각 질문의 영향도(impact)는 해당 조건의 중요성과 통장 선택에 미치는 영향을 설명
4. 질문 개수는 3-5개로 제한
5. 빈도수가 높은 패턴 우선으로 질문 생성

=== 질문 생성 가이드라인 (우대조건 성격별) ===

**기존 실적/상태 확인형** (현재 진행형 - 이미 하고 있는 것):
- **카드 사용**: "하나은행, 신한은행 등의 체크카드나 신용카드로 월 30만원 이상 사용하고 계신가요?"
- **급여이체**: "급여를 토스뱅크, 카카오뱅크 등으로 받고 계신가요?"
- **자동이체**: "공과금이나 통신비 등을 하나은행, 신한은행 등에서 자동이체하고 계신가요?"

**향후 가능성 확인형** (가능형 - 새롭게 할 수 있는 것):
- **마케팅 동의**: "마케팅 정보 수신(SMS, 앱 푸시, 이메일 등)에 동의하실 수 있나요?"
- **앱 사용**: "토스뱅크, 카카오뱅크 등의 모바일 앱을 월 1회 이상 사용하실 수 있나요?"
- **비대면가입**: "토스뱅크, 카카오뱅크 등에서 인터넷이나 모바일로 통장을 개설하실 수 있나요?"

=== 중요 지침 ===
- 실제 RAG 검색 결과를 참고하여 현실적이고 구체적인 질문 생성
- **우대조건의 성격을 분석하여 적절한 질문 형태 선택**:
  * **실적 기반 조건**: "~하고 계신가요?" (현재 상태 확인)
  * **동의/가능 조건**: "~하실 수 있나요?" (향후 가능성 확인)
- impact 설명은 해당 조건이 통장 선택에 미치는 실질적 영향을 명시
- category는 반드시 "우대_" 접두사를 포함한 패턴명 사용
- **질문에서 반드시 구체적인 은행명을 포함하여 작성** (예: "토스뱅크, 카카오뱅크에서", "하나은행의")
- **"위 은행들" 같은 모호한 표현 대신 실제 은행명 2-3개를 명시**
- 각 패턴의 [적격 은행 정보]에서 대표적인 은행 2-3개를 선택하여 질문에 포함
- related_banks는 해당 패턴의 [적격 은행 정보] 정보를 활용
- generation_success는 항상 true로 설정

=== 질문 작성 예시 ===
**실적 확인형 (좋은 예)**: "토스뱅크나 카카오뱅크를 이미 사용하고 계신가요?"
**실적 확인형 (나쁜 예)**: "위 은행들의 카드로 월 30만원 이상 사용하실 수 있나요?"

**가능성 확인형 (좋은 예)**: "하나은행이나 신한은행의 모바일 앱을 월 1회 이상 사용하실 수 있나요?"
**가능성 확인형 (나쁜 예)**: "위 은행들의 앱을 사용하고 계신가요?"
"""
        return prompt
