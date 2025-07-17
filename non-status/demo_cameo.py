from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from cameo_soup_nfpa import *

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

options.set_preference("browser.download.folderList", 2)
options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
options.set_preference("pdfjs.disabled", True)
options.set_preference("browser.download.manager.showWhenStarting", False)

def fetch_nfpa_cameo(cas_number):
    try:
        driver = webdriver.Firefox(options=options)
        print("Navigating to Cameo Chemicals...")
        driver.get("https://cameochemicals.noaa.gov/search/simple")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@name='cas']")))
        print("Homepage loaded")

        search = driver.find_element(By.XPATH, "//input[@name='cas']")
        search.clear()
        search.send_keys(cas_number)
        time.sleep(0.5)
        search.send_keys(u'\ue007')

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.pseudo_button[href^="/chemical/"]')))

        links = driver.find_elements(By.CSS_SELECTOR, 'a.pseudo_button[href^="/chemical/"]')
        # print(len(links))

        nfpa_urls = [link.get_attribute("href") for link in links]
        # print("Collected NFPA URLs:", nfpa_urls)

        nfpa_results = []
        for url in nfpa_urls:
            result = extract_nfpa_704(url)
            nfpa_results.append(result)

        # print(nfpa_results)
        return (nfpa_results)

    except Exception as e:
        print(f"Cameo Chemicals Error: {e}")
    finally:
        driver.quit()


def compare_nfpa_results(results):
    categories = ["Health", "Flammability", "Instability", "Special"]

    consensus_result = {}

    for category in categories:
        values = []
        descriptions = []
        full_entries = []

        for result in results:
            entry = result.get(category, {})
            value = entry.get("value_html", "").strip()
            desc = entry.get("description", "").strip()
            if value or desc:
                values.append(value)
                descriptions.append(desc)
                full_entries.append(entry)

        print(f"{category}")

        if not values:
            print("- All blank (no data for this category in any result)\n")
            if category == "Special":
                consensus_result["Special"] = {
                    "value_html": None,
                    "description": None
                }
            continue

        all_values_same = all(v == values[0] for v in values)
        all_desc_same = all(d == descriptions[0] for d in descriptions)

        if all_values_same and all_desc_same:
            print(f"- All match: {values[0]} - {descriptions[0]}\n")
            consensus_result[category] = {
                "value_html": values[0],
                "description": descriptions[0]
            }
        else:
            print("- Mismatch:")
            for i, (v, d) in enumerate(zip(values, descriptions)):
                print(f"- Chem {i}: {v} - {d}")
            print()

    if "Special" not in consensus_result:
        consensus_result["Special"] = {
            "value_html": None,
            "description": None
        }

    return consensus_result



if __name__ == "__main__":
    res = fetch_nfpa_cameo("64-19-7")
    consensus = compare_nfpa_results(res)
    print("\n\n FINAL: ",consensus)