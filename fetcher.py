import os
import glob
import requests

# TODO: headless download not working
#       user prompt for directory save location
#       if no download SDS button, try on AaronChem
#           currently crashes program, need graceful way to switch to AC
#           AC has format of: aaronchem.com/sds/{cas}.pdf -> 404 error if not found
#       figure out how to access this file to be used in parser.py (rename to cas number)

def fetch_sds_sigma_aldrich(cas_number, download_dir=None):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time

    options = Options()
    prefs = {
        "download.default_directory": download_dir or "/tmp",
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    # options.add_argument("--headless=new")  # Remove if you want to see browser
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options)

    try:

        driver.get("https://www.sigmaaldrich.com")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "header-search-search-wrapper-input")))

        # Type CAS and press Enter
        search = driver.find_element(By.ID, "header-search-search-wrapper-input")
        search.clear()
        search.send_keys(cas_number)
        time.sleep(0.5)
        search.send_keys(u'\ue007')

        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
            print("Cookie popup dismissed.")
        except:
            print("No cookie popup appeared.")
        
        # Generic click for any SDS download button
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[starts-with(@data-testid, 'sds-')]"))
        )
        button = driver.find_element(By.XPATH, "//button[starts-with(@data-testid, 'sds-')]")
        driver.execute_script("arguments[0].click();", button)

        link = driver.find_element(By.XPATH, "//a[@id='sds-link-EN']")
        link.click()

        # Wait for download to finish
        download_wait_time = 15  # seconds
        download_poll_interval = 2

        for _ in range(int(download_wait_time / download_poll_interval)):
            time.sleep(download_poll_interval)
            break
        

    except Exception as e:
        print(f"Sigma-Aldrich Error: {e}")
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    # fetch_sds_sigma_aldrich('123027-99-6', '/Users/sophiezhou/Downloads/purdue/[10] summer 25/evonik/SDS GHS Extractor') # aaronchem
    fetch_sds_sigma_aldrich('64-19-7', '/Users/sophiezhou/Downloads/purdue/[10] summer 25/evonik/SDS GHS Extractor') # sigma aldrich