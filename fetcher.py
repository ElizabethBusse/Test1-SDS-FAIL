from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def setup_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(options=options)


def fetch_sds_sigma_aldrich(cas_number):
    driver = setup_driver()
    try:
        url = f"https://www.sigmaaldrich.com/US/en/search/{cas_number}"
        driver.get(url)
        time.sleep(2)  # Let the page load

        product_links = driver.find_elements(By.CSS_SELECTOR, "a[data-testid='product-card-link']")
        if product_links:
            product_links[0].click()
            time.sleep(2)
            sds_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Safety Data Sheet")
            sds_url = sds_link.get_attribute("href")
            print(f"Sigma-Aldrich SDS URL: {sds_url}")
            return sds_url
        else:
            print("No product found.")
            return None
    except Exception as e:
        print(f"Sigma-Aldrich Error: {e}")
        return None
    finally:
        driver.quit()