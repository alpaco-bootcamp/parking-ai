"""
StrategyPrompts - 전략 생성 관련 프롬프트 템플릿 모음
InterestCalculatorTool 및 StrategyScenarioTool용 프롬프트 제공
"""

from schemas.strategy_tool_schema import ProductDetailInfo, ProductInterestCalculation
from schemas.eligibility_conditions import EligibilityConditions
from schemas.agent_responses import UserResponse


class StrategyPrompts:
    """전략 생성 관련 프롬프트 템플릿 클래스"""

    @staticmethod
    def create_interest_calculation_prompt(
            product_details: list[ProductDetailInfo],
            user_conditions: EligibilityConditions,
            user_responses: list[UserResponse]
    ) -> str:
        """
        이자 계산용 프롬프트 생성 (복리 계산 포함)

        Args:
            product_details: 상품별 상세 정보
            user_conditions: 사용자 조건
            user_responses: 사용자 질문-답변 목록

        Returns:
            str: 이자 계산용 프롬프트
        """
        # 사용자 조건 추출
        budget = user_conditions.budget
        deposit_period = user_conditions.deposit_period

        # 상품별 정보 포맷팅
        products_info = ""
        for product in product_details:
            products_info += f"""
상품명: {product.product_name}
상품코드: {product.product_code}
"""
            # 청크별 정보 추가
            for chunk in product.chunks:
                chunk_title = "금리정보" if chunk.chunk_type == "basic_rate_info" else "우대조건"
                products_info += f"{chunk_title}: {chunk.content_natural}\n"

            products_info += "---\n"

        # 사용자 응답 포맷팅
        user_conditions_met = []
        for response in user_responses:
            if response.response_value:
                user_conditions_met.append(response.question)

        conditions_text = ', '.join(user_conditions_met) if user_conditions_met else "없음"

        prompt = f"""
다음 파킹통장들에 대해 사용자 조건을 바탕으로 정확한 이자를 계산해주세요.

사용자 조건:
- 예치 금액: {budget:,}원
- 예치 기간: {deposit_period}개월
- 충족 가능한 우대조건: {conditions_text}

상품 정보:
{products_info}

계산 요구사항:
1. 사용자가 이 통장에 {budget:,}원을 예치합니다.
2. 이 통장은 매월 말 이자를 지급하며, 이자는 원금에 합산되어 복리로 계산됩니다.
3. 월복리 기준이며, 월 이자율은 연이율 ÷ 12로 계산해주세요.
4. {deposit_period}개월 동안의 총 수령 이자(세후, 15.4% 공제)를 계산해주세요.
5. 각 상품별로 사용자가 충족 가능한 우대조건만 적용해주세요.
6. 구간별 차등 금리가 있는 경우 정확히 계산해주세요.

주의사항:
- 복리 계산 공식: 원금 × (1 + 월이율)^개월수 - 원금
- 세후 이자 = 세전 이자 × (1 - 0.154)
- 우대조건을 충족하지 못하는 경우 기본금리만 적용
- 금액별 차등금리는 구간별로 나누어 계산

계산 예시:
- 단순 복리: 1000만원 × (1 + 0.033/12)^12 - 1000만원 = 335,059원(세전) → 283,460원(세후)
- 구간별 차등: 50만원×7% + 950만원×2% = 복리 계산 후 세후 적용
"""
        return prompt

    @staticmethod
    def create_strategy_scenario_prompt(
            top_interest_calculations: list[ProductInterestCalculation],
            user_conditions: EligibilityConditions,
            user_responses: list[UserResponse],
            max_account_number: int = 5
    ) -> str:
        """
        전략 시나리오 생성용 프롬프트

        Args:
            top_interest_calculations: 상위 10개 이자 계산 결과
            user_conditions: 사용자 조건
            user_responses: 사용자 질문-답변 목록
            max_account_number: 시나리오별 최대 통장 개수 (기본값: 5개)

        Returns:
            str: 시나리오 생성용 프롬프트
        """
        budget = user_conditions.budget
        deposit_period = user_conditions.deposit_period

        # 상위 10개 계산 결과 포맷팅
        calculations_text = ""
        for i, calc in enumerate(top_interest_calculations, 1):
            calculations_text += f"""
    {i}. {calc.product_name}
       - 예상 이자: {calc.interest:,}원 ({deposit_period}개월)
       - 계산 상세: {calc.calculation_detail}
       - 적용 조건: {', '.join(calc.applied_conditions)}
    """

        # 사용자 응답 정리
        user_responses_text = ""
        for response in user_responses:
            status = "✅ 달성 가능" if response.response_value else "❌ 달성 불가"
            user_responses_text += f"- {response.question}: {status}\n"

        prompt = f"""
다음 이자 계산 결과를 바탕으로 사용자에게 최적의 파킹통장 전략 시나리오 3안을 제시해주세요.

📋 사용자 조건:
- 예치 금액: {budget:,}원
- 예치 기간: {deposit_period}개월

👤 사용자 우대조건 달성 현황:
{user_responses_text}

💰 상위 수익 상품 (TOP 10):
{calculations_text}

🎯 시나리오 설계 목표:
각 시나리오는 해당 카테고리 내에서 **최고 수익률**을 추구해야 합니다.

**시나리오 1: 단일형 (single)**
- 목표: 단일 통장 중에서 최고 수익률 달성
- 조건: 사용자가 달성 가능한 우대조건만 적용하여 이자 재계산
- 시나리오 이름: 단일통장 집중형

템플릿:
```
📌 [단일통장 집중 전략]

예치금액     : {{{{예치금액:,}}}}원
예치기간     : {{{{예치기간}}}}개월
전략 요약    : 가장 수익률 높은 통장에 전액 집중 투자

[선택 통장]
- 상품명      : {{{{상품명}}}}
- 적용 금리   : {{{{금리}}}}%
- 우대 조건   : {{{{우대조건들}}}}

[예상 세후 이자]
- 6개월       : 약 {{{{6개월이자:,}}}}원
- 1년         : 약 {{{{1년이자:,}}}}원
- 3년         : 약 {{{{3년이자:,}}}}원
```

**시나리오 2: 분산형 (distributed)**
- 목표: 금리 구간별 최적화를 통한 수익 극대화
- 조건: 최대 {max_account_number}개 통장 활용
- 시나리오 이름: 분산형 통장 쪼개기

템플릿:
```
📌 [분산형 통장 쪼개기 전략]

예치금액     : {{{{총예치금액:,}}}}원
예치기간     : {{{{예치기간}}}}개월
전략 요약    : 우대금리 구간에 맞춰 분산 예치하여 전체 수익 최적화

[예치 내역]
1. 상품명    : {{{{상품1}}}}
   예치금액 : {{{{금액1:,}}}}원
   금리     : {{{{금리1}}}}%
   우대조건 : {{{{우대조건1}}}}

2. 상품명    : {{{{상품2}}}}
   예치금액 : {{{{금액2:,}}}}원
   금리     : {{{{금리2}}}}%
   우대조건 : {{{{우대조건2}}}}

[총 예상 세후 이자]
- 6개월       : 약 {{{{6개월총이자:,}}}}원
- 1년         : 약 {{{{1년총이자:,}}}}원
- 3년         : 약 {{{{3년총이자:,}}}}원
```

**시나리오 3: 고수익형 (high_yield)**
- 목표: 갈아타기 포함 전체 수익률 극대화
- 시나리오 이름: 수익률 최우선 전략

템플릿:
```
📌 [수익률 최우선 전략 - 갈아타기 포함]

총 예치금액 : {{{{총예치금액:,}}}}원
총 예치기간 : {{{{총예치기간}}}}개월
전략 요약   : 기간에 따라 갈아타기 전략을 통해 최대 수익 확보

[Step 1 - 초기 예치]
- 상품명    : {{{{특판상품명}}}}
  예치금액 : {{{{금액1:,}}}}원
  금리     : {{{{금리1}}}}%
  조건     : {{{{조건1}}}}

[Step 2 - 이후 갈아타기]
- 갈아타기 : {{{{상품명2}}}} ({{{{금리2}}}}%)
---
[예상 세후 이자]
- 6개월       : 약 {{{{6개월총이자:,}}}}원
- 1년         : 약 {{{{1년총이자:,}}}}원
- 1년 6개월   : 약 {{{{18개월이자:,}}}}원
```

⚙️ 모든 시나리오에 포함될 출력 필드:
- scenario_type: "single", "distributed", "high_yield"
- scenario_name: 고정 문자열
- scenario_content: 위 템플릿을 채워서 반환
- scenario_summary: 시나리오 핵심 요약 (1~2줄)
- products: 상품별 배분 정보
- total_allocated_amount, total_expected_interest_6m/1y/3y
- advantages, disadvantages, recommended_for
- condition_achievement_rate: (0.0 ~ 1.0)

💡 중요 지침:
1. 반드시 상위 수익 상품(TOP 10) 목록 기반 시나리오 생성
2. 세후 이자는 15.4% 공제 후 계산
3. 각 통장의 예치 한도, 조건 고려
4. 사용자 미달성 우대조건 제외
5. calculation_detail의 계산 로직 활용
6. 정확히 3개의 시나리오 생성
"""
        return prompt