import csv
import random
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path

# ---------------- CONFIG ----------------
csv_filenames = ['bnn_links\\notebook.csv',
                 'bnn_links\smartphone-and-accessories.csv',
                 'bnn_links\gaming-gear.csv'
                 ]  # เปลี่ยน \\ เป็น / เพื่อ cross-platform
output_dir = Path("bnn_details_json")
output_dir.mkdir(exist_ok=True)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36"
}
# ----------------------------------------


def scrape_product_detail(url: str) -> dict:
    """ดึงข้อมูลจาก product page (รวมทั้งใน summary และนอก summary)"""
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(resp.text, "html.parser")
        summary = soup.select_one("div.product-detail-summary")

        # ========== TITLE, BRAND, SKU, DESCRIPTION ==========
        title = soup.select_one("h1.product-name")  # ดึงจาก soup โดยตรง
        brand = soup.select_one(".brand-value")
        sku = soup.select_one(".sku-number-value")
        desc = soup.select_one(".product-short-description p")

        # ========== SPEC LIST ==========
        specs = {}
        for li in soup.select(".product-short-description li"):
            text = li.get_text(" ", strip=True)
            if ":" in text:
                key, value = text.split(":", 1)
                specs[key.strip()] = value.strip()
            else:
                specs[text] = None

        # ========== PROMOTION LABEL ==========
        labels = []
        for img in soup.select(".product-label-container img"):
            alt = img.get("alt")
            if alt:
                labels.append(alt.strip())

        # ========== IMAGE ==========
        image_urls = []
        for img_tag in soup.select('.gallery-thumbs img'):
            src = img_tag.get("src")
            if src and src.startswith("http"):
                image_urls.append(src.strip())

        # ========== PRICE ==========
        price_container = soup.select_one(".product-price-container")
        if not price_container and summary:
            price_container = summary.select_one(".product-price-container")  # fallback

        if price_container:
            selling_price_tag = price_container.select_one(".selling-price")
            srp_price_tag = price_container.select_one(".srp-price")
            selling_price = selling_price_tag.get_text(strip=True) if selling_price_tag else ""
            srp_price = srp_price_tag.get_text(strip=True) if srp_price_tag else ""
        else:
            selling_price = ""
            srp_price = ""

        # ========== WARRANTY ==========
        warranty_tag = soup.select_one(".product-warranty .caption")
        warranty = warranty_tag.get_text(strip=True) if warranty_tag else ""

        return {
            "title": title.get_text(strip=True) if title else "",
            "brand": brand.get_text(strip=True) if brand else "",
            "sku": sku.get_text(strip=True) if sku else "",
            "description": desc.get_text(" ", strip=True) if desc else "",
            "specs": specs,
            "labels": labels,
            "imageUrl": image_urls[0] if image_urls else "",
            "gallery": image_urls,
            "selling_price": selling_price,
            "srp_price": srp_price,
            "warranty": warranty
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------- START ----------------

for csv_filename in csv_filenames:
    category_name = Path(csv_filename).stem  # เช่น notebook
    output_file = output_dir / f"{category_name}_details.json"

    print(f"\n📂 เริ่มดึงข้อมูลจาก: {csv_filename}")
    all_results = []

    # อ่านไฟล์ CSV
    with open(csv_filename, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

        # สุ่ม 10 รายการ (ถ้าน้อยกว่า 10 ก็ใช้ทั้งหมด)
        # sample_size = min(10, len(rows))
        # sampled_rows = random.sample(rows, sample_size)

        for i, row in enumerate(rows, 1):
            name = row.get('name', '').strip()
            url = row.get('url', '').strip()

            # print(f'{i}. 📦 รุ่น: {name}')
            # print(f'   🔗 ลิงก์: {url}')

            detail = scrape_product_detail(url)
            detail["source_name"] = name
            detail["url"] = url

            all_results.append(detail)
            print(f'   ✅ ดึงข้อมูลสำเร็จแล้ว ({len(detail.keys())} ฟิลด์)')
            print('-' * 60)

    # บันทึก JSON
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"✅ บันทึกไฟล์เรียบร้อย: {output_file}")
