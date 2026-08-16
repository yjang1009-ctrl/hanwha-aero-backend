"""
투자자매매동향에서 '평소와 다른 신호'를 규칙 기반으로 뽑아냅니다.
카톡 방산포럼 자료에서 학습한 해석 패턴을 코드화한 것입니다:
  - 연속 순매수/순매도 일수
  - 최근 평균 거래량 대비 튀는 순매수량
  - 외국인/개인 수급 방향이 반대로 갈리는 구간
tr_id/필드가 실제로는 회사 기준일이 하루 밀려서 올 수 있으니, 운영 중 값이
이상해 보이면 raw response를 로그로 남겨서 필드명을 다시 확인하세요.
"""
from statistics import mean, pstdev


def _streak(values: list[int]) -> tuple[str, int]:
    """마지막 값 기준 연속 매수/매도 일수. values는 날짜 오름차순."""
    if not values:
        return ("none", 0)
    sign = 1 if values[-1] > 0 else (-1 if values[-1] < 0 else 0)
    if sign == 0:
        return ("none", 0)
    n = 0
    for v in reversed(values):
        s = 1 if v > 0 else (-1 if v < 0 else 0)
        if s == sign:
            n += 1
        else:
            break
    return ("buy" if sign == 1 else "sell", n)


def build_signals(investor_trend: list[dict]) -> list[dict]:
    if len(investor_trend) < 5:
        return []

    signals = []
    foreign = [d["foreign"] for d in investor_trend]
    individual = [d["individual"] for d in investor_trend]
    institution = [d["institution"] for d in investor_trend]

    f_type, f_streak = _streak(foreign)
    i_type, i_streak = _streak(individual)
    o_type, o_streak = _streak(institution)

    if f_streak >= 3:
        signals.append({
            "level": "notice",
            "title": f"외국인 {f_streak}거래일 연속 {'순매수' if f_type=='buy' else '순매도'}",
            "detail": "짧은 되돌림이 아니라 방향성 있는 자금 흐름일 가능성. 창구 분산 여부는 별도 확인 필요.",
        })

    # 개인 vs 외국인 역방향
    if f_type != "none" and i_type != "none" and f_type != i_type:
        signals.append({
            "level": "info",
            "title": f"개인({'매수' if i_type=='buy' else '매도'}) · 외국인({'매수' if f_type=='buy' else '매도'}) 수급 반대",
            "detail": "개인과 외국인이 반대 방향으로 움직이는 구간 — 단기 변동성에 대한 반응 차이일 수 있음.",
        })

    # 최근 순매수량이 최근 20일 평균 대비 튀는 경우
    recent_window = foreign[-20:] if len(foreign) >= 20 else foreign
    if len(recent_window) >= 5:
        avg = mean(recent_window)
        sd = pstdev(recent_window) or 1
        today = foreign[-1]
        z = (today - avg) / sd
        if abs(z) >= 1.8:
            signals.append({
                "level": "caution",
                "title": f"외국인 순매매량이 최근 평균 대비 {'급증' if z>0 else '급감'} (z={z:.1f})",
                "detail": "최근 20거래일 평균/표준편차 기준 통계적으로 튀는 수급. 재료 발생 여부와 함께 확인하세요.",
            })

    if o_streak >= 3:
        signals.append({
            "level": "notice",
            "title": f"기관 {o_streak}거래일 연속 {'순매수' if o_type=='buy' else '순매도'}",
            "detail": "연기금 등 장기 성격 자금의 방향성 판단에 참고.",
        })

    return signals
