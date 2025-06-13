import re
from bs4 import BeautifulSoup

from common.data import PRODUCT_GUIDE_FIELD, INTEREST_GUIDE_FIELD


def extract_product_guide(soup: BeautifulSoup) -> dict:
    """
    [상품 안내 섹션]에서 정보를 추출합니다.

    Args:
        soup: BeautifulSoup 객체

    Returns:
        Dict: 상품 안내 정보
    """
    product_guide = {key: '' for key in PRODUCT_GUIDE_FIELD}

    try:
        # 상품 안내 섹션 찾기
        product_section = soup.find("div", {"id": "PRODUCT_GUIDE"})
        if not product_section:
            print("⚠️ 상품 안내 섹션을 찾을 수 없습니다")
            return product_guide

        # 각 항목별 추출
        items = product_section.find_all(class_=lambda c: c and c.startswith("TextList_item"))
        for item in items:
            try:
                label_elem = item.find(lambda tag: tag.name in ["dt", "span"] and tag.get("class") and any("TextList_label" in cls for cls in tag.get("class")))
                desc_elem = item.find(lambda tag: tag.name in ["dd", "div", "span"] and tag.get("class") and any("TextList_description" in cls for cls in tag.get("class")))

                if not label_elem or not desc_elem:
                    continue

                label = extract_clean_text(label_elem)
                content = extract_clean_text(desc_elem)

                # 라벨에 따라 매핑
                if "금액" in label:
                    product_guide["amount_limit"] = content
                elif "가입방법" in label:
                    product_guide["signup_method"] = content
                elif "대상" in label:
                    product_guide["target_customer"] = content
                elif "우대조건" in label:
                    product_guide["basic_conditions"] = content

            except Exception as e:
                print(f"⚠️ 상품 안내 항목 처리 실패: {e}")
                continue

    except Exception as e:
        print(f"❌ 상품 안내 섹션 처리 실패: {e}")

    print(f"product_guide: {product_guide}")
    return product_guide


def extract_interest_guide(soup: BeautifulSoup) -> dict:
    """
    금리 안내 섹션에서 정보를 추출합니다.

    Args:
        soup: BeautifulSoup 객체

    Returns:
        Dict: 금리 안내 정보
    """
    interest_guide = {key: '' for key in INTEREST_GUIDE_FIELD}

    try:
        # 금리 안내 섹션 찾기
        interest_section = soup.find("div", {"id": "INTEREST_RATE_GUIDE"})
        print(f"🔥금리 안내 섹션: {interest_section}")
        if not interest_section:
            print("⚠️ 금리 안내 섹션을 찾을 수 없습니다")
            return interest_guide

        # 기본금리 추출 (테이블 또는 텍스트)
        interest_guide["basic_rate_info"] = extract_basic_rate(interest_section)

        # 조건별 정보 추출 (텍스트 전체)
        interest_guide["preferential_details"] = extract_preferential_details(interest_section)

        # 금리 유형 추출
        items = interest_section.find_all(class_=lambda c: c and c.startswith("TextList_item"))
        for item in items:
            label_elem = item.find(lambda tag: tag.name in ["dt", "span"] and tag.get("class") and any("TextList_label" in cls for cls in tag.get("class")))
            if label_elem and "유형" in extract_clean_text(label_elem):
                desc_elem = item.find(lambda tag: tag.name in ["dd", "div", "span"] and tag.get("class") and any("TextList_description" in cls for cls in tag.get("class")))
                if desc_elem:
                    interest_guide["rate_type"] = extract_clean_text(desc_elem)
                    break

    except Exception as e:
        print(f"❌ 금리 안내 섹션 처리 실패: {e}")

    return interest_guide


def extract_basic_rate(section) -> str:
    """
    기본금리 정보를 추출합니다 (테이블 또는 텍스트 형태).

    Args:
        section: 금리 안내 섹션 BeautifulSoup 객체

    Returns:
        str: 기본금리 정보 텍스트
    """
    try:
        # 1. 테이블 형태 시도
        table = section.find("table", class_=lambda c: c and c.startswith("InterestRateTable_table"))
        if table:
            table_text = extract_clean_text(table)
            if table_text.strip():
                return f"기본금리 (테이블): {table_text}"

        # 2. 텍스트 형태 시도
        basic_rate_items = section.find_all(class_=lambda c: c and c.startswith("TextList_item"))
        for item in basic_rate_items:
            label_elem = item.find(lambda tag: tag.name in ["dt", "span"] and tag.get("class") and any("TextList_label" in cls for cls in tag.get("class")))
            if label_elem and "기본금리" in extract_clean_text(label_elem):
                desc_elem = item.find(lambda tag: tag.name in ["dd", "div", "span"] and tag.get("class") and any("TextList_description" in cls for cls in tag.get("class")))
                if desc_elem:
                    return extract_clean_text(desc_elem)

        return "기본금리 정보 없음"

    except Exception as e:
        print(f"⚠️ 기본금리 추출 실패: {e}")
        return "기본금리 추출 실패"


def extract_preferential_details(section) -> str:
    """
    조건별 우대금리 정보를 모두 추출합니다.

    Args:
        section: 금리 안내 섹션 BeautifulSoup 객체

    Returns:
        str: 조건별 우대금리 전체 텍스트
    """
    try:
        all_texts = []
        items = section.find_all(class_=lambda c: c and c.startswith("TextList_item"))
        is_preferential_section = False

        for item in items:
            label_elem = item.find(lambda tag: tag.name in ["dt", "span"] and tag.get("class") and any("TextList_label" in cls for cls in tag.get("class")))
            desc_elem = item.find(lambda tag: tag.name in ["dd", "div", "span"] and tag.get("class") and any("TextList_description" in cls for cls in tag.get("class")))

            if label_elem:
                label_text = extract_clean_text(label_elem)
                if "조건별" in label_text:
                    is_preferential_section = True
                elif label_text.strip() and "조건별" not in label_text and is_preferential_section:
                    if "유형" in label_text:
                        break

            if is_preferential_section and desc_elem:
                content = extract_clean_text(desc_elem)
                if content.strip():
                    all_texts.append(content)

        return " | ".join(all_texts) if all_texts else "우대조건 정보 없음"

    except Exception as e:
        print(f"⚠️ 우대조건 추출 실패: {e}")
        return "우대조건 추출 실패"


def extract_clean_text(element) -> str:
    """
    HTML 요소에서 태그를 제거하고 깨끗한 텍스트만 추출합니다.

    Args:
        element: BeautifulSoup 요소

    Returns:
        str: 정제된 텍스트
    """
    if not element:
        return ""
    text = element.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()
