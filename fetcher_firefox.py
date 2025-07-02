import tkinter as tk
from tkinter import filedialog
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import requests

# for cas number lookup


# TODO: if no download SDS button, try on AaronChem
#           currently crashes program, need graceful way to switch to AC
#           AC has format of: aaronchem.com/sds/{cas}.pdf -> 404 error if not found


root = tk.Tk()
root.withdraw()
selected_dir = filedialog.askdirectory(title="Select folder to save SDS files")


# Setup Firefox options and profile for headless download
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

options.set_preference("browser.download.folderList", 2)
options.set_preference("browser.download.dir", selected_dir or "/tmp")
options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
options.set_preference("pdfjs.disabled", True)
options.set_preference("browser.download.manager.showWhenStarting", False)

driver = webdriver.Firefox(options=options)


def fetch_sds_sigma_aldrich(cas_number, download_dir=None):
    try:
        print("Navigating to Sigma-Aldrich...")
        driver.get("https://www.sigmaaldrich.com")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "header-search-search-wrapper-input")))
        print("Homepage loaded")

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
        print("Waiting for download...")
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


    except Exception as e:
        print(f"Sigma-Aldrich Error: {e}")
        return False
    finally:
        driver.quit()


def fetch_sds_aaron_chem(cas_number, download_dir=None):
    try:
        print("Navigating to Aaron-Chem...")
        url = f"https://www.aaronchem.com/sds/{cas_number}.pdf"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.70 Safari/537.36"
        }
        response = requests.get(url, headers=headers, stream=True)
        print(response.status_code)

        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            save_path = os.path.join(download_dir or "/tmp", f"{cas_number}.pdf")
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded SDS from AaronChem to: {save_path}")
            return True
        else:
            print(f"No SDS found for CAS {cas_number} on AaronChem (status {response.status_code})")
            return False

    except Exception as e:
        print(f"AaronChem Error: {e}")
        return False

if __name__ == "__main__":
    # fetch_sds_sigma_aldrich('64-19-7', '/Users/sophiezhou/Downloads/purdue/[10] summer 25/evonik/SDS GHS Extractor')
    if selected_dir:
        # fetch_sds_sigma_aldrich('1173021-65-2', selected_dir)
        fetch_sds_aaron_chem('98327-87-8', selected_dir)
    else:
        print("No folder selected. Exiting.")