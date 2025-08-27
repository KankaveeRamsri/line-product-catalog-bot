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

user_context = {}

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

def load_csv_items(csv_path, limit=10, keyword=None):
    items = []
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = list(csv.DictReader(csvfile))
            for i, row in enumerate(reader):
                keys = list(row.keys())
                name = row.get(keys[0], "").strip()
                url = row.get(keys[1], "").strip()

                if not name or not url:
                    continue

                # ถ้ามี keyword ให้กรองเฉพาะสินค้าที่ชื่อมีคำนั้น
                if keyword and keyword.lower() not in name.lower():
                    continue

                items.append({
                    "name": name,
                    "url": url,
                    "csv_index": i   # ✅ เก็บ index เดิมใน CSV
                })

                if len(items) >= limit:
                    break

        print("✅ โหลดสินค้าได้", len(items), "รายการ")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
    return items


def get_url_by_index(csv_path, index):
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = list(csv.DictReader(csvfile))
            if 0 <= index < len(reader):
                return reader[index].get("url", "").strip()
    except Exception as e:
        print(f"❌ Error reading {csv_path}: {e}")
    return None

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
    for item_index, item in enumerate(items):  # ใช้ enumerate เพื่อได้ index
        name = item["name"]
        image = image_map.get(name, f"https://via.placeholder.com/1024x1024?text={category}")
        columns.append(
            CarouselColumn(
                title=name[:40],
                text=f"{category} รุ่นใหม่ 🔍",
                thumbnail_image_url=image,
                actions=[
                    MessageAction(label="ดูรายละเอียด", text=f"{item_index}|{category}")
                ]
            )
        )
    return columns

def reply_search_result(event, category, query, limit=10):
    csv_map = {
        "notebook": "bnn_links/notebook.csv",
        "smartphone": "bnn_links/smartphone-and-accessories.csv",
        "gaming gear": "bnn_links/gaming-gear.csv"
    }
    json_map = {
        "notebook": "bnn_details_json\\notebook_details.json",
        "smartphone": "bnn_details_json\smartphone-and-accessories_details.json",
        "gaming gear": "bnn_details_json\gaming-gear_details.json"
    }

    csv_path = csv_map.get(category)
    json_path = json_map.get(category)
    if not csv_path:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ ยังไม่รองรับหมวดนี้"))
        return

    items = load_csv_items(csv_path, limit=limit, keyword=query)
    if not items:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"ไม่พบสินค้าในหมวด {category} ที่ตรงกับ “{query}”")
        )
        return

    image_map = load_product_images_from_json(json_path)
    columns = []
    for it in items:
        img = image_map.get(it["name"], f"https://via.placeholder.com/1024x1024?text={category}")
        columns.append(
            CarouselColumn(
                title=it["name"][:40],
                text=f"{category.capitalize()} | ค้นหา: {query[:20]}",
                thumbnail_image_url=img,
                actions=[
                    MessageAction(
                        label="ดูรายละเอียด",
                        text=f"{it['csv_index']}|{category}"  # ✅ index เดิมจาก CSV
                    )
                ]
            )
        )

    message = TemplateSendMessage(
        alt_text=f"ผลการค้นหา {category}: {query}",
        template=CarouselTemplate(columns=columns)
    )
    line_bot_api.reply_message(event.reply_token, message)




