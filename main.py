import os
import telebot
import requests
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
# These will be set in Render Environment Variables
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
HF_TOKEN = os.getenv('HF_TOKEN')
API_URL = "https://api-inference.huggingface.co/models/deepseek-ai/DeepSeek-R1"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are ORACLE PRO, an autonomous institutional-grade financial intelligence system.
Your function is to analyze markets, detect trends, and generate probabilistic forecasts.

STRICT OUTPUT FORMAT:
📊 SYMBOL: [Symbol]
💰 PRICE: [Price]
📉 RSI: [Value]
📊 EMA TREND: [Bullish/Bearish/Sideways]
📊 VOLATILITY: [Low/Medium/High]
😨 SENTIMENT: [Fear/Neutral/Greed]
🧠 SCORE: [0-100]/100
🚦 SIGNAL: [BUY/SELL/WAIT]
💼 ACTION: [OPEN LONG/OPEN SHORT/NO TRADE]
🛡 RISK:
Position Size: [x%]
Stop Loss: [x%]
Take Profit: [x%]
🔮 PREDICTION: Bias: [Bullish/Bearish/Neutral]
Confidence: [Low/Medium/High]
Timeframe: [1h/6h/24h]
"""

def query_hf(prompt):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": f"{SYSTEM_PROMPT}\n\nUser Request: {prompt}",
        "parameters": {"max_new_tokens": 500, "return_full_text": False}
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        result = response.json()
        if isinstance(result, list):
            return result[0]['generated_text']
        return result.get('generated_text', "Error: Model failed to generate response.")
    except Exception as e:
        return f"Error connecting to ORACLE Core: {str(e)}"

# --- TELEGRAM HANDLERS ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🚀 ORACLE PRO ONLINE. Send a symbol (e.g., BTCUSDT) for intelligence analysis.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    analysis = query_hf(message.text)
    bot.reply_to(message, analysis)

# --- WEB SERVER FOR RENDER ---
@app.route('/')
def health_check():
    return "ORACLE PRO IS ACTIVE", 200

def run_bot():
    bot.polling(none_stop=True)

if __name__ == "__main__":
    # Run Telegram Bot in a separate thread
    Thread(target=run_bot).start()
    # Run Flask server for Render's health check
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
