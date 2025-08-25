# -*- coding: utf-8 -*-
# Selenium script (fixed) for opening BNN category URLs, auto-accepting popups,
# waiting for product cards, and extracting product names robustly.
#
# ✅ Changes from previous version:
#   - Added close_popups() with "Allow/อนุญาต/Accept/ยอมรับ/ตกลง" selectors
#   - More robust wait_products() that tries multiple selectors
#   - Scroll each product card into view before reading text
#   - get_name(): multi-strategy extraction (title nodes -> img alt -> a[aria-label|title] -> JS innerText)
#   - Optional wait for title nodes presence to avoid empty texts

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
import time
import re

import csv
from pathlib import Path
from urllib.parse import urlparse

chromedriver_autoinstaller.install()

OUT_DIR = Path("bnn_links")
OUT_DIR.mkdir(exist_ok=True)

def get_url_from_card(el):
    # การ์ดบางใบเป็น <a> เอง บางใบมี <a> อยู่ข้างใน
    try:
        if el.tag_name.lower() == "a":
            href = el.get_attribute("href")
            if href:
                return ("https://www.bnn.in.th"+href) if href.startswith("/") else href
    except:
        pass
    try:
        a = el.find_element(By.CSS_SELECTOR, "a[href*='/th/p/']")
        href = a.get_attribute("href")
        if href:
            return ("https://www.bnn.in.th"+href) if href.startswith("/") else href
    except:
        pass
    # fallback ด้วย JS
    try:
        href = driver.execute_script(
            "const a=arguments[0].querySelector(\"a[href*='/th/p/']\"); return a?a.getAttribute('href'):null;", el
        )
        if href:
            return ("https://www.bnn.in.th"+href) if href.startswith("/") else href
    except:
        pass
    return None

CATEGORY_URLS = [
    "https://www.bnn.in.th/th/p/notebook?ref=search-result",
    "https://www.bnn.in.th/th/p/smartphone-and-accessories?ref=search-result",
    "https://www.bnn.in.th/th/p/gaming-gear?ref=search-result",
]

CATEGORY_NAMES = [
    "notebook",
    "smartphone-and-accessories",
    "gaming-gear",
]

driver = webdriver.Chrome()
wait = WebDriverWait(driver, 15)

BADGE_PAT = re.compile(r"(ประหยัด|฿|บาท|%|ผ่อน|ของแถม|แถม|ส่วนลด)", re.I)
def is_valid_name(s: str) -> bool:
    if not s:
        return False
    if BADGE_PAT.search(s):
        return False            # ตัด badge/ราคา/โปรฯ
    return len(s.strip()) >= 6   # กันข้อความสั้น ๆ ที่ไม่น่าใช่ชื่อ


def close_popups():
    """Try to click away popups/cookie banners/allow dialogs."""
    xpaths = [
        "//button[contains(.,'Allow')]",
        "//button[contains(.,'อนุญาต')]",
        "//button[contains(.,'Accept')]",
        "//button[contains(.,'ยอมรับ')]",
        "//button[contains(.,'ตกลง')]",
        "//*[@aria-label='close']",
        "//*[contains(@class,'close') and (self::button or self::div)]",
    ]
    for xp in xpaths:
        try:
            btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xp)))
            btn.click()
            time.sleep(0.2)
        except:
            pass

def wait_products():
    """Wait for any product card selector to appear; return the successful locator."""
    candidates = [
        (By.CSS_SELECTOR, '[data-testid*="product-card"]'),
        (By.CSS_SELECTOR, 'a[href*="/th/p/"][class*="product"]'),
        (By.CSS_SELECTOR, 'li a[href*="/th/p/"]'),
    ]
    for loc in candidates:
        try:
            wait.until(EC.presence_of_element_located(loc))
            return loc
        except:
            continue
    raise RuntimeError("ไม่พบการ์ดสินค้าในหน้า")

