from flask import Flask
import threading
import main

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_bot():
    main.main_loop()  # Giả sử logic bot chính nằm trong hàm main_loop() trong main.py

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    app.run(host="0.0.0.0", port=8080) 