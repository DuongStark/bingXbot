import requests
from config import GEMINI_API_KEY, GEMINI_API_URL

def analyze(data_text, question):
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": f"{data_text}\n\n{question}"}]
        }]
    }
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                from logger import log_event
                log_event(f"Gemini API không trả về candidates: {result}")
                return ""
        else:
            from logger import log_event
            log_event(f"Gemini API lỗi: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        from logger import log_event
        log_event(f"Lỗi khi gọi Gemini API: {e}")
        return ""