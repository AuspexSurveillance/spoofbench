"""Price, buy and download CME order-by-order (MBO) data from Databento.

    pip install -U databento
    python get_cme_mbo.py          (or double-click run_me.bat)

The API key is read from the DATABENTO_API_KEY environment variable, or from APIKey.txt next to
this script, or asked for. Nothing is bought until you type BUY at the prompt. The job id is saved
in cme_mbo/job.json, so running this again resumes the same purchase instead of making a second one.
"""
import getpass
import json
import os
import sys
import time
from pathlib import Path

import databento as db

SYMBOLS = ["ESZ6", "ZNZ6"]                 # December 2026 contracts
REQ = dict(
    dataset="GLBX.MDP3",
    schema="mbo",
    stype_in="raw_symbol",
    start="2026-11-02T00:00:00+00:00",     # midnight UTC, so each day starts with a book snapshot
    end="2026-11-14T00:00:00+00:00",       # 10 trading days: Nov 2-13
)
HERE = Path(__file__).resolve().parent
OUT = HERE / "cme_mbo"
STATE = OUT / "job.json"
KEYFILE = HERE / "APIKey.txt"


def api_key():
    key = os.environ.get("DATABENTO_API_KEY")
    if not key and KEYFILE.exists():
        key = KEYFILE.read_text(encoding="utf-8-sig").strip()
    return key or getpass.getpass("Databento API key (input hidden): ").strip()


def main():
    client = db.Historical(api_key())
    OUT.mkdir(exist_ok=True)

    if STATE.exists():
        job_id = json.loads(STATE.read_text())["id"]
        print(f"Resuming job {job_id} (already purchased; nothing new will be bought).")
    else:
        total = 0.0
        for s in SYMBOLS:
            cost = client.metadata.get_cost(symbols=[s], **REQ)
            total += cost
            print(f"{s}: ${cost:,.2f}")
        print(f"total: ${total:,.2f}  ({REQ['start'][:10]} to {REQ['end'][:10]}, {REQ['schema']})")
        if input("Type BUY to purchase and download, anything else to stop: ").strip() != "BUY":
            sys.exit("Stopped. Nothing was bought.")
        job = client.batch.submit_job(symbols=SYMBOLS, encoding="dbn", compression="zstd",
                                      split_duration="day", split_symbols=True, **REQ)
        job_id = job["id"]
        STATE.write_text(json.dumps({"id": job_id, "request": REQ, "symbols": SYMBOLS}, indent=1))
        print(f"Submitted job {job_id}.")

    while True:
        state = next((j["state"] for j in client.batch.list_jobs() if j["id"] == job_id), "pending")
        print(time.strftime("%H:%M:%S"), state)
        if state == "done":
            break
        if state == "expired":
            sys.exit("The job expired on Databento's side. Check the Download center in the portal.")
        time.sleep(30)

    files = client.batch.download(job_id=job_id, output_dir=OUT)
    size = sum(p.stat().st_size for p in files) / 1e9
    print(f"Downloaded {len(files)} files, {size:.2f} GB, into {OUT.resolve()}")


if __name__ == "__main__":
    main()
