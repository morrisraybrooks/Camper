"""Fishing forecast for the Fishing page (2026-10-25).

Usage: fishing_solunar.py LAT LON TZ "PRESSURE_TREND" WIND_MPH
Prints JSON: a rating and 0-100 score for right now with the reasons, today's feeding
windows - major (moon overhead/underfoot, +-1 h) and minor (moonrise/moonset, +-30 min) -
plus sunrise/sunset, tomorrow's majors and the moon phase. Run every 5 min by the
command_line sensor sensor.fishing_forecast. Needs only the standard library plus astral
(ships with Home Assistant). Moon position: Paul Schlyter's low-precision method with the
main perturbations; checked against PyEphem to within about 4 minutes.
"""
import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LAT, LON, TZ = 35.0, -81.0, "America/New_York"   # placeholder: HA passes the real location
TREND, WIND = "unknown", 0.0
if len(sys.argv) >= 3:
    LAT, LON = float(sys.argv[1]), float(sys.argv[2])
if len(sys.argv) >= 4:
    TZ = sys.argv[3]
if len(sys.argv) >= 5:
    TREND = sys.argv[4]
if len(sys.argv) >= 6:
    try:
        WIND = float(sys.argv[5])
    except ValueError:
        WIND = 0.0
tz = ZoneInfo(TZ)
R = math.radians
D = math.degrees


def sind(x): return math.sin(R(x))
def cosd(x): return math.cos(R(x))


def moon_altitude(t):
    """Topocentric altitude (degrees) of the moon's center at UTC datetime t."""
    jd = t.timestamp() / 86400.0 + 2440587.5
    d = jd - 2451543.5
    N = 125.1228 - 0.0529538083 * d
    i = 5.1454
    w = 318.0634 + 0.1643573223 * d
    a = 60.2666
    e = 0.054900
    M = (115.3654 + 13.0649929509 * d) % 360
    E = M + D(e) * sind(M) * (1 + e * cosd(M))
    for _ in range(5):
        E = E - (E - D(e) * sind(E) - M) / (1 - e * cosd(E))
    xv, yv = a * (cosd(E) - e), a * math.sqrt(1 - e * e) * sind(E)
    v, r = D(math.atan2(yv, xv)), math.hypot(xv, yv)
    xh = r * (cosd(N) * cosd(v + w) - sind(N) * sind(v + w) * cosd(i))
    yh = r * (sind(N) * cosd(v + w) + cosd(N) * sind(v + w) * cosd(i))
    zh = r * (sind(v + w) * sind(i))
    lon, lat = D(math.atan2(yh, xh)), D(math.atan2(zh, math.hypot(xh, yh)))
    ws = 282.9404 + 4.70935e-5 * d
    Ms = (356.0470 + 0.9856002585 * d) % 360
    Ls, Lm = Ms + ws, M + w + N
    Dm, F = Lm - Ls, Lm - N
    lon += (-1.274 * sind(M - 2 * Dm) + 0.658 * sind(2 * Dm) - 0.186 * sind(Ms) - 0.059 * sind(2 * M - 2 * Dm)
            - 0.057 * sind(M - 2 * Dm + Ms) + 0.053 * sind(M + 2 * Dm) + 0.046 * sind(2 * Dm - Ms)
            + 0.041 * sind(M - Ms) - 0.035 * sind(Dm) - 0.031 * sind(M + Ms) - 0.015 * sind(2 * F - 2 * Dm)
            + 0.011 * sind(M - 4 * Dm))
    lat += (-0.173 * sind(F - 2 * Dm) - 0.055 * sind(M - F - 2 * Dm) - 0.046 * sind(M + F - 2 * Dm)
            + 0.033 * sind(F + 2 * Dm) + 0.017 * sind(2 * M + F))
    r += -0.58 * cosd(M - 2 * Dm) - 0.46 * cosd(2 * Dm)
    ecl = 23.4393 - 3.563e-7 * d
    xe = cosd(lon) * cosd(lat)
    ye = sind(lon) * cosd(lat) * cosd(ecl) - sind(lat) * sind(ecl)
    ze = sind(lon) * cosd(lat) * sind(ecl) + sind(lat) * cosd(ecl)
    ra, dec = D(math.atan2(ye, xe)), D(math.atan2(ze, math.hypot(xe, ye)))
    ut = t.hour + t.minute / 60 + t.second / 3600
    lst = (Ls + 180) / 15 + ut + LON / 15
    ha = lst * 15 - ra
    alt = D(math.asin(sind(LAT) * sind(dec) + cosd(LAT) * cosd(dec) * cosd(ha)))
    mpar = D(math.asin(1 / r))
    return alt - mpar * cosd(alt)


