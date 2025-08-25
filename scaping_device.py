from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller

chromedriver_autoinstaller.install()

chrome_options = Options()
chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
driver = webdriver.Chrome(options=chrome_options)

driver.get("https://www.bnn.in.th/th")

# อ่าน log จาก network
logs = driver.get_log("performance")

for entry in logs:
    msg = entry["message"]
    if '"Network.responseReceived"' in msg and 'https://www.bnn.in.th/th' in msg:
        import json
        j = json.loads(msg)
        status = j["message"]["params"]["response"]["status"]
        print("Status Code:", status)
        break
