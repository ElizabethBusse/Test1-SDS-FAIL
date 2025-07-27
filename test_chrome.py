from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.support.ui import WebDriverWait
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def get_driver():
    return webdriver.Chrome(
        service=Service(
            ChromeDriverManager().install()  # Automatically detects your browser version
        ),
        options=options,
    )

options = Options()
options.add_argument("--disable-gpu")
# options.add_argument("--headless")

driver = get_driver()

def fetch_sds_sigma_aldrich(cas_number, download_dir=None):
    # print("RUNNING ON STATUS FILE")
    try:
        # driver = webdriver.Firefox(options=options, executable_path=GeckoDriverManager().install())
        # driver = get_remote_driver(options)
        
        # driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
        driver.get("https://www.sigmaaldrich.com")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "header-search-search-wrapper-input")))

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
            print("Cookie popup dismissed.")
        except:
            print("No cookie popup appeared.")

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
        time.sleep(download_wait_time)

        # Rename the most recently downloaded PDF to the CAS number
        pdf_files = [f for f in os.listdir(download_dir) if f.endswith(".pdf")]
        if pdf_files:
            latest_pdf = max(
                [os.path.join(download_dir, f) for f in pdf_files],
                key=os.path.getmtime
            )
            new_path = os.path.join(download_dir, f"{cas_number}.pdf")
            os.rename(latest_pdf, new_path)
            print(f"Renamed {os.path.basename(latest_pdf)} to {cas_number}.pdf")
        

        return True

    except Exception as e:
        print(f"Sigma-Aldrich Error: {e}")
        return False
    finally:
        driver.quit()


fetch_sds_sigma_aldrich("64-19-7")