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
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return "" 