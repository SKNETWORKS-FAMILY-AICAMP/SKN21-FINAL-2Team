"""
날씨 조회 유틸리티 (Open-Meteo API)
- 무료, API key 불필요
- 날짜 미지정: 현재 날씨 + 3일 예보 반환
- 날짜 지정:   예보 범위(16일) 이내면 실제 예보, 초과하면 서울 월별 평균 반환
- intent_node에서 병렬 호출되어 planner/executor에서 참고
"""
import re
from datetime import date, timedelta

import httpx

from app.utils.common import dprint

# 서울 중심 좌표 (GPS 없을 때 기본값)
_SEOUL_LAT = 37.5665
_SEOUL_LON = 126.9780

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo 무료 예보 최대 일수
_FORECAST_MAX_DAYS = 16

# WMO 날씨 코드 → 한국어 설명
_WMO_CODE: dict[int, str] = {
    0:  "맑음",
    1:  "대체로 맑음",
    2:  "구름 조금",
    3:  "흐림",
    45: "안개",
    48: "짙은 안개",
    51: "가벼운 이슬비",
    53: "이슬비",
    55: "강한 이슬비",
    61: "가벼운 비",
    63: "비",
    65: "강한 비",
    71: "가벼운 눈",
    73: "눈",
    75: "강한 눈",
    77: "싸락눈",
    80: "소나기",
    81: "강한 소나기",
    82: "폭우",
    85: "눈 소나기",
    86: "강한 눈 소나기",
    95: "뇌우",
    96: "우박 동반 뇌우",
    99: "강한 우박 동반 뇌우",
}

# 서울 월별 평균 기후 (기온 min/max °C, 강수 특징)
_SEOUL_MONTHLY_CLIMATE: dict[int, dict] = {
    1:  {"lo": -6,  "hi": 2,   "desc": "매우 추운 겨울, 눈 가능성 있음",         "precip": "낮음"},
    2:  {"lo": -4,  "hi": 5,   "desc": "추운 겨울, 간헐적 눈·비",               "precip": "낮음"},
    3:  {"lo": 2,   "hi": 12,  "desc": "봄 시작, 일교차 크고 황사 가능",         "precip": "보통"},
    4:  {"lo": 8,   "hi": 19,  "desc": "온화한 봄, 맑은 날 많고 꽃 개화 시기",   "precip": "보통"},
    5:  {"lo": 14,  "hi": 24,  "desc": "따뜻한 봄, 야외 활동 최적",             "precip": "보통"},
    6:  {"lo": 19,  "hi": 29,  "desc": "초여름, 덥고 장마 시작 가능",           "precip": "높음"},
    7:  {"lo": 23,  "hi": 30,  "desc": "장마철, 잦은 비·높은 습도",             "precip": "매우 높음"},
    8:  {"lo": 23,  "hi": 31,  "desc": "무더운 여름, 소나기 잦음",              "precip": "높음"},
    9:  {"lo": 17,  "hi": 26,  "desc": "초가을, 선선하고 맑은 날 많음",          "precip": "보통"},
    10: {"lo": 10,  "hi": 20,  "desc": "가을, 단풍 시기·야외 활동 좋음",         "precip": "낮음"},
    11: {"lo": 2,   "hi": 11,  "desc": "늦가을, 쌀쌀하고 일교차 큼",            "precip": "낮음"},
    12: {"lo": -4,  "hi": 4,   "desc": "초겨울, 춥고 간헐적 눈",               "precip": "낮음"},
}


def _wmo_desc(code: int | None) -> str:
    if code is None:
        return "알 수 없음"
    return _WMO_CODE.get(int(code), f"코드 {code}")


def parse_travel_date(dates_str: str | None) -> date | None:
    """
    slots.dates 문자열을 date 객체로 파싱.
    지원 형식: "오늘", "내일", "모레", "yyyy-mm-dd", "mm-dd", "mm월 dd일"
    파싱 실패 시 None 반환.
    """
    if not dates_str:
        return None

    today = date.today()
    s = dates_str.strip()

    if s in ("오늘", "today"):
        return today
    if s in ("내일", "tomorrow"):
        return today + timedelta(days=1)
    if s in ("모레",):
        return today + timedelta(days=2)
    if s in ("글피",):
        return today + timedelta(days=3)

    # yyyy-mm-dd
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # mm-dd (연도 없을 때 올해 or 내년)
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})", s)
    if m:
        try:
            d = date(today.year, int(m.group(1)), int(m.group(2)))
            if d < today:
                d = d.replace(year=today.year + 1)
            return d
        except ValueError:
            pass

    # mm월 dd일
    m = re.search(r"(\d{1,2})월\s*(\d{1,2})일", s)
    if m:
        try:
            d = date(today.year, int(m.group(1)), int(m.group(2)))
            if d < today:
                d = d.replace(year=today.year + 1)
            return d
        except ValueError:
            pass

    return None


def _seoul_climate_summary(target: date) -> str:
    """예보 범위 초과 시 서울 월별 평균 기후 반환."""
    c = _SEOUL_MONTHLY_CLIMATE.get(target.month, {})
    lo = c.get("lo", "?")
    hi = c.get("hi", "?")
    desc = c.get("desc", "")
    precip = c.get("precip", "")
    return (
        f"{target.strftime('%Y-%m-%d')} 서울 평균 날씨 (예보 범위 초과 — 월별 기후 기준): "
        f"{desc}, 기온 {lo}~{hi}°C, 강수 가능성 {precip}"
    )


