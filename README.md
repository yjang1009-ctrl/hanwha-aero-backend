# 한화에어로 워치 — 백엔드

한국투자증권(KIS) Open API를 폴링해서 대시보드용 캐시를 만들어주는 FastAPI 서버입니다.
프론트엔드(hanwha-aero-dashboard.html)가 이 서버의 `/api/*` 엔드포인트를 15~30초 주기로
호출해서 화면을 자동 갱신합니다.

## 0. 준비물
- 한국투자증권 Open API 승인 (신청 이미 하셨다고 하셨죠 — 승인되면 앱포털에서 APP KEY / APP SECRET 발급)
  https://apiportal.koreainvestment.com/
- (선택) 네이버 오픈API 뉴스 검색 client id/secret — 뉴스 섹션용
  https://developers.naver.com/apps/#/register

## 1. 로컬 테스트
```bash
cd hanwha-backend
python -m venv venv && source venv/bin/activate   #윈도우는 venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # 값 채우기
export $(cat .env | xargs)   # 윈도우는 .env를 직접 환경변수로 등록하거나 python-dotenv 사용
uvicorn main:app --reload --port 8000
```
브라우저에서 http://localhost:8000/api/price 접속해서 JSON이 나오면 성공입니다.
처음엔 백그라운드 갱신 주기(20초~5분)를 기다려야 데이터가 채워집니다.

⚠️ 배포 전에 꼭 하세요: KIS 공식 예제 저장소
(https://github.com/koreainvestment/open-trading-api → examples_llm/domestic_stock)
에서 `inquire_price`, `inquire_daily_itemchartprice`, `inquire_investor`의 tr_id와
응답 필드명이 kis_client.py와 일치하는지 실제 API 응답으로 한 번 확인해 주세요.
증권사 API는 필드명이 종종 바뀌거나 계정 등급에 따라 값이 다르게 옵니다.

## 2. Render 무료 배포
1. 이 폴더를 GitHub 저장소로 올리기 (public/private 상관없음)
2. https://render.com 가입 → New → Blueprint → 방금 만든 저장소 선택
   (render.yaml을 자동으로 읽습니다)
3. KIS_APP_KEY / KIS_APP_SECRET / NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 값을
   Render 대시보드 Environment 탭에서 입력 (render.yaml엔 sync: false로 비워둠 → 비밀값 노출 방지)
4. 배포 완료되면 `https://hanwha-aero-backend.onrender.com` 같은 URL이 생김
5. 무료 플랜은 15분 이상 요청이 없으면 슬립 — 처음 접속 시 살짝 느릴 수 있음
   (완전히 끊기지 않게 하려면 유료 플랜 또는 UptimeRobot 같은 외부 핑 서비스 활용)

## 3. 프론트엔드 연결
`hanwha-aero-dashboard.html` 상단의
```js
const API_BASE = "https://hanwha-aero-backend.onrender.com";
```
를 실제 배포 주소로 바꾸면 끝입니다. 이후 대시보드를 열어두면 가격은 20초,
수급/차트는 5분, 뉴스는 10분 주기로 자동 갱신됩니다.

## 참고: 창구별(JP모간·골드만 등) 데이터
KIS 개인 개발자 API 표준 상품에는 "외국계 창구별 매매 상위" 데이터가 포함돼 있지
않습니다(HTS 유료 화면 기준). 이 레벨의 데이터를 자동화하려면 별도 정보업체
(에프앤가이드, 인포스탁 등) 유료 연동이 필요합니다. 지금 구조에서는 개인/외국인/기관
3분류 수급까지만 자동화되고, 창구별 상세는 필요하실 때 저에게 요청하시면 그때그때
검색해서 채워드리는 방식이 현실적입니다.
