"""
한화에어로 워치 백엔드.

실행(로컬):
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

배포(Render 등): README.md 참고.

설계: 진짜 실시간 웹소켓 대신 '캐시 + 짧은 주기 폴링' 방식을 씁니다.
  - 프론트엔드가 15~30초마다 /api/price, 5분마다 /api/flow, /api/news 를 호출
  - 서버는 백그라운드 태스크로 캐시를 미리 갱신해두고, 프론트는 그 캐시만 읽음
  - 이렇게 하면 KIS API 호출 한도(초당 요청 수 제한)를 안전하게 지키면서도
    체감상 '실시간 자동 업데이트'가 됩니다.
"""
import asyncio
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kis_client import KISClient
from news_client import fetch_news
from signals import build_signals

STOCK_CODE = os.environ.get("STOCK_CODE", "012450")  # 한화에어로스페이스

cache = {
    "price": None,
    "chart": {"D": [], "W": [], "M": [], "Y": []},
    "investor_trend": [],
    "signals": [],
    "news": [],
    "updated_at": {},
}


async def refresh_price(kis: KISClient):
    while True:
        try:
            cache["price"] = await kis.get_current_price(STOCK_CODE)
            cache["updated_at"]["price"] = time.time()
        except Exception as e:
            print("price refresh error:", e)
        await asyncio.sleep(20)  # 20초 간격 폴링


async def refresh_chart_and_flow(kis: KISClient):
    while True:
        try:
            for p in ["D", "W", "M", "Y"]:
                cache["chart"][p] = await kis.get_period_chart(STOCK_CODE, period=p)
                await asyncio.sleep(1)  # 호출 간 살짝 텀 주기(요청 한도 보호)
            trend = await kis.get_investor_trend(STOCK_CODE)
            cache["investor_trend"] = trend
            cache["signals"] = build_signals(trend)
            cache["updated_at"]["chart_flow"] = time.time()
        except Exception as e:
            print("chart/flow refresh error:", e)
        await asyncio.sleep(300)  # 5분 간격


async def refresh_news():
    while True:
        try:
            cache["news"] = await fetch_news()
            cache["updated_at"]["news"] = time.time()
        except Exception as e:
            print("news refresh error:", e)
        await asyncio.sleep(600)  # 10분 간격


@asynccontextmanager
async def lifespan(app: FastAPI):
    kis = KISClient()
    tasks = [
        asyncio.create_task(refresh_price(kis)),
        asyncio.create_task(refresh_chart_and_flow(kis)),
        asyncio.create_task(refresh_news()),
    ]
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(title="한화에어로 워치 백엔드", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시 대시보드가 열리는 도메인으로 좁히세요
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/price")
def get_price():
    return {"data": cache["price"], "updated_at": cache["updated_at"].get("price")}


@app.get("/api/chart/{period}")
def get_chart(period: str):
    period = period.upper()
    if period not in cache["chart"]:
        return {"error": "period must be one of D/W/M/Y"}
    return {"data": cache["chart"][period], "updated_at": cache["updated_at"].get("chart_flow")}


@app.get("/api/flow")
def get_flow():
    return {
        "investor_trend": cache["investor_trend"][-20:],
        "signals": cache["signals"],
        "updated_at": cache["updated_at"].get("chart_flow"),
    }


@app.get("/api/news")
def get_news():
    return {"data": cache["news"], "updated_at": cache["updated_at"].get("news")}


@app.get("/api/health")
def health():
    return {"ok": True}
