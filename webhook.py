from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    TemplateSendMessage, CarouselTemplate, CarouselColumn, MessageAction
)
from scraping_menudetail import scrape_product_detail  # ใช้ฟังก์ชัน scrape แบบสด
import csv
import json

app = Flask(__name__)

# LINE Credentials
CHANNEL_SECRET = '10cc7f532a62b2208f2bdeb03148705d'
CHANNEL_ACCESS_TOKEN = 'o0rmXIz8Xk1QDlHDkPbgLglKWg+qXjzOPnJt/21VmAXGBYuXkFQKlIyt71CpXQrAndBq5tsDAoj9BL+UUiVqkXHj7X1LeM7kRUfoBAgcbTzfo+3me0MPhMcFyF0Hpo1zdrRhbvhzSb5fsbVRURAeVgdB04t89/1O/w1cDnyilFU='
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ---------------- Webhook ----------------
@app.route("/", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

def load_csv_items(csv_path, limit=10):
    items = []
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                keys = list(row.keys())
                name_key = keys[0]  # ควรเป็น 'name'
                url_key = keys[1]   # ควรเป็น 'url'

                name = row.get(name_key, "").strip()
                url = row.get(url_key, "").strip()

                if name and url:
                    items.append({
                        "name": name,
                        "url": url
                    })

                if len(items) >= limit:
                    break

        print("✅ โหลดสินค้าได้", len(items), "รายการ")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
    return items

def load_product_images_from_json(json_path):
    """โหลด mapping จากชื่อสินค้า (source_name) → รูปภาพหลัก (imageUrl)"""
    image_map = {}
    try:
        with open(json_path, encoding='utf-8') as f:
            details = json.load(f)
            for item in details:
                name = item.get("source_name", "").strip()
                image = item.get("imageUrl", "")
                if name and image:
                    image_map[name] = image
    except Exception as e:
        print(f"❌ Error loading product images from JSON: {e}")
    return image_map


def generate_carousel_columns(items, category, image_map):
    columns = []
    for item in items:
        name = item["name"]
        image = image_map.get(name, f"https://via.placeholder.com/1024x1024?text={category}")
        columns.append(
            CarouselColumn(
                title=item["name"][:40],
                text=f"{category} รุ่นใหม่ 🔍",
                thumbnail_image_url= image,
                actions=[MessageAction(label="ดูรายละเอียด", text=item["name"])]
            )
        )
    return columns

# ---------------- Handle Message ----------------
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text.strip().lower()

    if user_input == "menu":
        carousel_columns = [
            CarouselColumn(
                title="💻 Notebook",
                text="กดเพื่อดูสินค้าหมวดโน้ตบุ๊ค",
                thumbnail_image_url="https://cdn.pixabay.com/photo/2015/01/21/14/14/apple-606761_1280.jpg",
                actions=[MessageAction(label="เลือก", text="notebook")]
            ),
            CarouselColumn(
                title="📱 Smartphone",
                text="กดเพื่อดูสินค้าหมวดสมาร์ตโฟน",
                thumbnail_image_url="https://cdn.pixabay.com/photo/2016/11/22/23/40/hands-1851218_640.jpg",
                actions=[MessageAction(label="เลือก", text="smartphone")]
            ),
            CarouselColumn(
                title="🎮 Gaming Gear",
                text="กดเพื่อดูสินค้าหมวดเกมมิ่งเกียร์",
                thumbnail_image_url="https://cdn.pixabay.com/photo/2021/02/10/13/35/tablet-6002100_640.jpg",
                actions=[MessageAction(label="เลือก", text="gaming gear")]
            )
        ]

        message = TemplateSendMessage(
            alt_text="เลือกหมวดสินค้า",
            template=CarouselTemplate(columns=carousel_columns)
        )

        line_bot_api.reply_message(event.reply_token, message)
    
    elif user_input == "notebook":
        items = load_csv_items("bnn_links/notebook.csv", limit=10)
        image_map = load_product_images_from_json("bnn_details_json\\notebook_details.json")

        if not items:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ ไม่พบสินค้าหมวด Notebook หรือไฟล์ CSV ผิดพลาด")
            )
            return

        columns = generate_carousel_columns(items, category="Notebook", image_map=image_map)
        if not columns:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ ไม่สามารถแสดงรายการสินค้าได้")
            )
            return

        message = TemplateSendMessage(
            alt_text="รายการ Notebook",
            template=CarouselTemplate(columns=columns)
        )
        line_bot_api.reply_message(event.reply_token, message)

    elif user_input == "smartphone":
        items = load_csv_items("bnn_links/smartphone-and-accessories.csv", limit=10)
        image_map = load_product_images_from_json("bnn_details_json\smartphone-and-accessories_details.json")

        columns = generate_carousel_columns(items, category="Smartphone", image_map=image_map)
        message = TemplateSendMessage(
            alt_text="รายการ Smartphone",
            template=CarouselTemplate(columns=columns)
        )
        line_bot_api.reply_message(event.reply_token, message)

    elif user_input == "gaming gear":
        items = load_csv_items("bnn_links/gaming-gear.csv", limit=10)
        image_map = load_product_images_from_json("bnn_details_json\gaming-gear_details.json")

        columns = generate_carousel_columns(items, category="Gaming+Gear", image_map=image_map)
        message = TemplateSendMessage(
            alt_text="รายการ Gaming Gear",
            template=CarouselTemplate(columns=columns)
        )
        line_bot_api.reply_message(event.reply_token, message)

    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🔎 พิมพ์ว่า 'menu' เพื่อเริ่มต้นเลือกหมวดสินค้า")
        )


if __name__ == "__main__":
    app.run(port=5000)