def get_name(el):
    # 0) ถ้า element เองคือ <a>
    try:
        if el.tag_name.lower() == "a":
            for attr in ["aria-label", "title", "data-name", "data-product-name"]:
                v = (el.get_attribute(attr) or "").strip()
                if is_valid_name(v): return v
            v = (el.get_attribute("innerText") or el.text or "").strip()
            if is_valid_name(v): return v
    except:
        pass

    # 1) ดึงจากลิงก์สินค้าภายในการ์ด
    try:
        a = el.find_element(By.CSS_SELECTOR, "a[href*='/th/p/']")
        for attr in ["aria-label", "title", "data-name", "data-product-name"]:
            v = (a.get_attribute(attr) or "").strip()
            if is_valid_name(v): return v
        v = (a.get_attribute("innerText") or a.text or "").strip()
        if is_valid_name(v): return v
    except:
        pass

    # 2) โหนด title ที่พบบ่อย
    for css in [
        "[data-testid*='title']",
        "[class*='title']",
        ".product-name", ".ProductName", ".name", ".product-title",
        "h3", "h2"
    ]:
        try:
            sub = el.find_element(By.CSS_SELECTOR, css)
            v = (sub.get_attribute("innerText") or sub.text or "").strip()
            if is_valid_name(v): return v
        except:
            pass

    # 3) alt ของรูป
    try:
        img = el.find_element(By.CSS_SELECTOR, "img")
        alt = (img.get_attribute("alt") or "").strip()
        if is_valid_name(alt): return alt
    except:
        pass

    # 4) Fallback: innerText ทั้งการ์ด แล้วคัดบรรทัดที่เข้าท่า
    try:
        txt = (driver.execute_script("return arguments[0].innerText || '';", el) or "").strip()
        for line in [x.strip() for x in txt.splitlines() if x.strip()]:
            if is_valid_name(line): return line
    except:
        pass

    return None


def get_url_from_card(el):
    # การ์ดบางใบเป็น <a> เอง บางใบมี <a> ข้างใน
    try:
        if el.tag_name.lower() == "a":
            href = el.get_attribute("href")
            if href:
                return ("https://www.bnn.in.th"+href) if href.startswith("/") else href
    except:
        pass
    try:
        a = el.find_element(By.CSS_SELECTOR, "a[href*='/th/p/']")
        href = a.get_attribute("href")
        if href:
            return ("https://www.bnn.in.th"+href) if href.startswith("/") else href
    except:
        pass
    # fallback ด้วย JS
    try:
        href = driver.execute_script(
            "const a=arguments[0].querySelector(\"a[href*='/th/p/']\"); return a?a.getAttribute('href'):null;", el
        )
        if href:
            return ("https://www.bnn.in.th"+href) if href.startswith("/") else href
    except:
        pass
    return None


def scrape_detail_in_new_tab(url):
    driver.execute_script("window.open(arguments[0], '_blank');", url)
    driver.switch_to.window(driver.window_handles[-1])
    try:
        close_popups()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".product-detail-summary"))
        )

        # ===== selectors ตาม DOM ที่ส่งมา =====
        title = get_text_safe(driver, [
            "h1.page-title.product-name"
        ])
        brand = get_text_safe(driver, [
            ".brand .brand-value"           # ex: ASUS
        ])
        sku = get_text_safe(driver, [
            ".sku-number .sku-number-value" # ex: 4711387786024
        ])

        # คำอธิบายสั้น: <div class="product-short-description html-content"> ... <p> ... <ul><li>...
        short_p = get_text_safe(driver, [
            ".product-short-description.html-content > p"
        ])
        bullets = get_all_list_items(driver, ".product-short-description.html-content ul li")

        return {
            "url": url,
            "title": title,
            "brand": brand,
            "sku": sku,
            "short_description": short_p,
            "bullets": bullets,  # ตัวอย่าง: ['CPU: ...', 'Graphics: ...', ...]
        }
    finally:
        driver.close()
        driver.switch_to.window(driver.window_handles[0])


def get_text_safe(driver, css_list):
    for css in css_list:
        try:
            el = driver.find_element(By.CSS_SELECTOR, css)
            txt = el.get_attribute("innerText") or el.text
            if txt and txt.strip():
                return txt.strip()
        except:
            pass
    return None

