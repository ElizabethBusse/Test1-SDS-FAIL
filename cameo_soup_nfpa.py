import requests
from bs4 import BeautifulSoup

def extract_nfpa_704(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    nfpa_data = {}

    rows = soup.find_all("td", class_="hazard")
    for row in rows:
        img = row.find("img")
        if not img or "alt" not in img.attrs:
            continue
        quadrant = img["alt"].strip()  # "Blue", "Red", "Yellow", "White"

        label_map = {
            "Blue": "Health",
            "Red": "Flammability",
            "Yellow": "Instability",
            "White": "Special"
        }
        label = label_map.get(quadrant, quadrant)

        value_cell = row.find_next_sibling("td", class_="value")
        value_html = str(value_cell.decode_contents()).strip()

        desc_cell = value_cell.find_next_sibling("td", class_="description")
        description = desc_cell.get_text(strip=True) if desc_cell else ""

        nfpa_data[label] = {
            "value_html": value_html,
            "description": description
        }

    return nfpa_data

if __name__ == "__main__":
    url = "https://cameochemicals.noaa.gov/chemical/9215"
    nfpa_info = extract_nfpa_704(url)
    print(nfpa_info)