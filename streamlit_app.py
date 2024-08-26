import streamlit as st
import pandas as pd
import os
import streamlit.components.v1 as components
from CD_Script import create_html_report, varids_to_nicknames, df, df_2020, df_vars, social_vars, econ_vars, industry_vars, housing_vars

# Set up the Streamlit app
st.title("Congressional District Report Generator")

# User input for congressional district
congressional_district = st.text_input("Enter Congressional District (e.g., NC-11):")

# Button to generate report
if st.button("Generate Report"):
    if congressional_district:
        # Generate the report
        social_vars_v = varids_to_nicknames(social_vars, df_vars, df)
        econ_vars_v = varids_to_nicknames(econ_vars, df_vars, df)
        industry_vars_v = varids_to_nicknames(industry_vars, df_vars, df)
        housing_vars_v = varids_to_nicknames(housing_vars, df_vars, df)
        
        html_report = create_html_report(congressional_district, df, df_2020, social_vars_v, econ_vars_v, industry_vars_v, housing_vars_v)
        
        # Save the report to a file
        report_filename = f"{congressional_district}_report.html"
        with open(report_filename, "w") as f:
            f.write(html_report)
        
        # Display the report using components.html
        components.html(html_report, height=800, scrolling=True)
        
        # Provide a download link for the report
        with open(report_filename, "rb") as f:
            st.download_button(
                label="Download Report",
                data=f,
                file_name=report_filename,
                mime="text/html"
            )
    else:
        st.error("Please enter a valid congressional district.")