"""
뉴스 수집기 (구글 뉴스 RSS 버전).
API 키 발급이 전혀 필요 없습니다 - 네이버 오픈API 신청 과정이 계속 바뀌어서
더 안정적인 방식으로 교체했습니다. 구글 뉴스가 한국 언론사 기사를 모아
RSS로 제공하는 공개 엔드포인트를 그대로 이용합니다.
"""
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime

RSS_URL = "https://news.google.com/rss/search"

CATEGORY_KEYWORDS = {
    "earn": ["실적", "영업이익", "매출", "어닝"],
    "export": ["수주", "수출", "계약", "MOU", "인도"],
    "macro": ["분할", "지배구조", "관세", "환율", "규제"],
}


def _categorize(title: str) -> str:
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(kw in title for kw in kws):
            return cat
    return "macro"


def _clean_title(raw: str) -> str:
    # 구글 뉴스는 title 끝에 " - 언론사명" 이 붙어 나옴
    if " - " in raw:
        return raw.rsplit(" - ", 1)[0].strip()
    return raw.strip()


def _source_from_title(raw: str) -> str:
    if " - " in raw:
        return raw.rsplit(" - ", 1)[1].strip()
    return ""


async def fetch_news(query: str = "한화에어로스페이스", limit: int = 20) -> list[dict]:
    params = {"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(RSS_URL, params=params, timeout=10)
        resp.raise_for_status()
        xml_text = resp.text

    root = ET.fromstring(xml_text)
    items = root.findall(".//item")[:limit]

    out = []
    for it in items:
        raw_title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub_date_raw = (it.findtext("pubDate") or "").strip()
        pub_date = None
        if pub_date_raw:
            try:
                dt = datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S %Z")
                pub_date = dt.isoformat()
            except ValueError:
                pub_date = pub_date_raw

        title = _clean_title(raw_title)
        out.append({
            "title": title,
            "link": link,
            "source": _source_from_title(raw_title),
            "pub_date": pub_date,
            "category": _categorize(title),
        })
    return out