def moon_events(day):
    """Rise/set (alt -0.833 deg), overhead (max) and underfoot (min) on a local day."""
    start = datetime(day.year, day.month, day.day, tzinfo=tz).astimezone(timezone.utc)
    pts = [(start + timedelta(minutes=m), moon_altitude(start + timedelta(minutes=m))) for m in range(-1, 1442)]
    ev = {"moonrise": None, "moonset": None, "overhead": None, "underfoot": None}
    h0 = -0.833
    for k in range(1, len(pts) - 1):
        (t0, a0), (t1, a1), (t2, a2) = pts[k - 1], pts[k], pts[k + 1]
        if not (start <= t1 < start + timedelta(days=1)):
            continue
        if (a0 - h0) < 0 <= (a1 - h0) and ev["moonrise"] is None:
            ev["moonrise"] = t0 + (t1 - t0) * ((h0 - a0) / (a1 - a0))
        if (a0 - h0) >= 0 > (a1 - h0) and ev["moonset"] is None:
            ev["moonset"] = t0 + (t1 - t0) * ((h0 - a0) / (a1 - a0))
        if a0 < a1 >= a2 and ev["overhead"] is None:
            ev["overhead"] = t1
        if a0 > a1 <= a2 and ev["underfoot"] is None:
            ev["underfoot"] = t1
    return ev


def moon_phase(day):
    """Days into the 29.53-day cycle (0 = new, 14.8 = full), from a known new moon."""
    ref = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    noon = datetime(day.year, day.month, day.day, 12, tzinfo=tz)
    return ((noon - ref).total_seconds() / 86400) % 29.530588853


def phase_name(age):
    names = [(1.0, "New Moon"), (6.4, "Waxing Crescent"), (8.4, "First Quarter"), (13.8, "Waxing Gibbous"),
             (15.8, "Full Moon"), (21.1, "Waning Gibbous"), (23.1, "Last Quarter"), (28.5, "Waning Crescent"),
             (30.0, "New Moon")]
    return next(n for lim, n in names if age < lim)


def sun_times(day):
    from astral import LocationInfo
    from astral.sun import sun
    s = sun(LocationInfo("camp", "", TZ, LAT, LON).observer, date=day, tzinfo=tz)
    return s["sunrise"], s["sunset"]


def iso(t):
    return t.astimezone(tz).isoformat(timespec="minutes") if t else None


def day_info(day):
    ev = moon_events(day)
    sunrise, sunset = sun_times(day)
    age = moon_phase(day)
    from_new_or_full = min(age, abs(age - 14.765), 29.53 - age)
    rating = "Best" if from_new_or_full <= 1.5 else "Good" if from_new_or_full <= 3.5 else "Average"
    periods = []
    for key, kind, half in (("overhead", "Major", 60), ("underfoot", "Major", 60),
                            ("moonrise", "Minor", 30), ("moonset", "Minor", 30)):
        if ev[key]:
            periods.append({"kind": kind, "why": {"overhead": "moon overhead", "underfoot": "moon underfoot",
                                                    "moonrise": "moonrise", "moonset": "moonset"}[key],
                            "start": iso(ev[key] - timedelta(minutes=half)), "end": iso(ev[key] + timedelta(minutes=half))})
    periods.sort(key=lambda p: p["start"])
    return {"date": day.isoformat(), "sunrise": iso(sunrise), "sunset": iso(sunset),
            "moonrise": iso(ev["moonrise"]), "moonset": iso(ev["moonset"]),
            "overhead": iso(ev["overhead"]), "underfoot": iso(ev["underfoot"]),
            "periods": periods, "phase": phase_name(age), "moon_age": round(age, 1),
            "illumination": round(100 * (1 - math.cos(2 * math.pi * age / 29.530588853)) / 2),
            "day_rating": rating}


def hm(t):
    return t.astimezone(tz).strftime("%-I:%M %p") if t else ""


