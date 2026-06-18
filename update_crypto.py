#!/usr/bin/env python3
"""
Binance 일봉(OHLCV) CSV 증분 갱신 스크립트.
- 기존 CSV의 마지막 캔들 이후 데이터만 받아서 이어붙입니다.
- 아직 마감되지 않은(진행 중) 캔들은 저장하지 않습니다.
"""
import os
import csv
import time
import requests

# 한국에서 api.binance.com 이 막히면 data-api.binance.vision 로 자동 폴백
BASE_URLS = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
]

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
INTERVAL = "1d"
DATA_DIR = "data"

HEADER = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]


def get_klines(symbol, start_time=None):
    """여러 base URL을 순서대로 시도하며 klines를 받아온다."""
    params = {"symbol": symbol, "interval": INTERVAL, "limit": 1000}
    if start_time:
        params["startTime"] = start_time
    last_err = None
    for base in BASE_URLS:
        try:
            r = requests.get(f"{base}/api/v3/klines", params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"{symbol} 데이터 수집 실패: {last_err}")


def last_open_time(path):
    """기존 CSV의 마지막 open_time(ms) 반환. 없으면 None."""
    if not os.path.exists(path):
        return None
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    if len(rows) <= 1:
        return None
    try:
        return int(rows[-1][0])
    except (ValueError, IndexError):
        return None


def update_symbol(symbol):
    path = os.path.join(DATA_DIR, f"{symbol}_{INTERVAL}.csv")
    os.makedirs(DATA_DIR, exist_ok=True)

    last_ts = last_open_time(path)
    start = last_ts + 1 if last_ts else None

    klines = get_klines(symbol, start)
    now_ms = int(time.time() * 1000)

    # close_time이 현재보다 과거 = 마감된 캔들만 채택
    closed = [k for k in klines if k[6] < now_ms]
    if last_ts:
        closed = [k for k in closed if k[0] > last_ts]

    write_header = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(HEADER)
        for k in closed:
            w.writerow(k)

    print(f"{symbol}: {len(closed)}개 캔들 추가 (파일: {path})")


if __name__ == "__main__":
    for s in SYMBOLS:
        update_symbol(s)
    print("완료")
