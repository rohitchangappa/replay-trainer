"""
fetch_replay_data.py — pull real 1-minute history for the Replay Trainer game.

Downloads actual past 1m OHLCV for SPY, QQQ, ES and NQ (front-month futures)
from Yahoo Finance and writes one JSON file per symbol in the format the game
imports directly:  [{"time":..., "open":..., "high":..., "low":..., "close":..., "volume":...}, ...]

Yahoo only serves 1-minute bars for the LAST ~30 DAYS, in chunks of <=7 days
per request — this script handles the chunking. Run it every week or two and
re-import to keep growing your library (the game merges days by date, so you
can also keep appending to one file per symbol yourself).

Usage (on your PC):
    pip install yfinance
    python fetch_replay_data.py

Output:  SPY_1m.json, QQQ_1m.json, ES_1m.json, NQ_1m.json  (in this folder)
Then move the files to the tablet and load each via the game's settings (pick
the matching instrument in the dropdown before choosing the file).
"""
import json, time, datetime as dt

try:
    import yfinance as yf
except ImportError:
    raise SystemExit("yfinance not installed. Run:  pip install yfinance")

SYMBOLS = {
    "SPY": {"yahoo": "SPY",  "prepost": True},   # include premarket for PMH/PML
    "QQQ": {"yahoo": "QQQ",  "prepost": True},
    "ES":  {"yahoo": "ES=F", "prepost": True},   # futures: overnight session -> ON H/L
    "NQ":  {"yahoo": "NQ=F", "prepost": True},
}
DAYS_BACK = 29          # Yahoo's 1m window is ~30 days
CHUNK_DAYS = 7          # Yahoo's per-request limit for 1m bars


def fetch_symbol(name, yahoo_sym, prepost):
    end = dt.datetime.now()
    start = end - dt.timedelta(days=DAYS_BACK)
    bars = {}
    t = start
    while t < end:
        t2 = min(t + dt.timedelta(days=CHUNK_DAYS), end)
        print(f"  {name}: {t.date()} -> {t2.date()} ...", flush=True)
        df = yf.download(
            yahoo_sym, interval="1m",
            start=t.strftime("%Y-%m-%d"), end=(t2 + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
            prepost=prepost, progress=False, auto_adjust=False, threads=False,
        )
        if df is not None and len(df):
            # yfinance may return multi-level columns; flatten
            if hasattr(df.columns, "levels"):
                df.columns = [c[0] for c in df.columns]
            for ts, row in df.iterrows():
                epoch = int(ts.timestamp())
                o, h, l, c = row.get("Open"), row.get("High"), row.get("Low"), row.get("Close")
                if o != o or c != c:   # NaN guard
                    continue
                v = row.get("Volume", 0)
                bars[epoch] = {
                    "time": epoch,
                    "open": round(float(o), 4), "high": round(float(h), 4),
                    "low": round(float(l), 4), "close": round(float(c), 4),
                    "volume": int(v) if v == v else 0,
                }
        t = t2
        time.sleep(1.5)  # be polite to Yahoo
    out = [bars[k] for k in sorted(bars)]
    return out


def main():
    for name, spec in SYMBOLS.items():
        print(f"Fetching {name} ({spec['yahoo']}) — real 1m bars, last {DAYS_BACK} days")
        rows = fetch_symbol(name, spec["yahoo"], spec["prepost"])
        if not rows:
            print(f"  !! no data returned for {name} — Yahoo may be rate-limiting; retry later")
            continue
        fn = f"{name}_1m.json"
        with open(fn, "w") as f:
            json.dump(rows, f)
        first = dt.datetime.fromtimestamp(rows[0]["time"]).date()
        last = dt.datetime.fromtimestamp(rows[-1]["time"]).date()
        print(f"  wrote {fn}: {len(rows):,} bars, {first} -> {last}")
    print("\nDone. Move the JSON files to the tablet and import each one in the game")
    print("(settings gear -> pick instrument in the dropdown -> choose file).")


if __name__ == "__main__":
    main()
