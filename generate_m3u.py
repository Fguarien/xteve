#!/usr/bin/env python3
# coding: utf-8
"""
Xtream API -> mini M3U generator
Reads player_api.php and get_live_streams, filters channels and writes /data/playlist.m3u
"""

import os, time, requests, json, sys, re
from urllib.parse import quote_plus

XT_HOST = os.getenv("XTREAM_HOST")
USER = os.getenv("XTREAM_USER")
PASS = os.getenv("XTREAM_PASS")
FILTER_KW = os.getenv("FILTER_KEYWORDS","").split(",")
REFRESH = int(os.getenv("REFRESH_SECS","21600"))
OUT_DIR = "/data"
OUT_FILE = os.path.join(OUT_DIR, "playlist.m3u")
PORT = int(os.getenv("PORT","35000"))

# Headers to mimic iPhone app
HEADERS = {
    "Host": XT_HOST,
    "Accept": "*/*",
    "User-Agent": "ipTV/193 CFNetwork/1410.4 Darwin/22.6.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

PROX = os.getenv("HTTP_PROXY") or None
PROXIES = {"http": PROX, "https": PROX} if PROX else None

def log(*a, **k):
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), *a, **k)
    sys.stdout.flush()

def build_base_url(path=""):
    # path can be "player_api.php" or full query
    if XT_HOST.startswith("http://") or XT_HOST.startswith("https://"):
        base = XT_HOST
    else:
        base = "http://" + XT_HOST
    return base.rstrip("/") + "/" + path.lstrip("/")

def fetch_json(url, params=None, timeout=30):
    try:
        r = requests.get(url, headers=HEADERS, params=params, proxies=PROXIES, timeout=timeout)
        r.raise_for_status()
        # sometimes API returns JSON or plain text
        return r.json()
    except Exception as e:
        log("fetch_json failed:", url, e)
        # fallback: try text parse
        try:
            return json.loads(r.text)
        except Exception:
            return None

def fetch_text(url, params=None, timeout=60):
    r = requests.get(url, headers=HEADERS, params=params, proxies=PROXIES, timeout=timeout, stream=True)
    r.raise_for_status()
    return r.text

def fetch_channels():
    # Try common endpoints. First: player_api.php with action=get_live_streams
    base = build_base_url("player_api.php")
    params = {"username": USER, "password": PASS, "action": "get_live_streams"}
    try:
        data = fetch_json(base, params=params)
        if not data:
            # Some providers require /player_api.php?username=..&password=.. (no action) to get user_info
            # Then use get_live_streams endpoint
            data = fetch_json(build_base_url("player_api.php"), params={"username":USER,"password":PASS,"action":"get_live_streams"})
    except Exception as e:
        log("Error fetching channels:", e)
        data = None

    # Some panels return a dict of channels keyed by an ID, or a list.
    channels = []
    if isinstance(data, list):
        channels = data
    elif isinstance(data, dict):
        # Try known keys
        if "streams" in data:
            channels = data.get("streams") or data.get("streams", [])
        elif "available_channels" in data:
            channels = data.get("available_channels")
        else:
            # try to detect list-like values
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict) and "stream_id" in v[0] or "stream_name" in v[0] or "name" in v[0]:
                    channels = v
                    break

    # Normalise channels to expected fields
    norm = []
    for c in channels:
        # several possible key names
        name = c.get("name") or c.get("stream_name") or c.get("title") or c.get("channel") or c.get("stream_title")
        stream_id = c.get("stream_id") or c.get("stream_id") or c.get("channel_id") or c.get("channel_number")
        cmd = None
        # if direct url provided
        if "url" in c:
            cmd = c.get("url")
        # else build typical xtream live url
        if not cmd:
            # some panels use: http://host:port/live/{USER}/{PASS}/{stream_id}.ts
            cmd = f"http://{XT_HOST}/live/{quote_plus(USER)}/{quote_plus(PASS)}/{stream_id}.ts"
        # group/category
        group = c.get("category") or c.get("stream_category") or c.get("category_name") or c.get("group") or ""
        tvgid = c.get("tvg_id") or c.get("tvg-id") or ""
        logo = c.get("icon") or c.get("stream_icon") or ""
        norm.append({
            "name": name or f"ch_{stream_id}",
            "id": stream_id,
            "url": cmd,
            "group": group or "",
            "tvgid": tvgid or "",
            "logo": logo or "",
        })
    return norm

def filter_channels(chs):
    if not FILTER_KW or FILTER_KW==[''] :
        return chs
    keep = []
    kws = [k.strip().lower() for k in FILTER_KW if k.strip()]
    for c in chs:
        hay = " ".join([c.get("name",""), c.get("group","")]).lower()
        if any(kw in hay for kw in kws):
            keep.append(c)
    return keep

def write_m3u(chs):
    log("Writing", OUT_FILE, "channels:", len(chs))
    with open(OUT_FILE + ".tmp", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for c in chs:
            ext = f'#EXTINF:-1 tvg-id="{c.get("tvgid","")}" tvg-name="{c.get("name","")}" tvg-logo="{c.get("logo","")}" group-title="{c.get("group","")}",{c.get("name","")}\n'
            f.write(ext)
            f.write(c.get("url") + "\n")
    os.replace(OUT_FILE + ".tmp", OUT_FILE)
    log("M3U updated:", OUT_FILE)

def main_loop():
    os.makedirs(OUT_DIR, exist_ok=True)
    while True:
        try:
            log("Fetching channels from XTream API...")
            chs = fetch_channels()
            if not chs:
                log("No channels fetched.")
            else:
                filtered = filter_channels(chs)
                if not filtered:
                    log("No channels after filtering (keywords):", FILTER_KW)
                    # fallback: keep first 200 channels to avoid empty lists
                    filtered = chs[:200]
                write_m3u(filtered)
        except Exception as e:
            log("Main loop error:", e)
        log(f"Sleeping {REFRESH} seconds...")
        time.sleep(REFRESH)

if __name__ == "__main__":
    main_loop()
