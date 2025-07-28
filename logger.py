from datetime import datetime

def log_event(event):
    with open("trade_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {event}\n") 