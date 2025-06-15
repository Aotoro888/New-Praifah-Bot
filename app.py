from flask import Flask, request, abort, render_template
from dotenv import load_dotenv
import os, sqlite3, datetime
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage

load_dotenv()
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")

app = Flask(__name__)
os.makedirs("static/images", exist_ok=True)

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        image_path TEXT,
        timestamp TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    return "✅ LINE Bot with Web UI is running."

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except Exception as e:
        print("ERROR:", e)
        abort(400)
    return 'OK'

@handler.add(MessageEvent)
def handle_message(event):
    text = None
    image_path = None

    if isinstance(event.message, TextMessage):
        text = event.message.text

    elif isinstance(event.message, ImageMessage):
        message_id = event.message.id
        content = line_bot_api.get_message_content(message_id)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"static/images/image_{timestamp}.jpg"
        with open(filename, "wb") as f:
            f.write(content.content)
        image_path = filename

    if text or image_path:
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO records (text, image_path, timestamp) VALUES (?, ?, ?)",
                  (text, image_path, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="✅ รับข้อมูลแล้ว")
        )

@app.route("/history")
def history():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT text, image_path, timestamp FROM records ORDER BY id DESC")
    records = c.fetchall()
    conn.close()

    html = "<h2>📋 ประวัติการส่งข้อมูล</h2><ul>"
    for text, image_path, timestamp in records:
        html += f"<li><b>{timestamp}</b><br>ข้อความ: {text or '-'}<br>"
        if image_path:
            html += f"<img src='/{image_path}' width='300'><br>"
        html += "</li><hr>"
    html += "</ul>"
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
