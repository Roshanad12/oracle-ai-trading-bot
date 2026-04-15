import os
import datetime
import requests
import telebot
import time
import random
from flask import Flask
from threading import Thread
from mongoengine import connect, Document, StringField, IntField, DateTimeField, FloatField, DynamicDocument

# --- 1. CONFIGURATION & ROBUST ENVIRONMENT ---
# Using os.environ.get with defaults prevents the script from crashing immediately
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
HF_TOKEN = os.environ.get('HF_TOKEN')
MONGO_URI = os.environ.get('MONGO_URI')
# DeepSeek-R1 via Hugging Face
API_URL = "https://api-inference.huggingface.co/models/deepseek-ai/DeepSeek-R1"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- 2. DATABASE CONNECTIVITY (WITH RETRY LOGIC) ---
def connect_db():
    try:
        connect(host=MONGO_URI, alias='default')
        print("✅ DATABASE: Connected to Oracle Intelligence Vault (MongoDB)")
    except Exception as e:
        print(f"❌ DATABASE ERROR: Could not connect. {e}")

connect_db()

class TradeSignal(DynamicDocument): # DynamicDocument allows for flexible data storage
    symbol = StringField(required=True, uppercase=True)
    signal = StringField(choices=['BUY', 'SELL', 'WAIT', 'NEUTRAL'])
    analysis = StringField()
    timestamp = DateTimeField(default=datetime.datetime.utcnow)
    meta = {'collection': 'trade_signals'}

# --- 3. THE ADVANCED AI ENGINE ---
SYSTEM_PROMPT = """
🚀 ORACLE PRO — AUTONOMOUS FINANCIAL INTELLIGENCE SYSTEM
Institutional-grade analysis requested. 

STRICT OUTPUT FORMAT:
📊 SYMBOL: [Symbol]
💰 PRICE: [Price]
🧠 AI SCORE: [0-100]/100
🚦 SIGNAL: [BUY/SELL/WAIT]
💼 ACTION: [OPEN LONG/OPEN SHORT/NO TRADE]
🛡 RISK: [1-2%]
🔮 PREDICTION: [Bullish/Bearish/Neutral]
---
Detailed Institutional Reasoning:
[Provide 2-3 sentences of deep technical reasoning here]
"""

def query_deepseek(user_input):
    if not HF_TOKEN:
        return "❌ HF_TOKEN missing in Environment Variables."
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    full_prompt = f"{SYSTEM_PROMPT}\n\n[MARKET DATA INPUT]: {user_input}\n\n[FINAL ANALYSIS]:"
    
    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 1000,
            "temperature": 0.6, # Lower temp = more professional/stable analysis
            "top_p": 0.9,
            "do_sample": True
        }
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        result = response.json()
        
        # DeepSeek-R1 can return thinking process; we want the clean output
        if isinstance(result, list) and len(result) > 0:
            return result[0].get('generated_text', "⚠️ AI returned empty string.")
        return "⚠️ Unexpected AI response format."
    except requests.exceptions.Timeout:
        return "⏱️ AI Engine Timeout (DeepSeek is thinking very hard...)"
    except Exception as e:
        return f"❌ Engine Failure: {str(e)}"

# --- 4. SMART TELEGRAM HANDLERS ---
@bot.message_handler(commands=['start'])
def welcome(message):
    msg = (
        "✨ **ORACLE PRO v3.0**\n"
        "DeepSeek-R1 Neural Engine: **ONLINE**\n"
        "Database Vault: **CONNECTED**\n\n"
        "Send market data for institutional analysis.\n"
        "Example: `SOL 145USD RSI 40 EMA 200 Support`"
    )
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def process_intelligence(message):
    # 1. Visual Feedback
    processing = bot.reply_to(message, "🔌 *Connecting to DeepSeek-R1 Neural Grid...*", parse_mode='Markdown')
    
    # 2. Get AI Analysis
    analysis = query_deepseek(message.text)
    
    # 3. Dynamic UI Update
    bot.edit_message_text(analysis, chat_id=message.chat.id, message_id=processing.message_id)
    
    # 4. Background Data Logging (Doesn't stop the user if DB fails)
    try:
        symbol_extracted = message.text.split()[0][:10].upper()
        sig = "WAIT"
        if "BUY" in analysis.upper(): sig = "BUY"
        elif "SELL" in analysis.upper(): sig = "SELL"
        
        TradeSignal(symbol=symbol_extracted, signal=sig, analysis=analysis).save()
        print(f"📊 LOGGED: {symbol_extracted} signal saved to MongoDB.")
    except:
        print("⚠️ LOGGING: Failed to write to MongoDB, but bot is continuing.")

# --- 5. RENDER-READY INFRASTRUCTURE ---
@app.route('/')
def health_check():
    quotes = ["Fortune favors the bold.", "Trend is your friend.", "Analyze, then act."]
    return {
        "service": "ORACLE_PRO_AI",
        "status": "HEALTHY",
        "wisdom": random.choice(quotes),
        "db_status": "CONNECTED"
    }, 200

def run_polling():
    """Keeps the bot polling forever with crash recovery."""
    while True:
        try:
            print("🤖 BOT: Starting infinity polling...")
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"🤖 BOT CRASH: {e}. Restarting in 10s...")
            time.sleep(10)

if __name__ == "__main__":
    # Start Bot Thread
    bot_thread = Thread(target=run_polling, daemon=True)
    bot_thread.start()
    
    # Start Web Server (Required for Render)
    # Using port 10000 as it's standard for Render Free tier
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 SERVER: Global launch on port {port}")
    app.run(host='0.0.0.0', port=port)
    