def forecast(now):
    today, tomorrow = day_info(now.date()), day_info(now.date() + timedelta(days=1))
    # Yesterday too: a window from a moon event late last night can run past midnight.
    yesterday = day_info(now.date() - timedelta(days=1))
    periods = [dict(p, s=datetime.fromisoformat(p["start"]), e=datetime.fromisoformat(p["end"]))
               for p in yesterday["periods"] + today["periods"] + tomorrow["periods"]]
    periods = [p for p in periods if p["e"].date() >= now.date()]
    current = [p for p in periods if p["s"] <= now <= p["e"]]
    window = next((p for p in current if p["kind"] == "Major"), current[0] if current else None)
    nxt = next((p for p in periods if p["s"] > now), None)
    soon = nxt is not None and (nxt["s"] - now) <= timedelta(hours=1)
    sunrise, sunset = datetime.fromisoformat(today["sunrise"]), datetime.fromisoformat(today["sunset"])
    near_sun = min(abs(now - sunrise), abs(now - sunset)) <= timedelta(hours=1)

    reasons, pts = [], 0
    trend_pts = {"Falling": 30, "Steady": 25, "Falling fast": 22, "Rising": 12, "Rising fast": 5}
    trend_why = {"Falling": "Pressure slowly falling - fish feed ahead of weather",
                 "Steady": "Pressure steady - normal feeding",
                 "Falling fast": "Pressure dropping fast - short feeding burst before the storm",
                 "Rising": "Pressure rising - fish are slower after a front",
                 "Rising fast": "Pressure rising fast - fish go deep and slow after a storm"}
    pts += trend_pts.get(TREND, 15)
    reasons.append(trend_why.get(TREND, "Pressure trend not known yet"))
    if window:
        pts += 25 if window["kind"] == "Major" else 15
        reasons.append(f"In a {window['kind'].upper()} feeding window ({window['why']}) until {hm(window['e'])}")
    elif soon:
        pts += 8
        reasons.append(f"{nxt['kind']} window starts at {hm(nxt['s'])} ({nxt['why']})")
    if near_sun:
        pts += 20
        reasons.append("Dawn or dusk - prime time")
    pts += {"Best": 15, "Good": 10, "Average": 5}[today["day_rating"]]
    reasons.append(f"{today['phase']} - {today['day_rating'].lower()} moon for fishing")
    if WIND > 25:
        pts -= 20
        reasons.append(f"Very windy ({WIND:.0f} mph)")
    elif WIND > 15:
        pts -= 10
        reasons.append(f"Windy ({WIND:.0f} mph)")
    score = max(0, min(100, round(pts * 100 / 90)))
    rating = "Excellent" if score >= 75 else "Good" if score >= 55 else "Fair" if score >= 35 else "Slow"

    rows = [{"time": hm(sunrise), "sort": today["sunrise"], "what": "Sunrise", "kind": "Sun",
             "active": False, "past": sunrise < now},
            {"time": hm(sunset), "sort": today["sunset"], "what": "Sunset", "kind": "Sun",
             "active": False, "past": sunset < now}]
    for p in periods:
        if p["s"].date() == now.date() or p["e"].date() == now.date():
            last_night = p["s"].date() < now.date()
            rows.append({"time": f"{hm(p['s'])} - {hm(p['e'])}", "sort": p["start"],
                         "what": p["why"].capitalize() + (" (last night)" if last_night else ""),
                         "kind": p["kind"], "active": p in current, "past": p["e"] < now})
    rows.sort(key=lambda r: r["sort"])
    for r in rows:
        r.pop("sort")
    tomorrow_majors = [f"{hm(datetime.fromisoformat(p['start']))} - {hm(datetime.fromisoformat(p['end']))}"
                       for p in tomorrow["periods"] if p["kind"] == "Major"]
    if window:
        now_text = f"{window['kind']} window now - until {hm(window['e'])}"
    elif nxt:
        now_text = f"Next: {nxt['kind']} window at {hm(nxt['s'])}"
    else:
        now_text = ""
    # Icon follows the phase name, so the two always agree.
    moon_icon = {"New Moon": "mdi:moon-new", "Waxing Crescent": "mdi:moon-waxing-crescent",
                 "First Quarter": "mdi:moon-first-quarter", "Waxing Gibbous": "mdi:moon-waxing-gibbous",
                 "Full Moon": "mdi:moon-full", "Waning Gibbous": "mdi:moon-waning-gibbous",
                 "Last Quarter": "mdi:moon-last-quarter", "Waning Crescent": "mdi:moon-waning-crescent"}[today["phase"]]
    return {"rating": rating, "score": score, "reasons": reasons, "now_text": now_text,
            "in_window": window["kind"] if window else "", "rows": rows,
            "tomorrow_majors": tomorrow_majors, "tomorrow_rating": tomorrow["day_rating"],
            "phase": today["phase"], "illumination": today["illumination"], "day_rating": today["day_rating"],
            "moon_icon": moon_icon, "trend": TREND, "wind_mph": round(WIND)}


if __name__ == "__main__":
    print(json.dumps(forecast(datetime.now(tz))))
