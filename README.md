
# Safety Data Sheet Parser
[sdsreader.streamlit.app]()  
Takes a while to load on first startup, please be patient :)  
<img width="1170" height="756" alt="image" src="https://github.com/user-attachments/assets/9c3210c7-a554-49e3-b386-f148462b8032" />

Note: parser **specified for Millipore-Sigma and AaronChem**, may not be accurate for other SDS sources
###
Parse SDS files for:  
- CAS number
- PubChem CID
- Name (from SDS and NIST) 
- Hazard Statements (HXXX)
- GHS Category 1 Hazards (Physical, Health, Environmental)
- Other Hazards (Section 2 SDS)
- NPFA Rating (CameoChemicals or PubChem)
- Flash Point, Appearance, Odor (Section 9 SDS)
- Storage Condition (Section 7 SDS)
- Reactivity Information (Section 10 SDS)
###
Built for EHS @ Evonik Industries  
Sources for SDS: Millipore-Sigma (all), Aaron Chemicals  
Additional sources for cross reference: NIST, PubChem, CameoChemicals
#

### App Flow
```
sds-ghs-extractor
│
├── PDF Upload
│   └── home_page.py
|   └── streamlit_pdf_conv.py
|       └── sds_upload
|   └── test_parser.py
|       └── run_parser
|   └── parser.py
|       └── parse_sds_file
│
├── CAS Input
│   └── home_page.py
|   └── streamlit_pdf_conv.py
|       └── cas_reader
|   └── test_cas_upload.py
|       └── search_by_cas
|   └── status_test_fetcher.py
|   └── test_no_selenium.py
|       └── fetch_sds_sigma_aldrich
|       └── fetch_sds_aaron_chem
|   └── test_parser.py
|       └── run_parser
|   └── parser.py
|       └── parse_sds_file
│   
└── README.md
```
#
### Tech Stack
**Core**  
*Language*: Python 3.11+  
*PDF Parsing*: PyMuPDF (fitz)  
*HTML Parsing / Web Scraping*: BeautifulSoup4, requests  
*Regex & Fuzzy Logic*: re, fuzzywuzzy
  
**UI**  
*Web Interface*: Streamlit  
  
**Data Sources**  
*SDS*: Millipore-Sigma, Aaron Chemicals  
*Chemical Data*: PubChem, CameoChemicals, NIST  
*Hazard Statement Reference*: [https://pubchem.ncbi.nlm.nih.gov/ghs/](), stored locally (ghs_annex1_pubchem.json)  
*CAS Validation*: [https://www.cas.org/training/documentation/chemical-substances/checkdig]()
#
### Parsing Logic  
```
CAS Number: 
parser.py/extract_best_guess_cas

- looks for valid cas pattern: (2-7 digits)-(2 digits)-(1 digit)
    - high confidence: found near a "CAS" tag
    - low confidence: found anywhere else in SDS, only used if high confidence CAS not found
- checks validity of cas number using check digit system, source linked in CAS Validation above
```

```
CID: 
parser.py/get_cid_from_cas

- used for cross-referencing with PubChem & finding CameoChemicals links for NFPA rating 
  (described below in NFPA Rating)
- https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cas_number}/cids/JSON
    - looks for CID in IdentifierList by cas_number
```

```
Product Name: 
parser.py/extract_product_name
nist_name.py/get_nist_names

- looks between section 1 & 2 of SDS for keyword "Product name"
- https://webbook.nist.gov/cgi/cbook.cgi?ID={cas}&Units=SI
    - looks for name by cas
```

```
Hazard Statements:
parser.py/extract_ghs_statements
parser.py/get_pubchem_ghs_by_cas
haz_comp_full.py/get_pubchem_ghs_phrases

- looks between section 2 & 3 of SDS for keyword "Hazard Statements"
- looks for HXXX pattern (including HXXX + HXXX + ...)
- matches the text after HXXX to ghs_annex1_pubchem.json 
  (source linked in Hazard Statement Reference above)

- cross references with hazards statements present on a chemical's PubChem page
- https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON
    - safety and hazards -> hazards identification -> ghs classification -> ghs hazard statements
    - lookup by cid
```

```
GHS Category 1:
parser.py/ghs_category_1

- looks between section 2 & 3
- looks between keywords: "GHS classification in accordance with..." and "Label elements, including precautinary statements"
- looks for pattern of "Category" or "Sub category" followed by 1
- references list of all possible physical, health, and environmental hazards to match official hazard name
```

```
Other Hazards
parser.py/other_hazards

- looks between section 2 & 3
- looks between keywords: "Hazards not otherwise classified..." and "GHS label elements..."
- takes all text in between this
```

```
NFPA Rating:
test_no_selenium.py/fetch_nfpa_cameo
  - test_no_selenium.py/get_cameo_links_from_pubchem
test_no_selenium.py/compare_nfpa_results
pub_nfpa.py/extract_nfpa_hazard

- searches PubChem for CameoChemicals webpages links (CameoChemicals is loaded dynamically using JS to find pages for a 
CAS number; to avoid using headless browsing/improve speed, used workaround to find list of some/most of the Cameo pages 
for a CAS through PubChem)
- finds CID from CAS number, then uses PUGREST API from PubChem to find all cited resources, specifically ones for a cameo webpage 
(cameochemicals.noaa.gov/chemical/...)
- checks all cameo pages for CAS number and makes sure it matches
- from matches, it saves NFPA rating and Cameo's name
- if multiple matches for one CAS, this app displays/exports all unique with their name from Cameo
  - first checks if they are unique, if they're the same they are combined into one result
- if no Cameo pages for NFPA rating, searches on PubChem
```

```
Flash Point/Appearance/Odor:
- section 9 SDS
```

```
Storage Condition:
- section 7 SDS
```

```
Reactivity
- section 10 SDS
```