async def _call_open_meteo(lat: float, lon: float, params: dict) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(_OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        dprint(f"[Weather] API call failed: {e}")
        return None


async def fetch_weather(lat: float | None = None, lon: float | None = None) -> str | None:
    """
    날짜 미지정: 현재 날씨 + 향후 3일 예보 반환.
    """
    _lat = lat if lat is not None else _SEOUL_LAT
    _lon = lon if lon is not None else _SEOUL_LON

    data = await _call_open_meteo(_lat, _lon, {
        "latitude": _lat,
        "longitude": _lon,
        "current": "temperature_2m,apparent_temperature,precipitation_probability,weathercode",
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "Asia/Seoul",
        "forecast_days": 4,
    })
    if not data:
        return _seoul_climate_summary(date.today())

    try:
        current = data.get("current", {})
        daily = data.get("daily", {})

        temp = current.get("temperature_2m")
        feels = current.get("apparent_temperature")
        precip_prob = current.get("precipitation_probability")
        wcode = current.get("weathercode")

        current_line = (
            f"현재 날씨: {_wmo_desc(wcode)}, "
            f"기온 {temp:.0f}°C (체감 {feels:.0f}°C), "
            f"강수확률 {precip_prob}%"
        )

        dates_list: list[str] = daily.get("time", [])
        wcodes: list[int] = daily.get("weathercode", [])
        max_temps: list[float] = daily.get("temperature_2m_max", [])
        min_temps: list[float] = daily.get("temperature_2m_min", [])
        precip_probs: list[int] = daily.get("precipitation_probability_max", [])

        forecast_lines = []
        day_labels = ["내일", "모레", "글피"]
        for i, label in enumerate(day_labels):
            idx = i + 1
            if idx >= len(dates_list):
                break
            w = _wmo_desc(wcodes[idx] if idx < len(wcodes) else None)
            hi = f"{max_temps[idx]:.0f}" if idx < len(max_temps) else "?"
            lo = f"{min_temps[idx]:.0f}" if idx < len(min_temps) else "?"
            pp = f"{precip_probs[idx]}%" if idx < len(precip_probs) else "?"
            forecast_lines.append(f"{label}: {w} {hi}/{lo}°C 강수확률 {pp}")

        forecast_str = ", ".join(forecast_lines) if forecast_lines else "예보 없음"
        return f"{current_line}\n예보 ({', '.join(day_labels[:len(forecast_lines)])}): {forecast_str}"

    except Exception as e:
        dprint(f"[Weather] parse failed: {e}")
        return _seoul_climate_summary(date.today())


async def fetch_weather_for_date(
    lat: float | None = None,
    lon: float | None = None,
    dates_str: str | None = None,
) -> str | None:
    """
    특정 여행 날짜의 날씨 조회.

    - 예보 범위(16일) 이내: Open-Meteo 실제 예보 반환
    - 예보 범위 초과: 서울 월별 평균 기후 반환 (구체적 예보 불가 안내 포함)
    - 날짜 파싱 실패: None 반환 (caller가 현재 날씨 fallback 사용)
    """
    target = parse_travel_date(dates_str)
    if target is None:
        dprint(f"[Weather] date parse failed for: {dates_str!r}")
        return None

    today = date.today()
    days_ahead = (target - today).days

    # 과거 날짜는 현재 날씨로 처리
    if days_ahead < 0:
        dprint(f"[Weather] past date {target}, falling back to current weather")
        return await fetch_weather(lat, lon)

    # 예보 범위 초과 → 월별 평균 기후
    if days_ahead > _FORECAST_MAX_DAYS:
        dprint(f"[Weather] {target} is {days_ahead} days away, using climate average")
        return _seoul_climate_summary(target)

    # 예보 범위 이내 → 실제 예보
    _lat = lat if lat is not None else _SEOUL_LAT
    _lon = lon if lon is not None else _SEOUL_LON

    data = await _call_open_meteo(_lat, _lon, {
        "latitude": _lat,
        "longitude": _lon,
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "Asia/Seoul",
        "forecast_days": days_ahead + 1,
    })
    if not data:
        return _seoul_climate_summary(target)

    try:
        daily = data.get("daily", {})
        dates_list: list[str] = daily.get("time", [])
        target_str = target.isoformat()

        if target_str not in dates_list:
            dprint(f"[Weather] {target_str} not in forecast, using climate average")
            return _seoul_climate_summary(target)

        idx = dates_list.index(target_str)
        wcodes: list = daily.get("weathercode", [])
        max_temps: list = daily.get("temperature_2m_max", [])
        min_temps: list = daily.get("temperature_2m_min", [])
        precip_probs: list = daily.get("precipitation_probability_max", [])

        w = _wmo_desc(wcodes[idx] if idx < len(wcodes) else None)
        hi = f"{max_temps[idx]:.0f}" if idx < len(max_temps) else "?"
        lo = f"{min_temps[idx]:.0f}" if idx < len(min_temps) else "?"
        pp = f"{precip_probs[idx]}%" if idx < len(precip_probs) else "?"

        return (
            f"{target_str} 날씨 예보: {w}, "
            f"최고 {hi}°C / 최저 {lo}°C, 강수확률 {pp}"
        )

    except Exception as e:
        dprint(f"[Weather] date forecast parse failed: {e}")
        return _seoul_climate_summary(target)
