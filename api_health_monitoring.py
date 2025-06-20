import requests
import time
import schedule
import logging
import json
from datetime import datetime
from config import ENDPOINTS, SLACK_ENABLED, SLACK_WEBHOOK_URL, LOG_FILE

# Set up logging
logging.basicConfig(
    filename=LOG_FILE,
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log(msg, level="info"):
    print(msg)
    if level == "info":
        logging.info(msg)
    elif level == "error":
        logging.error(msg)
    elif level == "warning":
        logging.warning(msg)

def send_slack_alert(title, message):
    if not SLACK_ENABLED:
        log("[!] Slack alert skipped (disabled)", "warning")
        return

    payload = {
        "text": f"*{title}*\n{message}",
        "username": "API Monitor",
        "icon_emoji": ":rotating_light:"
    }

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code != 200:
            raise Exception(f"Slack response: {response.status_code}")
        log("[+] Slack alert sent")
    except Exception as e:
        log(f"[!] Failed to send Slack alert: {e}", "error")

def check_endpoint(ep):
    try:
        log(f"[*] Checking {ep['name']} - {ep['url']}")
        method = ep.get("method", "GET").upper()
        req = requests.request(
            method,
            ep["url"],
            json=ep.get("payload"),
            headers=ep.get("headers"),
            timeout=ep["timeout"]
        )
        duration = req.elapsed.total_seconds()
        status = req.status_code

        if status != ep["expected_status"]:
            raise Exception(f"Expected {ep['expected_status']}, got {status}")
        
        if "expected_text" in ep and ep["expected_text"] not in req.text:
            raise Exception("Expected text not found in response")

        log(f"[+] {ep['name']} OK in {duration:.2f}s")

    except Exception as e:
        error_msg = f"[!] {ep['name']} FAILED: {e}"
        log(error_msg, "error")
        send_slack_alert(f"[ALERT] {ep['name']} failed", f"Endpoint: {ep['url']}\nError: {e}")

def run_all_checks():
    log(f"=== Running API checks @ {datetime.now()} ===")
    for ep in ENDPOINTS:
        check_endpoint(ep)

# Schedule the job every 5 minutes
schedule.every(5).minutes.do(run_all_checks)

# Initial run
run_all_checks()

# Main loop
while True:
    schedule.run_pending()
    time.sleep(1)
