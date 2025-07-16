# two options: SDS upload or CAS search
# collect all data that will be displayed onto streamlit UI

from parser import streamlit_pdf_upload
from test_parser import run_parser
import tempfile
from selenium.webdriver.firefox.options import Options
from test_cas_upload import search_by_cas

def sds_upload(pdf_file):
    text = streamlit_pdf_upload(pdf_file)
    results = run_parser(input_val=text)
    return results

def cas_reader(cas_list):
    temp_dir = tempfile.TemporaryDirectory()
    selected_dir = temp_dir.name

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", selected_dir or "/tmp")
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
    options.set_preference("pdfjs.disabled", True)
    options.set_preference("browser.download.manager.showWhenStarting", False)

    results = search_by_cas(cas_list)
    return results

if __name__ == "__main__":
    cas_list = ['64-19-7', '1015484-22-6', '000-00-0']
    temp_dir = tempfile.TemporaryDirectory()
    selected_dir = temp_dir.name
    search_by_cas(cas_list)