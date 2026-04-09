
import streamlit as st
from parser import is_valid_cas
from streamlit_pdf_conv import sds_upload, cas_reader
import re
import io
from exporter import export_result_to_excel

st.set_page_config(
    page_title="SDS Reader",
    page_icon="🧪",
    layout="centered"
)

if 'submitted' not in st.session_state:
    st.session_state.submitted = False

if 'input' not in st.session_state:
    st.session_state.input = None

if not st.session_state.submitted:
    invalid = False
    if "show_data_editor" not in st.session_state:
        st.session_state.show_data_editor = False

    st.header("Safety Data Sheet Parser")

    with st.form("all_data"):
        col1, col2 = st.columns(2)

        with col1:
            st.write("Upload SDS Files")
            uploaded_pdfs = st.file_uploader(
                "file_upload",
                type="pdf",
                accept_multiple_files=True,
                label_visibility="collapsed",
                key="uploaded"
            )

        with col2:
            st.write("CAS Input")
            container = st.container(border=True, height=135)
            with container:
                container.write('Type in CAS numbers')
                pressed = st.form_submit_button("Input")

            if pressed:
                st.session_state.show_data_editor = not st.session_state.show_data_editor

            if st.session_state.show_data_editor:
                data = st.data_editor(
                    use_container_width=True,
                    data={"CAS Number": [""]},
                    num_rows="dynamic",
                    key="inputs"
                )

                if data:
                    invalid_rows = []
                    for i, row in enumerate(data["CAS Number"]):
                        row = str(row)
                        if row and not is_valid_cas(row):
                            invalid_rows.append(row)

                    if invalid_rows:
                        invalid = True
                        st.error(f"Invalid CAS Number(s): {', '.join(invalid_rows)}")
                    else:
                        invalid = False

        pressed = st.form_submit_button("Submit", type="primary")

    st.caption("Specified for Millipore-Sigma and AaronChem")

    if pressed and not invalid:
        st.session_state.submitted = True
        st.rerun()


def nfpa_design(nfpa, expander):
    expander.write(f"Name: {nfpa['name']}")

    rows = [
        ("Health", "blue"),
        ("Flammability", "red"),
        ("Instability", "orange")
    ]

    for label, color in rows:
        c1, c2, c3 = expander.columns([3, 1, 16])
        c1.badge(label, color=color)
        c2.badge(nfpa[label]["value_html"], color="gray")
        c3.write(nfpa[label]["description"])

    c1, c2, c3 = expander.columns([3, 1, 16])
    c1.badge("Specific", color="gray")
    if nfpa["Special"]["description"]:
        c3.write(nfpa["Special"]["description"])
    if nfpa["Special"]["value_html"]:
        c2.badge(nfpa["Special"]["value_html"], color="gray")


def page_design(results, show_all=False):
    if not isinstance(results, dict):
        return

    cas_number = results.get("cas_number", "None")
    expander = st.expander(cas_number, expanded=show_all)

    expander.write(f"**CAS Number**: {cas_number}")
    expander.write(f"**CID**: {results.get('cid')}")

    expander.divider()
    expander.write("**Name**")
    if results.get("chemical_name"):
        expander.badge(results["chemical_name"], color="primary")

    expander.divider()
    expander.write("**Hazard Statements**")
    for item in results.get("ghs_from_sds", []) or []:
        c1, c2 = expander.columns([3, 12])
        c1.badge(item.get("ghs_code", ""), color="gray")
        c2.write(item.get("original_text", ""))

    expander.divider()
    expander.write("**NFPA Rating**")
    nfpa = results.get("nfpa")
    if isinstance(nfpa, dict):
        nfpa_design(nfpa, expander)
    elif isinstance(nfpa, list):
        for r in nfpa:
            nfpa_design(r, expander)

    for field in ["flash_point", "appearance", "odor", "storage_conditions", "reactivity"]:
        if results.get(field):
            expander.divider()
            expander.write(f"**{field.replace('_', ' ').title()}**")
            expander.write(results[field])

    expander.caption(f"Source: {results.get('source')}")


if st.session_state.submitted:
    if "all_results" not in st.session_state:
        results_combined = []

        if st.session_state.get("uploaded"):
            for uploaded_file in st.session_state.uploaded:
                with st.spinner("Reading..."):
                    results_combined.append(sds_upload(uploaded_file))
            st.success("PDFs processed")

        if st.session_state.get("inputs"):
            cas_numbers = []
            for row in st.session_state.inputs['edited_rows'].values():
                cas = row.get('CAS Number')
                if cas:
                    cas_numbers.append(cas)

            results_combined.append(cas_reader(cas_numbers))

        st.session_state["all_results"] = results_combined
        st.rerun()

    else:
        col0, col1, col2 = st.columns([6, 18, 5])

        if col1.button("Home", type="secondary"):
            for key in ["submitted", "uploaded", "inputs", "all_results", "show_data_editor"]:
                st.session_state.pop(key, None)
            st.rerun()

        show_all = col2.toggle("Expand all", value=True)

        for result in st.session_state["all_results"]:
            page_design(result, show_all=show_all)

        if st.session_state["all_results"]:
            output = export_result_to_excel(st.session_state["all_results"])
            with col0:
                st.download_button(
                    "Export to Excel",
                    output.getvalue(),
                    "sds_summary.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

