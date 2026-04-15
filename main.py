import os
import datetime
import requests
import telebot
from flask import Flask
from threading import Thread
from mongoengine import connect, Document, StringField, IntField, DateTimeField, FloatField

# --- 1. CONFIGURATION & ENVIRONMENT ---
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
HF_TOKEN = os.getenv('HF_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
# Hugging Face DeepSeek-R1 API
API_URL = "https://api-inference.huggingface.co/models/deepseek-ai/DeepSeek-R1"

# Initialize Bot and Flask
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- 2. DATABASE SCHEMA (MONGOENGINE) ---
# This tracks every signal ORACLE PRO generates
connect(host=MONGO_URI)

class TradeSignal(Document):
    symbol = StringField(required=True, uppercase=True)
    price = StringField()
    signal = StringField(choices=['BUY', 'SELL', 'WAIT'])
    score = IntField()
    analysis = StringField()
    created_at = DateTimeField(default=datetime.datetime.utcnow)

# --- 3. ORACLE PRO AI ENGINE ---
SYSTEM_PROMPT = """
🚀 ORACLE PRO — AUTONOMOUS FINANCIAL INTELLIGENCE SYSTEM
Analyze the following market data and provide a professional institutional-grade report.

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
Position Size: [1-2%]
Stop Loss: [Value%]
Take Profit: [Value%]
🔮 PREDICTION: Bias: [Bullish/Bearish/Neutral]
Confidence: [Low/Medium/High]
Timeframe: [1h/6h/24h]
"""

def query_deepseek(user_input):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    # We combine the system logic with the user market data
    full_prompt = f"{SYSTEM_PROMPT}\n\nMarket Data Input: {user_input}\n\nAnalysis:"
    
    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 800,
            "temperature": 0.7,
            "return_full_text": False
        }
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0:
            return result[0]['generated_text']
        else:
            return "⚠️ Error: AI Engine returned empty result."
    except Exception as e:
        return f"❌ AI Engine Error: {str(e)}"

# --- 4. TELEGRAM BOT HANDLERS ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🚀 **ORACLE PRO ONLINE**\n"
        "Autonomous Financial Intelligence System Activated.\n\n"
        "**Usage:** Send me a symbol and current data.\n"
        "**Example:** `BTCUSDT Price 68000 RSI 65 EMA Bullish`"
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_analysis(message):
    processing_msg = bot.reply_to(message, "🧠 *Processing Market Intelligence...*", parse_mode='Markdown')
    
    # Get Analysis from DeepSeek
    analysis_output = query_deepseek(message.text)
    
    # Send Result to User
    bot.edit_message_text(analysis_output, chat_id=message.chat.id, message_id=processing_msg.message_id)
    
    # Save to MongoDB for Trade History
    try:
        # Simple extraction logic for logging
        sig_type = "WAIT"
        if "BUY" in analysis_output.upper(): sig_type = "BUY"
        elif "SELL" in analysis_output.upper(): sig_type = "SELL"
        
        log = TradeSignal(
            symbol=message.text.split()[0][:10], # Extract first word as symbol
            signal=sig_type,
            analysis=analysis_output
        )
        log.save()
    except Exception as db_e:
        print(f"Database Log Error: {db_e}")

# --- 5. SERVER INFRASTRUCTURE ---
@app.route('/')
def health_check():
    return "ORACLE PRO IS ACTIVE", 200

def run_bot():
    print("Bot is polling...")
    bot.infinity_polling()

if __name__ == "__main__":
    # Start Telegram in a background thread
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    
    # Start Flask for Render
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