csv_filenames = [
    "bnn_links\\notebook.csv",
    "bnn_links\smartphone-and-accessories.csv",
    "bnn_links\gaming-gear.csv"
]


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
        user_context[event.source.user_id] = {"last_category": "notebook"}
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
        user_context[event.source.user_id] = {"last_category": "smartphone"}
        items = load_csv_items("bnn_links/smartphone-and-accessories.csv", limit=10)
        image_map = load_product_images_from_json("bnn_details_json\smartphone-and-accessories_details.json")

        columns = generate_carousel_columns(items, category="Smartphone", image_map=image_map)
        message = TemplateSendMessage(
            alt_text="รายการ Smartphone",
            template=CarouselTemplate(columns=columns)
        )
        line_bot_api.reply_message(event.reply_token, message)

    elif user_input == "gaming gear":
        user_context[event.source.user_id] = {"last_category": "gaming gear"}
        items = load_csv_items("bnn_links/gaming-gear.csv", limit=10)
        image_map = load_product_images_from_json("bnn_details_json\gaming-gear_details.json")

        columns = generate_carousel_columns(items, category="Gaming gear", image_map=image_map)
        message = TemplateSendMessage(
            alt_text="รายการ Gaming Gear",
            template=CarouselTemplate(columns=columns)
        )
        line_bot_api.reply_message(event.reply_token, message)

    else:
        # แยก user_input ออกเป็น index และ category
        if '|' in user_input:
            try:
                index_str, category = user_input.split('|')
                index = int(index_str)

                # เลือก CSV path ตาม category
                csv_map = {
                    "notebook": "bnn_links/notebook.csv",
                    "smartphone": "bnn_links/smartphone-and-accessories.csv",
                    "gaming gear": "bnn_links/gaming-gear.csv"
                }
                csv_path = csv_map.get(category.lower())

                if not csv_path:
                    raise ValueError("ไม่รู้จักหมวดหมู่")

                url = get_url_by_index(csv_path, index)
                print("URL:", url)

                if url:
                    detail = scrape_product_detail(url)
                    if "error" in detail:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=f"⚠️ ดึงข้อมูลล้มเหลว: {detail['error']}")
                        )
                        return

                    message = (
                        f"📦 {detail['title']}\n"
                        f"🛠️ แบรนด์: {detail['brand']}\n"
                        f"🔢 SKU: {detail['sku']}\n"
                        f"💵 ราคา: {detail['selling_price']} (ปกติ {detail['srp_price']})\n"
                        f"🧾 การรับประกัน: {detail['warranty']}\n\n"
                        f"{detail['description'][:300]}...\n\n"
                        f"ดูรายละเอียดเพิ่มเติมได้ตามลิงค์ที่แนบด้านล่างครับ"
                    )

                    line_bot_api.reply_message(event.reply_token, [
                        TextSendMessage(text=message),
                        TextSendMessage(text=url)
                    ])
                else:
                    raise ValueError("ไม่พบ URL")
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"❌ เกิดข้อผิดพลาด: {e}\nพิมพ์ 'menu' เพื่อเริ่มใหม่")
                )
        else:
            # ดึงหมวดล่าสุดของ user (ถ้าไม่มีให้ default เป็น notebook)
            last_cat = user_context.get(event.source.user_id, {}).get("last_category", "notebook")

            # รองรับรูปแบบ "notebook acer", "smartphone samsung" เพื่อสลับหมวดแบบ inline
            lowered = user_input.lower()
            if lowered.startswith("notebook "):
                last_cat = "notebook"
                query = lowered.replace("notebook", "", 1).strip()
                user_context[event.source.user_id] = {"last_category": last_cat}
            elif lowered.startswith("smartphone "):
                last_cat = "smartphone"
                query = lowered.replace("smartphone", "", 1).strip()
                user_context[event.source.user_id] = {"last_category": last_cat}
            elif lowered.startswith("gaming "):  # เผื่อผู้ใช้พิมพ์ gaming, gaming gear ...
                last_cat = "gaming gear"
                query = lowered.replace("gaming", "", 1).replace("gear", "", 1).strip()
                user_context[event.source.user_id] = {"last_category": last_cat}
            else:
                query = user_input  # ใช้ข้อความทั้งหมดเป็นคำค้นในหมวดล่าสุด

            # ตรวจจับคำทักทายทั่วไป
            greetings = ["สวัสดี", "hello", "hi", "ดีจ้า", "หวัดดี", "ดีครับ", "ดีค่ะ"]
            if user_input.strip() in greetings:
                greet_text = (
                    "สวัสดีครับ 👋 ยินดีต้อนรับสู่ระบบแนะนำสินค้าไอที 💻📱🎮\n\n"
                    "คุณสามารถพิมพ์ชื่อสินค้าเพื่อค้นหาได้ เช่น:\n"
                    "- notebook acer\n"
                    "- smartphone samsung\n"
                    "- gaming gear logitech\n\n"
                    "หรือพิมพ์ `menu` เพื่อดูหมวดหมู่ทั้งหมดครับ 😊"
                )
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=greet_text))
                return

            # ตอบผลการค้นหาในหมวดล่าสุด
            reply_search_result(event, last_cat, query, limit=10)


if __name__ == "__main__":
    app.run(port=5000)