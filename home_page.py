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

# TODO: hazard statement as written in SDS, or official?

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





def page_design(results, show_all=False):
    with st.container():
        cas_number = results.get("cas_number", "None")
        expander1 = st.expander(f"{cas_number}", expanded=show_all)
        expander1.write(f"**CAS Number**: {cas_number}")

        cid = results.get("cid", "None")
        expander1.write(f"**CID**: {cid}")

        expander1.divider()
        col1, col2 = expander1.columns([13,1])
        with col1:
            pubnames = results.get("pubchem_name", "None")
            if pubnames == None:
                col1.write("**Name**: None Found")
            else:
                col1.write("**Name**")
                if isinstance(pubnames, list):
                    def strip_html_tags(text):
                        return re.sub(r"<.*?>", "", text)

                    clean_names = [strip_html_tags(name) for name in pubnames]
                    unique_names = list(dict.fromkeys(clean_names))

                    for name in unique_names:
                        col1.badge(f"{name}", color="gray")
                else:
                    col1.badge(f"{pubnames}", color="gray")
        with col2:
            if pubnames != None:
                st.badge("", icon=":material/check:", color="green")


        expander1.divider()
        expander1.write("**Hazard Statements**")
        ghs = results.get("ghs_from_sds", "None")
        for item in ghs:
            col1, col2, col3 = expander1.columns([3,10,1])

            if ghs == None:
                col1.write("GHS not found")

            else:
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
        nfpa = results.get("nfpa")
        expander1.write("**NFPA Rating**")
        expander1.write(nfpa)


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