"""
KIS API에는 뉴스가 없으므로 별도로 수집합니다.
가장 간단하고 안정적인 방법: 네이버 뉴스 검색 오픈API (무료, 앱키만 있으면 됨).
  발급: https://developers.naver.com/apps/#/register  (검색 API 사용 설정)
네이버 뉴스 API가 부담스러우면 각 언론사 RSS를 직접 파싱하는 방식으로 바꿔도 됩니다
(카톡 방산포럼에서 학습한 주요 매체 목록은 README 참고).
"""
import os
import httpx

NAVER_URL = "https://openapi.naver.com/v1/search/news.json"

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


async def fetch_news(query: str = "한화에어로스페이스", display: int = 20) -> list[dict]:
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        return []

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            NAVER_URL,
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret,
            },
            params={"query": query, "display": display, "sort": "date"},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])

    out = []
    for it in items:
        title = (
            it.get("title", "")
            .replace("<b>", "")
            .replace("</b>", "")
            .replace("&quot;", '"')
            .replace("&amp;", "&")
        )
        out.append({
            "title": title,
            "link": it.get("originallink") or it.get("link"),
            "pub_date": it.get("pubDate"),
            "category": _categorize(title),
        })
    return out
