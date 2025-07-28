import requests
from lxml import html
import os
from cameo_soup_nfpa import extract_nfpa_704
import tempfile
from bs4 import BeautifulSoup
import streamlit as st

selected_dir = tempfile.mkdtemp(dir="/tmp")

def get_cid_from_cas(cas_number):
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cas_number}/cids/JSON"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        try:
            return data['IdentifierList']['CID'][0]
        except KeyError:
            return None
    else:
        return None

def extract_sigma_link(cas_number):
    url = f"https://www.sigmaaldrich.com/US/en/search/{cas_number}?focus=products&page=1&perpage=30&sort=relevance&term={cas_number}&type=cas_number"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("Failed to fetch page (S-A CAS number search).")
        return None

    tree = html.fromstring(response.content)
    link = tree.xpath("//a[starts-with(@id, 'NAME-pdp-link-') and contains(@href, '/product/')]")
    if not link:
        print("No matching link found.")
        return None

    href = link[0].attrib['href']
    full_link = "https://www.sigmaaldrich.com" + href
    full_link = full_link.replace("/product/", "/sds/")
    full_link += "?userType=anonymous"
    return full_link
    

def fetch_sds_sigma_aldrich(cas_number, download_dir=None):
    with st.status("Searching on Sigma-Aldrich...", expanded=True) as status:
        try:
            url = extract_sigma_link(cas_number)
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.70 Safari/537.36"
            }
            response = requests.get(url, headers=headers, stream=True)

            if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
                save_path = os.path.join(download_dir or "/tmp", f"{cas_number}.pdf")
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Downloaded SDS for {cas_number} from SA")
                status.update(label="Download completed from Sigma-Aldrich", state="complete", expanded=False)
                return True
            else:
                print(f"No SDS found for CAS {cas_number} on SA")
                status.update(label=f"Not found on Sigma-Aldrich", state="error", expanded=False)
                return False

        except Exception as e:
            print(f"S-A Download Error: {e}")
            status.update(label=f"Not found on Sigma-Aldrich", state="error", expanded=False)
            return False
    

def fetch_sds_aaron_chem(cas_number, download_dir=None):
    with st.status("Searching AaronChem...", expanded=True) as status:
        try:
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
                status.update(label="Download completed from Aaron Chemicals", state="complete", expanded=False)
                return True
            else:
                status.update(label=f"Not found on Aaron Chem", state="error", expanded=False)
                return False

        except Exception as e:
            print(f"AaronChem Error: {e}")
            status.update(label=f"Not found on Aaron Chem", state="error", expanded=False)
            return False


# return list of full url
# from pubchem's references using cameochemicals.noaa.gov/chemicals/...
def get_cameo_links_from_pubchem(cas):
    cid = get_cid_from_cas(cas)
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed to fetch data for CID {cid}")
        return []

    data = response.json()
    record = data.get("Record", {})
    references = record.get("Reference", [])

    links = []
    for ref in references:
        if ref.get("SourceName") == "CAMEO Chemicals":
            href = ref.get("URL", "")
            if "cameochemicals.noaa.gov/chemical/" in href:
                links.append(href)

    # check links for correct cas no.
    verified_links = []
    for link in links:
        try:
            page = requests.get(link, headers={"User-Agent": "Mozilla/5.0"})
            if page.status_code == 200:
                soup = BeautifulSoup(page.content, "html.parser")
                cas_element = soup.select_one('td[headers="th-cas"]')
                if cas_element:
                    page_cas = cas_element.get_text(strip=True)
                    # print(f"Found CAS: {page_cas}")
                    if page_cas == cas:
                        verified_links.append(link)
                else:
                    print(f"CAS not found on {link}")
        except Exception as e:
            print(f"Error verifying {link}: {e}")

    return verified_links


# returns list of nfpa result dicts
def fetch_nfpa_cameo(cas_number):
    with st.status(f"Searching Cameo for NFPA 704 rating ({cas_number})...", expanded=True) as status:
        cameo_links = get_cameo_links_from_pubchem(cas_number)
        nfpa_results = []

        for url in cameo_links:
            result = extract_nfpa_704(url)
            nfpa_results.append(result)

        if not nfpa_results or nfpa_results == [{}]:
            status.update(label="No NFPA information found on Cameo", state="error", expanded=False)
            return None
        status.update(label="NFPA rating search completed", state="complete", expanded=False)
        return nfpa_results


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


if __name__ == "__main__":
    # cas_input = ["64-19-7", "3734-67-6", "68-12-2", "75-05-8", "108-20-3"]
    cas_input = "6484-52-2"
    # for cas in cas_input:
    #     fetch_sds_sigma_aldrich(cas_number=cas, download_dir="/Users/sophiezhou/Downloads/no_sel_test")
    results = fetch_nfpa_cameo(cas_input)
    consensus = compare_nfpa_results(results)
    print(consensus)