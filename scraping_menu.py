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

chromedriver_autoinstaller.install()

CATEGORY_URLS = [
    "https://www.bnn.in.th/th/p/notebook?ref=search-result",
    # "https://www.bnn.in.th/th/p/smartphone-and-accessories?ref=search-result",
    # "https://www.bnn.in.th/th/p/gaming-gear?ref=search-result",
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
    # 0) ดึงจากลิงก์สินค้าหลัก (มักมี aria-label/title ที่เป็นชื่อจริง)
    try:
        a = el.find_element(By.CSS_SELECTOR, "a[href*='/th/p/']")
        for attr in ["aria-label", "title"]:
            v = (a.get_attribute(attr) or "").strip()
            if is_valid_name(v):
                return v
        # ถ้าในลิงก์มี h3/หัวข้อ
        try:
            t = a.find_element(By.CSS_SELECTOR, "h3, [class*='title']")
            v = t.text.strip()
            if is_valid_name(v):
                return v
        except:
            pass
    except:
        pass

    # 1) โหนด title ทั่วไป (เผื่อ DOM เปลี่ยน)
    for css in ['[data-testid*="title"]', '[class*="title"]', 'h3', 'h2', '.name', '.product-name']:
        try:
            sub = el.find_element(By.CSS_SELECTOR, css)
            v = sub.text.strip()
            if is_valid_name(v):
                return v
        except:
            pass

    # 2) alt ของภาพ (บางทีเป็นชื่อเต็ม)
    try:
        img = el.find_element(By.CSS_SELECTOR, "img")
        alt = (img.get_attribute("alt") or "").strip()
        if is_valid_name(alt):
            return alt
    except:
        pass

    # 3) Fallback: innerText ทั้งการ์ด แล้วกรองบรรทัดที่ดูเป็นชื่อ
    try:
        txt = (driver.execute_script("return arguments[0].innerText || '';", el) or "").strip()
        for line in [x.strip() for x in txt.splitlines()]:
            if is_valid_name(line):
                return line
    except:
        pass
    return None


try:
    for url in CATEGORY_URLS:
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

        # Show first 10 names as a sanity check
        names = []
        want = 10
        # ดูการ์ดเผื่อไว้ 30 ใบแรก (เผื่อมีการ์ดที่ไม่ใช่สินค้า/ชื่อยังไม่ขึ้น)
        for el in cards[:30]:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.3)  # รอให้ virtualized DOM เรนเดอร์ชื่อ
                nm = get_name(el)
                if nm:
                    names.append(nm)
                    if len(names) == want:
                        break
            except:
                pass

        print(f"🧾 ตัวอย่างชื่อสินค้า {len(names)} ชิ้นแรก:")
        for n in names:
            print("  -", n)

finally:
    driver.quit()
