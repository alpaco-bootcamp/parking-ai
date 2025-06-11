# 🚀 parking-ai

**AI-powered parking account recommendation system that finds the perfect high-yield savings account tailored to your financial profile and goals.**

> "복잡한 통장 비교는 AI에게 맡기고, 당신은 수익만 누리세요."

---

## 🧠 About the Project

**parking-ai**는 파킹통장을 찾는 사용자의 조건(예산, 우대조건, 가입여부 등)에 따라  
최적의 전략을 자동으로 추천하는 **LangChain 기반 Multi-Agent 시스템**입니다.

### 💡 주요 기능

- ✅ 최신 파킹통장 실시간 정보 수집 (크롤링 기반)
- ✅ 조건 기반 전략 3안 제시 (단일형 / 분산형 / 수익극대화형)
- ✅ 예상 세후 이자 계산기
- ✅ 자연어 기반 우대조건 해석 및 전략 설명

---

## 📦 Tech Stack

| 기술        | 설명                                    |
|-------------|-----------------------------------------|
| Python      | 백엔드 언어                             |
| LangChain   | Agent & Tool 기반 전략 설계             |
| MongoDB     | 구조화 + 비정형 통합 데이터 저장         |
| OpenAI GPT  | 조건 분석 및 전략 설명 생성             |
| BeautifulSoup | 웹 크롤링을 통한 실시간 통장 정보 수집 |
| pipenv      | 의존성 관리 및 실행 환경 구성           |
| FastAPI (예정) | 향후 API 서버 구축 시 사용 예정        |

---

## 🔧 Installation

1. **리포지토리 클론**

```bash
git clone https://github.com/alpaco-bootcamp/parking-ai.git
cd parking-ai
```

2. **Pipenv 환경 설정**

```bash
pipenv install --dev
```

3. **가상환경 진입**

```bash
pipenv shell
```

---

## 🗂️ Project Structure
```bash
parking-ai/
│
├── agents/             # 에이전트 정의 및 Tool 연동 폴더
├── crawler/            # HTML 크롤링 및 파싱 스크립트 폴더
├── data/               # 크롤링된 JSON 데이터 샘플 저장 폴더
├── db/                 # MongoDB 연동 및 데이터 처리 유틸리티
├── prompts/            # 프롬프트 템플릿 모음
├── rag/                # RAG 기반 검색 및 LLM 연동 모듈
├── simulator/          # 전략 시뮬레이션 및 이자 계산기
```


---

## 🧪 How to Use

```bash
pipenv run python main.py
```

**실행 흐름:**
1. 예산, 쪼개기 여부, 우대조건 등을 입력
2. Agent가 조건 필터링 및 전략 수립
3. 전략 3안 출력 (세후 이자 계산 포함)

---

## 📊 Example Output

```
[전략1] 단일형: 카카오뱅크 (연 3.5%)
[전략2] 분산형: 토스 1000만원, 케이뱅크 300만원
[전략3] 고수익형: 6개월간 하나저축 7% → 이후 갈아타기

예상 세후 이자 (1년 기준): 359,100원 ~ 565,520원
```

---

## 📈 Future Plans

- [ ] Airflow 기반 주기적 크롤링 자동화
- [ ] 웹 UI 연동 (FastAPI + React)
- [ ] 갈아타기 알림 리마인더 기능
- [ ] 약관 요약 AI 기능 (복잡한 우대조건 해석 자동화)

---

## 🤝 Contributing

Pull Request와 이슈 제안 모두 환영합니다.  
본 리포지토리는 개발자와 금융 초보자를 위한 **오픈 파이낸스 에이전트**의 첫 걸음입니다.

---

## 📄 License

MIT License

---

**문의 / 협업 제안:**  
📩 chutzrit@gmail.com  
🎙️ AI & Frontend Development Instructor | 🎥 YouTube Creator | 🚀 Builder of practical, educational tech projects
