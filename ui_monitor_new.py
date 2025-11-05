"""
ui_monitor_schedule.py

Monitor multiple URLs with individual check intervals specified in a CSV file.
CSV format: url,interval
Example:
  URL,interval
  https://nationwide.com/,2
  https://uat.nationwide.com/,4
  https://staging.nationwide.com/,5

This script reads the CSV, schedules checks per-URL, and prints UP/DOWN/ERROR messages with flush=True.
"""
import csv
import time
import requests
import sys
from datetime import datetime
from urllib.parse import urlparse

CSV_FILE = "url.csv"
REQUEST_TIMEOUT = 10
DOWN_INDICATOR = "The website you are trying to reach is temporarily unavailable"

# Use a browser-like User-Agent to avoid simple bot-blocking by some sites
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def read_url_intervals(csv_file):
    url_intervals = {}
    try:
        with open(csv_file, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if not row:
                    continue
                # skip header row if present
                first = row[0].strip()
                if first.lower() in ("url", "site"):
                    continue
                url = first
                interval = None
                if len(row) >= 2 and row[1].strip():
                    try:
                        interval = int(row[1].strip())
                    except ValueError:
                        print(f"[WARN] Invalid interval '{row[1]}' for '{url}', skipping row", flush=True)
                        continue
                if not urlparse(url).scheme:
                    url = 'https://' + url
                url_intervals[url] = interval or 60
    except FileNotFoundError:
        print(f"[ERROR] CSV file not found: {csv_file}", flush=True)
    except Exception as e:
        print(f"[ERROR] Could not read CSV file: {e}", flush=True)
    return url_intervals

def is_site_down(response_text):
    return DOWN_INDICATOR in response_text

def check_url(url):
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        status_code = resp.status_code

        # Monitor specific HTTP error codes for alerts
        if status_code in [500, 502, 503, 504, 501]:
            return "ERROR", f"HTTP {status_code}: Server error"
        elif status_code in [404, 403, 410, 429]:
            return "ERROR", f"HTTP {status_code}: Client error or rate limiting"
        elif status_code >= 400:
            return "DOWN", f"HTTP {status_code}: {resp.reason}"

        # Check site down indicator text in response body
        if is_site_down(resp.text):
            return "DOWN", f"Site indicates down: {DOWN_INDICATOR}"

        return "UP", f"HTTP {status_code}"

    except requests.exceptions.RequestException as e:
        return "ERROR", str(e)
    except Exception as e:
        return "ERROR", str(e)

def monitor(csv_file):
    url_intervals = read_url_intervals(csv_file)
    if not url_intervals:
        print('[ERROR] No valid URL entries found in CSV. Exiting.', flush=True)
        sys.exit(1)

    next_check = {url: time.time() for url in url_intervals}
    last_status = {url: None for url in url_intervals}

    print(f"Monitoring {len(url_intervals)} URLs (per-row intervals).", flush=True)
    try:
        while True:
            now = time.time()
            for url, interval in url_intervals.items():
                if now >= next_check[url]:
                    status, detail = check_url(url)
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if status == 'UP':
                        print(f"[{timestamp}] [OK] {url} - {detail}", flush=True)
                    elif status == 'DOWN':
                        print(f"[{timestamp}] [ALERT] {url} - {detail}", flush=True)
                    else:
                        print(f"[{timestamp}] [ERROR] {url} - {detail}", flush=True)
                    last_status[url] = status
                    next_check[url] = now + interval
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nMonitoring stopped by user', flush=True)

if __name__ == '__main__':
    monitor(CSV_FILE)
