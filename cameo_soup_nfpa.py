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
        value_html_raw = str(value_cell.decode_contents()).strip()

        if label == "Special":
            value_soup = BeautifulSoup(value_html_raw, "html.parser")
            strike_tag = value_soup.find("strike")

            # Only capture 'W', not any following text
            if strike_tag:
                value_html = "<strike>W</strike>"
            else:
                text = value_soup.get_text(strip=True)
                value_html = None if not text else text[0]

            # Extract description
            desc_tag = value_soup.find("td", class_="description")
            if not desc_tag:
                parent_tr = row.find_parent("tr")
                desc_tag = parent_tr.find("td", class_="description") if parent_tr else None
            description = desc_tag.get_text(strip=True) if desc_tag else None
        else:
            value_html = value_html_raw
            desc_cell = row.find_next_sibling("td", class_="description")
            description = desc_cell.get_text(strip=True) if desc_cell else ""

        nfpa_data[label] = {
            "value_html": value_html,
            "description": description
        }

    return nfpa_data

if __name__ == "__main__":
    url = "https://cameochemicals.noaa.gov/chemical/2284"
    nfpa_info = extract_nfpa_704(url)
    print(nfpa_info)