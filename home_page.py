import streamlit as st
from parser import is_valid_cas
from streamlit_pdf_conv import sds_upload, cas_reader
import re

# Configure page settings
# st.set_page_config(
#     page_title="SDS GHS Extractor",
#     page_icon="🧪",
#     layout="centered",
#     initial_sidebar_state="collapsed"
# )

if 'submitted' not in st.session_state:
    st.session_state.submitted = False

if 'input' not in st.session_state:
    st.session_state.input = None

if not st.session_state.submitted:
    invalid = False
    if "show_data_editor" not in st.session_state:
        st.session_state.show_data_editor = False

    st.header("Safety Data Sheet GHS Extractor")

    with st.form("all_data"):
        col1, col2 = st.columns(2)
        with col1:
            st.write("Upload SDS Files")
            uploaded_pdfs = st.file_uploader("file_upload", type="pdf", accept_multiple_files=True, label_visibility="collapsed", key="uploaded")

        with col2:
            st.write("CAS Input")
            container = st.container(border=True, height=135)
            with container:
                container.write('Type in CAS numbers')
                container.caption("")
                pressed = st.form_submit_button("Input", use_container_width=False)
            if pressed:
                st.session_state.show_data_editor = not st.session_state.show_data_editor
            if st.session_state.show_data_editor:
                data = st.data_editor(use_container_width = True, data = {"CAS Number": [""]}, num_rows="dynamic", key="inputs")
                if data:
                    # print(data)
                    invalid_rows = []
                    for i, row in enumerate(data["CAS Number"]):
                        row = str(row)
                        if row == "":
                            continue
                        if not is_valid_cas(row):
                            invalid_rows.append((i, row))
                    if invalid_rows:
                        invalid = True
                        st.error(f"Invalid CAS Number(s): {', '.join(row for _, row in invalid_rows)}")
                    else:
                        invalid = False

        pressed = st.form_submit_button("Submit", type="primary")

    st.caption("Specified for Millipore-Sigma and AaronChem")

    if pressed:
        if invalid:
            pass
        else:
            if 'inputs' in st.session_state:
                print(st.session_state.inputs)
            st.session_state.submitted = True
            st.rerun()
            pass



def nfpa_design(nfpa, expander1):
    # col1, col2 = expander1.columns([2,13])
    # expander1.write(f"Name: {nfpa["name"]}")
    expander1.write(f"Name: {nfpa['name']}")
    # col2.badge(nfpa["name"], color="gray")

    col1, col2, col3 = expander1.columns([3,1,16])
    col1.badge("Health", color="blue")
    col2.badge(nfpa["Health"]["value_html"], color="gray")
    col3.write(nfpa["Health"]["description"])

    col1, col2, col3 = expander1.columns([3,1,16])
    col1.badge("Flammability", color="red")
    col2.badge(nfpa["Flammability"]["value_html"], color="gray")
    col3.write(nfpa["Flammability"]["description"])

    col1, col2, col3 = expander1.columns([3,1,16])
    col1.badge("Instability", color="orange")
    col2.badge(nfpa["Instability"]["value_html"], color="gray")
    col3.write(nfpa["Instability"]["description"])

    col1, col2, col3 = expander1.columns([3,1,16])
    col1.badge("Specific", color='gray')
    if nfpa["Special"]["description"] == "":
        col3.write(None)
    else:
        col3.write(nfpa["Special"]["description"])
    if nfpa["Special"]["value_html"] is not None:
        if "w" in nfpa["Special"]["value_html"].lower():
            col2.badge("~~W~~", color="gray")
        else:
            col2.badge(nfpa["Special"]["value_html"], color="gray")


