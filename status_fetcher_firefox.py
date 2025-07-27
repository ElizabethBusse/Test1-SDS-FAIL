# import tkinter as tk
# from tkinter import filedialog
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import requests
import tempfile
import streamlit as st

from webdriver_manager.firefox import GeckoDriverManager


from cameo_soup_nfpa import *
# from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver

# temp_dir = tempfile.TemporaryDirectory()
# selected_dir = temp_dir.name

import shutil

selected_dir = tempfile.mkdtemp(dir="/tmp")
def clean_temp_dir(path):
    try:
        shutil.rmtree(path)
    except Exception as e:
        print(f"Cleanup failed: {e}")

def get_remote_driver(options):
    return webdriver.Remote(
        command_executor="http://localhost:4444/wd/hub",
        options=options
    )

# from selenium.webdriver.firefox.service import Service
options = Options()

# service = Service(executable_path="/usr/local/bin/geckodriver")
# driver = webdriver.Firefox(service=service, options=options)

# Setup Firefox options and profile for headless download
options.set_capability("browserName", "firefox")
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument('--disable-dev-shm-usage')

options.set_preference("browser.download.folderList", 2)
options.set_preference("browser.download.dir", selected_dir or "/tmp")
# options.set_preference("browser.download.dir", selected_dir)
options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
options.set_preference("pdfjs.disabled", True)
options.set_preference("browser.download.manager.showWhenStarting", False)


from selenium.webdriver.firefox.service import Service

service = Service(GeckoDriverManager().install())
driver = webdriver.Firefox(
    options=options,
    service=service,
)


def fetch_sds_sigma_aldrich(cas_number, download_dir=None):
    # print("RUNNING ON STATUS FILE")
    with st.status("Searching on Sigma-Aldrich...", expanded=True) as status:
        try:
            # driver = webdriver.Firefox(options=options, executable_path=GeckoDriverManager().install())
            # driver = get_remote_driver(options)
            
            # driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
            st.write("Navigating to Sigma-Aldrich...")
            driver.get("https://www.sigmaaldrich.com")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "header-search-search-wrapper-input")))
            st.write("Homepage loaded")

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
            st.write("Waiting for download...")
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
            
            status.update(label="Download completed from Sigma-Aldrich", state="complete", expanded=False)

            return True

        except Exception as e:
            print(f"Sigma-Aldrich Error: {e}")
            status.update(label=f"Not found on Sigma-Aldrich {e}", state="error", expanded=False)
            return False
        finally:
            driver.quit()


def fetch_sds_aaron_chem(cas_number, download_dir=None):
    with st.status("Searching AaronChem...", expanded=True) as status:
        try:
            st.write("Navigating to Aaron Chemicals...")
            url = f"https://www.aaronchem.com/sds/{cas_number}.pdf"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.70 Safari/537.36"
            }
            response = requests.get(url, headers=headers, stream=True)

            if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
                save_path = os.path.join(download_dir or "/tmp", f"{cas_number}.pdf")
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                st.write(f"Downloaded SDS from AaronChem")
                status.update(label="Download completed from Aaron Chemicals", state="complete", expanded=False)
                return True
            else:
                st.write(f"No SDS found for CAS {cas_number} on AaronChem")
                status.update(label=f"Not found on Aaron Chem {e}", state="error", expanded=False)
                return False

        except Exception as e:
            print(f"AaronChem Error: {e}")
            return False


def fetch_nfpa_cameo(cas_number):
    with st.status(f"Searching Cameo for NFPA 704 rating ({cas_number})...", expanded=True) as status:
        try:
            # driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
            st.write("Navigating to Cameo Chemicals...")
            driver.get("https://cameochemicals.noaa.gov/search/simple")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@name='cas']")))
            st.write("Homepage loaded")

            search = driver.find_element(By.XPATH, "//input[@name='cas']")
            search.clear()
            search.send_keys(cas_number)
            time.sleep(0.5)
            search.send_keys(u'\ue007')

            st.write("Searching for NFPA table...")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.pseudo_button[href^="/chemical/"]')))

            links = driver.find_elements(By.CSS_SELECTOR, 'a.pseudo_button[href^="/chemical/"]')
            # print(len(links))

            nfpa_urls = [link.get_attribute("href") for link in links]
            # print("Collected NFPA URLs:", nfpa_urls)

            nfpa_results = []
            for url in nfpa_urls:
                result = extract_nfpa_704(url)
                nfpa_results.append(result)

            if not nfpa_results or nfpa_results == [{}]:
                status.update(label="No NFPA information found on Cameo", state="error", expanded=False)
                return None
            status.update(label="NFPA rating search completed", state="complete", expanded=False)
            return nfpa_results

        except Exception as e:
            # print(f"Cameo Chemicals Error: {e}")
            st.write(f"Cameo Chemicals Error: {e}")
            status.update(label=f"No NFPA information found on Cameo {e}", state="error", expanded=False)
            return None
        finally:
            driver.quit()


def compare_nfpa_results(results):
    # Filter out blank/None results
    filtered = [r for r in results if r and isinstance(r, dict) and r.get('Health')]

    if not filtered:
        return None

    # Compare the filtered results for consensus (ignoring blank)
    first = filtered[0]
    consensus = all(
        r['Health']['value_html'] == first['Health']['value_html'] and
        r['Flammability']['value_html'] == first['Flammability']['value_html'] and
        r['Instability']['value_html'] == first['Instability']['value_html'] and
        r['Special']['value_html'] == first['Special']['value_html']
        for r in filtered
    )

    consensus_result = first if consensus else filtered
    return consensus_result


# if __name__ == "__main__":
#     # fetch_sds_sigma_aldrich('64-19-7', '/Users/sophiezhou/Downloads/purdue/[10] summer 25/evonik/SDS GHS Extractor')
#     if selected_dir:
#         fetch_sds_sigma_aldrich('000-00-0', selected_dir)
#         # fetch_sds_aaron_chem('98327-87-8', selected_dir)
#     else:
#         print("No folder selected. Exiting.")