def get_all_list_items(driver, css):
    items = []
    for li in driver.find_elements(By.CSS_SELECTOR, css):
        try:
            t = li.get_attribute("innerText") or li.text
            t = (t or "").strip()
            if t:
                items.append(t)
        except:
            pass
    return items

# เติมชื่อให้รายการที่ชื่อยังว่าง ด้วยการเข้าไปหน้า detail (เฉพาะตัวที่ว่าง)
def fill_missing_names_from_detail(rows):
    for r in rows:
        if r.get("name"):  # ข้ามตัวที่มีชื่อแล้ว
            continue
        url = r.get("url")
        if not url:
            continue
        try:
            driver.execute_script("window.open(arguments[0], '_blank');", url)
            driver.switch_to.window(driver.window_handles[-1])
            close_popups()
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.page-title.product-name, .product-detail-summary h1"))
            )
            h1 = driver.find_element(By.CSS_SELECTOR, "h1.page-title.product-name, .product-detail-summary h1")
            title = (h1.get_attribute("innerText") or h1.text or "").strip()
            if title:
                r["name"] = title
        except Exception as e:
            # พลาดก็ข้ามไป ไม่ให้ล้มทั้งชุด
            pass
        finally:
            try:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except:
                pass

try:
    for url, cat in zip(CATEGORY_URLS, CATEGORY_NAMES):
        print(f"\n➡️ เปิดหมวด: {url}")
        driver.get(url)
        close_popups()

        # Optional: wait until any title node exists to reduce empty reads
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h3, [class*='title'], [data-testid*='title']"))
            )
        except:
            pass

        locator = wait_products()
        close_popups()

        cards = driver.find_elements(*locator)
        print(f"✅ สินค้าพบแล้ว: {len(cards)} รายการ")

        # === สร้าง rows ทั้งหน้าปัจจุบัน ===
        rows_all = []
        for el in cards[:25]:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.1)
                name = get_name(el)              # อาจว่างได้บางใบ ไม่เป็นไร
                url_item = get_url_from_card(el) # ต้องมี URL
                if url_item:
                    rows_all.append({"name": name, "url": url_item})
            except:
                pass
        
        fill_missing_names_from_detail(rows_all)

        # === พิมพ์ตัวอย่าง 10 รายการ (ชื่อ + ลิงก์) ===
        samples = [r for r in rows_all if r.get("name")]
        print(f"🧾 ตัวอย่างสินค้า {min(10, len(samples))} ชิ้นแรก (พร้อมลิงก์):")
        for r in samples[:10]:
            print(f"  - {r['name']} — {r['url']}")

        out_path = OUT_DIR / f"{cat}.csv"

        # กันซ้ำภายในรอบรันนี้ (ตาม url)
        seen = set()
        dedup_rows = []
        for r in rows_all:
            if r["url"] not in seen:
                seen.add(r["url"])
                dedup_rows.append(r)

        # เขียนไฟล์ (append แบบมี header ครั้งแรก)
        is_new = not out_path.exists()
        with out_path.open("a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["name", "url"])
            if is_new:
                w.writeheader()
            w.writerows(dedup_rows)

        print(f"💾 บันทึก {len(dedup_rows)} แถว -> {out_path}")

        
        # pairs = [(name, href), ...] ได้จากหน้าลิสต์เหมือนเดิม
        # details = []
        # for nm, href in pairs:
        #     try:
        #         info = scrape_detail_in_new_tab(href)
        #         details.append(info)
        #         print(f"✅ {nm} -> SKU={info.get('sku')}, BRAND={info.get('brand')}")
        #     except Exception as e:
        #         print("❌ detail fail:", nm, e)

        # # ดูตัวอย่างผลลัพธ์ 1 ชิ้น
        # if details:
        #     d0 = details[0]
        #     print("\n🔎 sample detail:")
        #     print("title:", d0["title"])
        #     print("brand:", d0["brand"])
        #     print("sku:", d0["sku"])
        #     print("short_description:", d0["short_description"])
        #     print("bullets:", d0["bullets"])


finally:
    driver.quit()