def page_design(results, show_all=False):
    with st.container():
        cas_number = results.get("cas_number", "None")
        expander1 = st.expander(f"{cas_number}", expanded=show_all)

        extra = results.get("additional_cas", "None")
        if extra:
            expander1.badge(f"Multiple CAS found on SDS PDF ({results.get("chemical_name")})", icon='⚠️', color="orange")

        expander1.write(f"**CAS Number**: {cas_number}")

        cid = results.get("cid", "None")
        expander1.write(f"**CID**: {cid}")

        expander1.divider()
        col1, col2 = expander1.columns([13,1])
        with col1:
            col1.write("**Name**")
            sds_name = results.get("chemical_name", "None")
            if sds_name:
                col1.badge(sds_name, color="primary")


            pubnames = results.get("pubchem_name", "None")
            if pubnames:
                if isinstance(pubnames, list):
                    def strip_html_tags(text):
                        return re.sub(r"<.*?>", "", text)

                    clean_names = [strip_html_tags(name) for name in pubnames]
                    unique_names = list(dict.fromkeys(clean_names))

                    for name in unique_names[:5]:
                        if len(name) <= 50:
                            col1.badge(f"{name}", color="gray")
                        else:
                            pass
                else:
                    col1.badge(f"{pubnames}", color="gray")

            if not pubnames and not sds_name:
                col1.write(None)
        with col2:
            if pubnames:
                st.badge("", icon=":material/check:", color="green")


        expander1.divider()
        expander1.write("**Hazard Statements**")
        ghs = results.get("ghs_from_sds", "None")
        if not ghs:
            expander1.write(None)
        else:
            for item in ghs:
                col1, col2, col3 = expander1.columns([3,10,1])

                code = item.get("ghs_code", "")
                original_text = item.get("original_text", "")
                if original_text is not None:
                    cleaned_text = re.sub(r'^(H\d{3}(?:\s*\+\s*H\d{3})*)\s*[:\-]?\s*', '', original_text).strip()
                col2.write(cleaned_text)
                col1.badge(f"{code}", color="gray")

                comparison = results.get("comparison", {})
                confirmed = comparison.get("confirmed", [])

                if code in confirmed:
                    col3.badge("", icon=":material/check:", color="green")

        
        expander1.divider()
        expander1.write("**GHS Category 1**")
        cat1 = results.get("ghs_categories", "None")
        if not cat1:
            expander1.write(None)
        else:
            for item in cat1:
                col1, col2 = expander1.columns([1,13])
                text = item.get("ghs_name_match", "")
                cat = item.get("category", "")
                col1.badge(cat, color="gray")
                col2.write(text)

        
        expander1.divider()
        expander1.write("**Other Hazards**")
        haz = results.get("other_hazards", "None")
        if not haz:
            expander1.write(None)
        else:
            for val in haz:
                expander1.write(val)


        expander1.divider()
        nfpa = results.get("nfpa")
        expander1.write("**NFPA Rating**")
        # expander1.write(nfpa)
        if nfpa is not None:
            num_nfpa = int(len(nfpa) / 4)

            col1, col2, col3 = expander1.columns([3,1,16])

            if num_nfpa == 1:
                nfpa_design(nfpa, expander1)

            else:
                expander1.badge(f"Found {len(nfpa)} matches for the NFPA Rating", color="orange", icon="⚠️")
                expander1.write("")

                for rating in nfpa:
                    nfpa_design(rating, expander1)
                    if rating != nfpa[-1]:
                        expander1.divider()
        else:
            expander1.write(None)


        expander1.divider()
        flash = results.get("flash_point")
        expander1.write(f"**Flash Point**: {flash}")

        appearance = results.get("appearance")
        expander1.write(f"**Appearance**: {appearance}")

        odor = results.get("odor")
        expander1.write(f"**Odor**: {odor}")


        expander1.divider()
        storage = results.get("storage_conditions")
        expander1.write("**Storage Condition**")
        expander1.write(storage)


        expander1.divider()
        reactivity = results.get("reactivity")
        expander1.write("**Reactivity**")
        expander1.write(reactivity)


        source = results.get("source", "None")
        expander1.caption(f"Source: {source}")


if st.session_state.submitted:
    if "all_results" not in st.session_state:
        results_combined = []

        if not st.session_state.uploaded:
            print("No uploaded files, skipping...")
        # if 'uploaded' in st.session_state:
        else:
            print(st.session_state.uploaded)
            for uploaded_file in st.session_state.uploaded:
                with st.spinner("Reading..."):
                    results = sds_upload(uploaded_file)
                results_combined.append(results)
            st.success("PDFs processed")
                    # st.write(results)
                # page_design(results)


        if 'inputs' in st.session_state:
            print(st.session_state.inputs)
            data_editor_output = st.session_state.inputs
            cas_numbers = []

            for row in data_editor_output['edited_rows'].values():
                cas = row.get('CAS Number')
                if cas:
                    cas_numbers.append(cas)
            for row in data_editor_output['added_rows']:
                cas = row.get('CAS Number')
                if cas:
                    cas_numbers.append(cas)

            cas_numbers = list(set(cas_numbers))
            results2 = cas_reader(cas_numbers)
            results_combined.extend(results2)

        st.session_state["all_results"] = results_combined
        st.rerun()

    else:
        col1, col2 = st.columns([13,3])
        if col1.button("Home", type="primary"):
            for key in ["submitted", "uploaded", "inputs", "all_results", "show_data_editor"]:
                st.session_state.pop(key, None)
            st.rerun()
        show_all = col2.toggle("Expand all", value=True)
        for result in st.session_state["all_results"]:
            page_design(result, show_all=show_all)
            if result.get("additional_cas"):
                for additional in result["additional_cas"]:
                    page_design(additional, show_all=show_all)