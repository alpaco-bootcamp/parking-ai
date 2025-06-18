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
    product_guide = {key: "" for key in PRODUCT_GUIDE_FIELD}

    try:
        # 상품 안내 섹션 찾기
        product_section = soup.find("div", {"id": "PRODUCT_GUIDE"})
        if not product_section:
            print("⚠️ 상품 안내 섹션을 찾을 수 없습니다")
            return product_guide

        # 각 항목별 추출
        items = product_section.find_all(
            class_=lambda c: c and c.startswith("TextList_item")
        )
        for item in items:
            try:
                label_elem = item.find(
                    lambda tag: tag.name in ["dt", "span"]
                    and tag.get("class")
                    and any("TextList_label" in cls for cls in tag.get("class"))
                )
                desc_elem = item.find(
                    lambda tag: tag.name in ["dd", "div", "span"]
                    and tag.get("class")
                    and any("TextList_description" in cls for cls in tag.get("class"))
                )

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
    interest_guide = {}

    try:
        # 금리 안내 섹션 찾기
        interest_section = soup.find("div", {"id": "INTEREST_RATE_GUIDE"})
        if not interest_section:
            print("⚠️ 금리 안내 섹션을 찾을 수 없습니다")
            return interest_guide

        # 기본금리 추출 (테이블 또는 텍스트)
        interest_guide["basic_rate_info"] = extract_basic_rate(interest_section)

        # 조건별 정보 추출 (텍스트 전체)
        interest_guide["preferential_details"] = extract_preferential_details(
            interest_section
        )

        # 금리 유형 추출
        interest_guide["rate_type"] = extract_rate_type(interest_section)

    except Exception as e:
        print(f"❌ 금리 안내 섹션 처리 실패: {e}")

    return interest_guide


def extract_basic_rate(section) -> list[dict]:
    """
    기본금리 정보를 추출합니다.

    Args:
        section: 금리 안내 섹션 BeautifulSoup 객체

    Returns:
        list:
        [
            {"condition": "5백만원 이하 분", "rate": "연 3.01%(세전)"},
            {"condition": "3억 원 이하 분", "rate": "연 2.8%(세전)"},
            ...
        ]
       or 텍스트 형태인 경우
        [
            {"text": "저축예금 : 연 0.1%(2025.5.9 기준, 세금공제 전)"}
        ]
    """
    try:
        # 1. 테이블 형태 추출
        table = section.find(
            "table", class_=lambda c: c and c.startswith("InterestRateTable_table")
        )
        if table:
            rows = table.find_all("tr")
            rate_info = []

            for row in rows:
                # 모든 셀이 <th> 태그인 경우, 즉 헤더행은 건너뜀
                if all(col.name == "th" for col in row.find_all(["td", "th"])):
                    continue

                cols = row.find_all(["td", "th"])
                if len(cols) >= 2:
                    condition = extract_clean_text(cols[0])
                    rate = extract_clean_text(cols[1])
                    if condition and rate:
                        rate_info.append({"condition": condition, "rate": rate})

            if rate_info:
                return rate_info

        # 2. 텍스트 형태 추출
        # 금리 안내 텍스트 정보가 있는 영역 추출
        text_info = section.find(
            "div",
            class_=lambda c: c and c.startswith("InterestRateGuide_area-text-info"),
        )
        if text_info:
            items = text_info.find_all(
                "div", class_=lambda c: c and c.startswith("TextList_item")
            )
            if items:
                # 첫 번째 항목이 기본금리 정보일 가능성이 높음
                desc_elem = items[0].find(
                    lambda tag: tag.name in ["dd", "div", "span"]
                    and tag.get("class")
                    and any("TextList_description" in cls for cls in tag.get("class"))
                )
                if desc_elem:
                    text = extract_clean_text(desc_elem)
                    return [{"text": text}]

        return [{"text": "기본금리 정보 없음"}]

    except Exception as e:
        print(f"⚠️ 기본금리 추출 실패: {e}")
        return [{"text": "기본금리 추출 실패"}]


def extract_preferential_details(section) -> dict:
    """
    금리 안내 섹션 중 우대금리 조건(preferential_details)을 구조화하여 추출합니다.

    Args:
        section: 금리 안내 섹션 BeautifulSoup 객체

    Returns:
        dict: {
            "intro": str,
            "conditions": [
                { "index": str, "description": str },
                ...
            ]
        } 또는 빈 dict (조건별 항목이 없을 경우)
    """
    try:
        # 텍스트 블록 전체 추출
        text_infos = section.find_all(
            "div",
            class_=lambda c: c and c.startswith("InterestRateGuide_area-text-info"),
        )
        if not text_infos:
            return {}

        items = []
        for text_info in text_infos:
            items.extend(
                text_info.find_all(
                    "div", class_=lambda c: c and c.startswith("TextList_item")
                )
            )

        found_condition_label = False
        intro = ""
        conditions = []

        for item in items:
            label_elem = item.find(
                lambda tag: tag.name in ["dt", "span"]
                and tag.get("class")
                and any("TextList_label" in cls for cls in tag.get("class"))
            )
            desc_elem = item.find(
                lambda tag: tag.name in ["dd", "div", "span"]
                and tag.get("class")
                and any("TextList_description" in cls for cls in tag.get("class"))
            )

            if not desc_elem:
                continue

            label_text = extract_clean_text(label_elem) if label_elem else ""

            # 조건별 도입부
            if "조건별" in label_text:
                intro = extract_clean_text(desc_elem)
                found_condition_label = True
                continue

            # 조건들 추출
            if found_condition_label:
                ul = desc_elem.find("ul", class_="number-list")
                if ul:
                    for li in ul.find_all("li"):
                        index_tag = li.find("b")
                        desc_tag = li.find("p")
                        if desc_tag:
                            conditions.append(
                                {
                                    "index": (
                                        index_tag.get_text(strip=True)
                                        if index_tag
                                        else ""
                                    ),
                                    "description": desc_tag.get_text(
                                        separator="\n", strip=True
                                    ),
                                }
                            )

        if found_condition_label:
            return {"intro": intro, "conditions": conditions}

        # 조건별 라벨이 없으면 빈 dict 반환
        return {}

    except Exception as e:
        print(f"⚠️ 우대조건 추출 실패: {e}")
        return {}


def extract_rate_type(section: BeautifulSoup) -> str:
    """
    금리 유형 정보를 추출합니다.

    Args:
        section: 금리 안내 섹션 BeautifulSoup 객체

    Returns:
        str: 금리 유형 (예: '변동금리', '고정금리' 등)
    """
    try:
        items = section.find_all(class_=lambda c: c and c.startswith("TextList_item"))
        for item in items:
            label_elem = item.find(
                lambda tag: tag.name in ["dt", "span"]
                and tag.get("class")
                and any("TextList_label" in cls for cls in tag.get("class"))
            )
            desc_elem = item.find(
                lambda tag: tag.name in ["dd", "div", "span"]
                and tag.get("class")
                and any("TextList_description" in cls for cls in tag.get("class"))
            )

            if label_elem and "유형" in extract_clean_text(label_elem) and desc_elem:
                return extract_clean_text(desc_elem)

        return ""

    except Exception as e:
        print(f"⚠️ 금리 유형 추출 실패: {e}")
        return ""


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
