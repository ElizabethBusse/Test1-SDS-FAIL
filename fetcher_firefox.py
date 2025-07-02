from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

def fetch_sds_sigma_aldrich(cas_number, download_dir=None):
    # Setup Firefox options and profile for headless download
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", download_dir or "/tmp")
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
    options.set_preference("pdfjs.disabled", True)
    options.set_preference("browser.download.manager.showWhenStarting", False)

    driver = webdriver.Firefox(options=options)

    try:
        print("🌐 Navigating to Sigma-Aldrich...")
        driver.get("https://www.sigmaaldrich.com")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "header-search-search-wrapper-input")))
        print("✅ Homepage loaded")

        # Enter CAS number and press Enter
        search = driver.find_element(By.ID, "header-search-search-wrapper-input")
        search.clear()
        search.send_keys(cas_number)
        time.sleep(0.5)
        search.send_keys(u'\ue007')  # Press Enter

        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
            print("🍪 Cookie popup dismissed.")
        except:
            print("🍪 No cookie popup appeared.")

        # Wait for SDS button and click
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[starts-with(@data-testid, 'sds-')]"))
        )
        button = driver.find_element(By.XPATH, "//button[starts-with(@data-testid, 'sds-')]")
        driver.execute_script("arguments[0].click();", button)

        # Click actual SDS PDF link
        link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@id='sds-link-EN']"))
        )
        link.click()

        # Wait for download to complete (basic wait)
        download_wait_time = 3  # seconds
        print("⬇️ Waiting for download...")
        time.sleep(download_wait_time)

    except Exception as e:
        print(f"❌ Sigma-Aldrich Error: {e}")
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    fetch_sds_sigma_aldrich(
        '64-19-7',
        '/Users/sophiezhou/Downloads/purdue/[10] summer 25/evonik/SDS GHS Extractor'
    )