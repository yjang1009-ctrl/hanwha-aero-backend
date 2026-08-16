"""
한국투자증권(KIS) Open API 래퍼.

공식 예제 저장소: https://github.com/koreainvestment/open-trading-api
  domestic_stock 폴더의 inquire_price / inquire_daily_itemchartprice / inquire_investor
  샘플과 tr_id를 배포 전에 반드시 한 번 대조 확인하세요. (API는 공지 없이 바뀔 수 있습니다)

이 파일은 그 3개 기능만 최소 구현합니다:
  1) get_current_price   : 실시간에 가까운 현재가/등락률
  2) get_period_chart     : 일/주/월/년 봉 시세
  3) get_investor_trend   : 최근 N영업일 투자자별(개인/외국인/기관) 순매수 동향

주의: 창구(JP모간/골드만 등) 단위 매매 데이터는 KIS 개인 개발자 API의 표준 상품에는
포함되어 있지 않습니다(HTS 화면 기준). 이 데이터를 쓰려면 별도 유료 정보업체 연동이
필요하며, 이 코드에서는 해당 부분을 비워두고 있습니다. 자세한 내용은 답변 본문 참고.
"""
import os
import time
import httpx

REAL_BASE = "https://openapi.koreainvestment.com:9443"
PAPER_BASE = "https://openapivts.koreainvestment.com:29443"


class KISClient:
    def __init__(self):
        self.app_key = os.environ["KIS_APP_KEY"]
        self.app_secret = os.environ["KIS_APP_SECRET"]
        # 모의투자로 먼저 테스트하고 싶으면 KIS_ENV=paper 로 설정
        self.base_url = PAPER_BASE if os.environ.get("KIS_ENV") == "paper" else REAL_BASE
        self._token = None
        self._token_expire_at = 0

    # ---------- 인증 ----------
    async def _get_token(self) -> str:
        if self._token and time.time() < self._token_expire_at - 60:
            return self._token
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/oauth2/tokenP",
                json={
                    "grant_type": "client_credentials",
                    "appkey": self.app_key,
                    "appsecret": self.app_secret,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            # expires_in 은 보통 초 단위(대략 24시간)
            self._token_expire_at = time.time() + int(data.get("expires_in", 86400))
            return self._token

    async def _headers(self, tr_id: str) -> dict:
        token = await self._get_token()
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    async def _get(self, path: str, tr_id: str, params: dict) -> dict:
        headers = await self._headers(tr_id)
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}{path}", headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()

    # ---------- 1) 현재가 ----------
    async def get_current_price(self, code: str) -> dict:
        data = await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            tr_id="FHKST01010100",
            params={"fid_cond_mrkt_div_code": "J", "fid_input_iscd": code},
        )
        out = data.get("output", {})
        return {
            "code": code,
            "price": int(out.get("stck_prpr", 0)),
            "change": int(out.get("prdy_vrss", 0)),
            "change_rate": float(out.get("prdy_ctrt", 0)),
            "volume": int(out.get("acml_vol", 0)),
            "market_cap_rank": out.get("stck_mxpr", None),
        }

    # ---------- 2) 기간별(일/주/월/년) 시세 ----------
    async def get_period_chart(self, code: str, period: str = "D", count_days: int = 100) -> list[dict]:
        """period: D(일) / W(주) / M(월) / Y(년)"""
        today = time.strftime("%Y%m%d")
        start = "19900101"  # 기간 코드 넣으면 종료일 기준 최근 구간을 반환하는 편이라 넉넉히 과거로 시작
        data = await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
            tr_id="FHKST03010100",
            params={
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": code,
                "fid_input_date_1": start,
                "fid_input_date_2": today,
                "fid_period_div_code": period,
                "fid_org_adj_prc": "1",
            },
        )
        rows = data.get("output2", [])
        out = [
            {
                "date": r.get("stck_bsop_date"),
                "close": int(r.get("stck_clpr", 0)),
                "open": int(r.get("stck_oprc", 0)),
                "high": int(r.get("stck_hgpr", 0)),
                "low": int(r.get("stck_lwpr", 0)),
                "volume": int(r.get("acml_vol", 0)),
            }
            for r in rows if r.get("stck_bsop_date")
        ]
        out.sort(key=lambda x: x["date"])
        return out[-count_days:]

    # ---------- 3) 투자자별 매매동향 ----------
    async def get_investor_trend(self, code: str) -> list[dict]:
        data = await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-investor",
            tr_id="FHKST01010900",
            params={"fid_cond_mrkt_div_code": "J", "fid_input_iscd": code},
        )
        rows = data.get("output", [])
        out = [
            {
                "date": r.get("stck_bsop_date"),
                "individual": int(r.get("prsn_ntby_qty", 0)),
                "foreign": int(r.get("frgn_ntby_qty", 0)),
                "institution": int(r.get("orgn_ntby_qty", 0)),
            }
            for r in rows if r.get("stck_bsop_date")
        ]
        out.sort(key=lambda x: x["date"])
        return out
