#!/usr/bin/env python3
"""
ASYCUDA Export Declaration Automation Tool

This is the main application file for the ASYCUDA Export Declaration Automation Tool.
It provides a Streamlit web interface for uploading sales data, configuring settings,
generating declarations, and exporting results.
"""

import streamlit as st
import pandas as pd
import os
import io
import json
import zipfile
import tempfile
import datetime
import logging
from pathlib import Path

# Import data model components
from data_model.asycuda_data_model import Declaration, Item, Entity
from data_model.field_mapper import FieldMapper
from data_model.format_generators import FormatGeneratorFactory
from data_model.validation import ValidationService
from data_model.error_handling import AsycudaExportManager, ErrorHandler, UserFeedback, UXHelper
from data_model.automation import AutomationService, ScheduleConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REFERENCE_DATA_DIR = os.path.join(BASE_DIR, "reference_data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Create directories if they don't exist
for directory in [DATA_DIR, REFERENCE_DATA_DIR, OUTPUT_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)

# Initialize components
error_handler = ErrorHandler(LOG_DIR)
user_feedback = UserFeedback()
validation_service = ValidationService()
export_manager = AsycudaExportManager(LOG_DIR)
automation_service = AutomationService(BASE_DIR)

# Set page configuration
st.set_page_config(
    page_title="ASYCUDA Export Declaration Automation",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define pages
PAGES = {
    "Home": "home",
    "Upload Data": "upload_data",
    "Configure Settings": "configure_settings",
    "Generate Declaration": "generate_declaration",
    "Export Results": "export_results",
    "Reference Data": "reference_data",
    "Automation": "automation",
    "About": "about"
}

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "home"
if "sales_data" not in st.session_state:
    st.session_state.sales_data = None
if "reference_data" not in st.session_state:
    st.session_state.reference_data = None
if "settings" not in st.session_state:
    st.session_state.settings = {
        "declaration_type": "EX3",
        "customs_office": "LCVFP",
        "general_procedure_code": "3071",
        "extended_procedure_code": "113",
        "country_of_destination": "VC",
        "mode_of_transport": "VC",
        "office_of_entry_exit": "LCVFP",
        "currency_code": "XCD",
        "exchange_rate": 1.0
    }
if "exporter" not in st.session_state:
    st.session_state.exporter = Entity(
        id="A0001015",
        name="ANSE CHASTANET HOTEL",
        address_line1="P.O. BOX 7000",
        address_line2="SOUFRIERE",
        city="SOUFRIERE",
        country="LC"
    )
if "declarant" not in st.session_state:
    st.session_state.declarant = Entity(
        id="H0002656",
        name="HARRIS CUSTOMS BROKERAGE",
        address_line1="HEWANORRA INTERNATIONAL AIRPORT",
        address_line2="BOX 354",
        city="VIEUX FORT",
        country="LC"
    )
if "declaration" not in st.session_state:
    st.session_state.declaration = None
if "export_formats" not in st.session_state:
    st.session_state.export_formats = {}
if "validation_results" not in st.session_state:
    st.session_state.validation_results = {}
if "column_mappings" not in st.session_state:
    st.session_state.column_mappings = {
        "description": "Description",
        "quantity": "Quantity",
        "unit_price": "Unit Price",
        "total_price": "Total Price"
    }
if "fuzzy_threshold" not in st.session_state:
    st.session_state.fuzzy_threshold = 80

# Sidebar navigation
st.sidebar.title("ASYCUDA Export Automation")
selected_page = st.sidebar.radio("Navigation", list(PAGES.keys()))
st.session_state.page = PAGES[selected_page]

# Display progress if available
if "progress" in st.session_state and st.session_state.progress:
    progress = st.session_state.progress
    progress_percentage = progress.get("percentage", 0)
    st.sidebar.progress(progress_percentage / 100)
    st.sidebar.text(f"Progress: {progress_percentage:.0f}%")
    
    # Show current step
    current_step = progress.get("current_step")
    if current_step:
        step_status = progress.get("steps", {}).get(current_step, {}).get("status", "")
        step_message = progress.get("steps", {}).get(current_step, {}).get("message", "")
        
        if step_status == "in_progress":
            st.sidebar.info(f"Working on: {current_step}")
        elif step_status == "completed":
            st.sidebar.success(f"Completed: {current_step}")
        elif step_status == "failed":
            st.sidebar.error(f"Failed: {current_step} - {step_message}")

# Display validation status if available
if "validation_results" in st.session_state and st.session_state.validation_results:
    validation_results = st.session_state.validation_results
    
    # Format validation results
    formatted_results = UXHelper.format_validation_results(validation_results)
    
    # Display overall status
    overall = formatted_results.get("overall", {})
    if overall.get("is_valid", False):
        st.sidebar.success("✅ Validation passed")
    else:
        st.sidebar.error(f"❌ Validation failed: {overall.get('error_count', 0)} errors")

# Home page
def render_home():
    st.title("ASYCUDA Export Declaration Automation")
    
    st.markdown("""
    Welcome to the ASYCUDA Export Declaration Automation Tool for duty-free shops in Saint Lucia.
    
    This tool helps you convert sales reports into ASYCUDA-compliant export declarations that can be
    directly imported into ASYCUDA World without manual re-entry.
    
    ## Getting Started
    
    1. **Upload Data**: Upload your sales report Excel file and optional reference data
    2. **Configure Settings**: Set up exporter, declarant, and default values
    3. **Generate Declaration**: Process your sales data into an ASYCUDA declaration
    4. **Export Results**: Download the declaration in various formats
    
    ## Features
    
    - **Intelligent Mapping**: Automatically match sales descriptions to HS codes
    - **Multiple Export Formats**: XML, pipe-delimited text, Excel, and PDF
    - **Validation**: Ensure all declarations meet ASYCUDA requirements
    - **Automation**: Schedule daily, weekly, or monthly processing
    """)
    
    # Quick start buttons
    st.subheader("Quick Start")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Upload Data", key="home_upload"):
            st.session_state.page = "upload_data"
            st.experimental_rerun()
    
    with col2:
        if st.button("Configure Settings", key="home_settings"):
            st.session_state.page = "configure_settings"
            st.experimental_rerun()
    
    with col3:
        if st.button("Generate Declaration", key="home_generate"):
            st.session_state.page = "generate_declaration"
            st.experimental_rerun()
    
    # Status overview
    st.subheader("Status Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.session_state.sales_data is not None:
            st.success("✅ Sales data loaded")
        else:
            st.warning("❌ No sales data loaded")
        
        if st.session_state.reference_data is not None:
            st.success("✅ Reference data loaded")
        else:
            st.info("ℹ️ No reference data loaded (optional)")
    
    with col2:
        if st.session_state.declaration is not None:
            st.success("✅ Declaration generated")
        else:
            st.warning("❌ No declaration generated")
        
        if st.session_state.export_formats:
            st.success(f"✅ {len(st.session_state.export_formats)} export formats generated")
        else:
            st.warning("❌ No export formats generated")

# Upload data page
def render_upload_data():
    st.title("Upload Data")
    
    st.markdown("""
    Upload your sales report Excel file and optional reference data for HS code matching.
    
    The sales report should contain at least the following columns:
    - Product description
    - Quantity
    - Unit price
    - Total price
    
    Reference data should be in ANSE CHASTANET STOCK format with HS codes and product descriptions.
    """)
    
    # Upload sales data
    st.subheader("Sales Report")
    
    sales_file = st.file_uploader("Upload sales report Excel file", type=["xlsx", "xls"])
    
    if sales_file is not None:
        try:
            # Save file to disk
            sales_file_path = os.path.join(DATA_DIR, "sales_report.xlsx")
            with open(sales_file_path, "wb") as f:
                f.write(sales_file.getvalue())
            
            # Load sales data
            sales_data = pd.read_excel(sales_file)
            
            # Display preview
            st.subheader("Sales Data Preview")
            st.dataframe(sales_data.head(10))
            
            # Store in session state
            st.session_state.sales_data = sales_data
            st.session_state.sales_file_path = sales_file_path
            
            st.success(f"Successfully loaded sales data with {len(sales_data)} rows")
            
        except Exception as e:
            st.error(f"Error loading sales data: {str(e)}")
    
    # Upload reference data
    st.subheader("Reference Data (Optional)")
    
    reference_file = st.file_uploader("Upload reference data file", type=["xlsx", "xls", "csv"])
    
    if reference_file is not None:
        try:
            # Save file to disk
            reference_file_path = os.path.join(REFERENCE_DATA_DIR, "reference_data.xlsx")
            with open(reference_file_path, "wb") as f:
                f.write(reference_file.getvalue())
            
            # Load reference data
            if reference_file.name.endswith(".csv"):
                reference_data = pd.read_csv(reference_file)
            else:
                reference_data = pd.read_excel(reference_file)
            
            # Display preview
            st.subheader("Reference Data Preview")
            st.dataframe(reference_data.head(10))
            
            # Store in session state
            st.session_state.reference_data = reference_data
            st.session_state.reference_file_path = reference_file_path
            
            st.success(f"Successfully loaded reference data with {len(reference_data)} rows")
            
        except Exception as e:
            st.error(f"Error loading reference data: {str(e)}")
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Back to Home"):
            st.session_state.page = "home"
            st.experimental_rerun()
    
    with col2:
        if st.button("Continue to Configure Settings"):
            st.session_state.page = "configure_settings"
            st.experimental_rerun()

# Configure settings page
def render_configure_settings():
    st.title("Configure Settings")
    
    st.markdown("""
    Configure the settings for your ASYCUDA export declaration.
    
    These settings include:
    - Exporter and declarant information
    - Default values for declaration fields
    - Column mappings for your sales data
    - Fuzzy matching settings
    """)
    
    # Create tabs for different settings
    tab1, tab2, tab3, tab4 = st.tabs(["Entity Information", "Default Values", "Column Mappings", "Matching Settings"])
    
    # Entity Information tab
    with tab1:
        st.subheader("Exporter Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            exporter_id = st.text_input("Exporter ID", value=st.session_state.exporter.id)
            exporter_name = st.text_input("Exporter Name", value=st.session_state.exporter.name)
            exporter_address1 = st.text_input("Address Line 1", value=st.session_state.exporter.address_line1)
        
        with col2:
            exporter_address2 = st.text_input("Address Line 2", value=st.session_state.exporter.address_line2)
            exporter_city = st.text_input("City", value=st.session_state.exporter.city)
            exporter_country = st.text_input("Country Code", value=st.session_state.exporter.country)
        
        # Update exporter in session state
        st.session_state.exporter = Entity(
            id=exporter_id,
            name=exporter_name,
            address_line1=exporter_address1,
            address_line2=exporter_address2,
            city=exporter_city,
            country=exporter_country
        )
        
        st.subheader("Declarant Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            declarant_id = st.text_input("Declarant ID", value=st.session_state.declarant.id)
            declarant_name = st.text_input("Declarant Name", value=st.session_state.declarant.name)
            declarant_address1 = st.text_input("Address Line 1", value=st.session_state.declarant.address_line1)
        
        with col2:
            declarant_address2 = st.text_input("Address Line 2", value=st.session_state.declarant.address_line2)
            declarant_city = st.text_input("City", value=st.session_state.declarant.city)
            declarant_country = st.text_input("Country Code", value=st.session_state.declarant.country)
        
        # Update declarant in session state
        st.session_state.declarant = Entity(
            id=declarant_id,
            name=declarant_name,
            address_line1=declarant_address1,
            address_line2=declarant_address2,
            city=declarant_city,
            country=declarant_country
        )
    
    # Default Values tab
    with tab2:
        st.subheader("Default Values")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            declaration_type = st.selectbox(
                "Declaration Type",
                options=["EX1", "EX2", "EX3"],
                index=["EX1", "EX2", "EX3"].index(st.session_state.settings["declaration_type"])
            )
            
            customs_office = st.selectbox(
                "Customs Office",
                options=["LCVFP", "LCHB", "LCCAP", "LCVGC"],
                index=["LCVFP", "LCHB", "LCCAP", "LCVGC"].index(st.session_state.settings["customs_office"])
            )
            
            general_procedure_code = st.text_input(
                "General Procedure Code",
                value=st.session_state.settings["general_procedure_code"]
            )
        
        with col2:
            extended_procedure_code = st.text_input(
                "Extended Procedure Code",
                value=st.session_state.settings["extended_procedure_code"]
            )
            
            country_of_destination = st.text_input(
                "Country of Destination",
                value=st.session_state.settings["country_of_destination"]
            )
            
            mode_of_transport = st.text_input(
                "Mode of Transport",
                value=st.session_state.settings["mode_of_transport"]
            )
        
        with col3:
            office_of_entry_exit = st.text_input(
                "Office of Entry/Exit",
                value=st.session_state.settings["office_of_entry_exit"]
            )
            
            currency_code = st.text_input(
                "Currency Code",
                value=st.session_state.settings["currency_code"]
            )
            
            exchange_rate = st.number_input(
                "Exchange Rate",
                value=float(st.session_state.settings["exchange_rate"]),
                min_value=0.01,
                step=0.01
            )
        
        # Update settings in session state
        st.session_state.settings.update({
            "declaration_type": declaration_type,
            "customs_office": customs_office,
            "general_procedure_code": general_procedure_code,
            "extended_procedure_code": extended_procedure_code,
            "country_of_destination": country_of_destination,
            "mode_of_transport": mode_of_transport,
            "office_of_entry_exit": office_of_entry_exit,
            "currency_code": currency_code,
            "exchange_rate": exchange_rate
        })
    
    # Column Mappings tab
    with tab3:
        st.subheader("Column Mappings")
        
        # Show available columns if sales data is loaded
        if st.session_state.sales_data is not None:
            available_columns = list(st.session_state.sales_data.columns)
            
            st.info(f"Available columns in your sales data: {', '.join(available_columns)}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                description_column = st.selectbox(
                    "Description Column",
                    options=available_columns,
                    index=available_columns.index(st.session_state.column_mappings["description"]) if st.session_state.column_mappings["description"] in available_columns else 0
                )
                
                quantity_column = st.selectbox(
                    "Quantity Column",
                    options=available_columns,
                    index=available_columns.index(st.session_state.column_mappings["quantity"]) if st.session_state.column_mappings["quantity"] in available_columns else 0
                )
            
            with col2:
                unit_price_column = st.selectbox(
                    "Unit Price Column",
                    options=available_columns,
                    index=available_columns.index(st.session_state.column_mappings["unit_price"]) if st.session_state.column_mappings["unit_price"] in available_columns else 0
                )
                
                total_price_column = st.selectbox(
                    "Total Price Column",
                    options=available_columns,
                    index=available_columns.index(st.session_state.column_mappings["total_price"]) if st.session_state.column_mappings["total_price"] in available_columns else 0
                )
            
            # Update column mappings in session state
            st.session_state.column_mappings.update({
                "description": description_column,
                "quantity": quantity_column,
                "unit_price": unit_price_column,
                "total_price": total_price_column
            })
        else:
            st.warning("Please upload sales data first to configure column mappings")
    
    # Matching Settings tab
    with tab4:
        st.subheader("Fuzzy Matching Settings")
        
        fuzzy_threshold = st.slider(
            "Fuzzy Matching Threshold",
            min_value=50,
            max_value=100,
            value=st.session_state.fuzzy_threshold,
            help="Higher values require closer matches"
        )
        
        # Update fuzzy threshold in session state
        st.session_state.fuzzy_threshold = fuzzy_threshold
        
        st.info("""
        The fuzzy matching threshold controls how closely a product description must match a reference description to be considered a match.
        
        - Higher values (e.g., 90-100) require very close matches
        - Lower values (e.g., 50-70) allow more flexible matching but may introduce errors
        - Recommended value: 80
        """)
    
    # Save settings button
    if st.button("Save Settings"):
        st.success("Settings saved successfully")
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Back to Upload Data"):
            st.session_state.page = "upload_data"
            st.experimental_rerun()
    
    with col2:
        if st.button("Continue to Generate Declaration"):
            st.session_state.page = "generate_declaration"
            st.experimental_rerun()

# Generate declaration page
def render_generate_declaration():
    st.title("Generate Declaration")
    
    st.markdown("""
    Generate an ASYCUDA-compliant export declaration from your sales data.
    
    This process will:
    1. Match product descriptions to HS codes
    2. Calculate weights and values
    3. Apply default values and settings
    4. Create a complete declaration
    """)
    
    # Check if sales data is loaded
    if st.session_state.sales_data is None:
        st.warning("Please upload sales data first")
        
        if st.button("Go to Upload Data"):
            st.session_state.page = "upload_data"
            st.experimental_rerun()
        
        return
    
    # Declaration details
    st.subheader("Declaration Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        registration_number = st.text_input(
            "Registration Number",
            value=f"A{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
        )
        
        commercial_reference = st.text_input(
            "Commercial Reference",
            value=f"REF{datetime.datetime.now().strftime('%Y%m%d')}"
        )
    
    # Generate declaration button
    if st.button("Generate Declaration"):
        try:
            # Show spinner during processing
            with st.spinner("Generating declaration..."):
                # Process sales file
                result = export_manager.process_sales_file(
                    sales_file_path=st.session_state.sales_file_path,
                    reference_data_path=st.session_state.reference_file_path if hasattr(st.session_state, "reference_file_path") else None,
                    exporter=st.session_state.exporter,
                    declarant=st.session_state.declarant,
                    settings={
                        **st.session_state.settings,
                        "registration_number": registration_number,
                        "commercial_reference": commercial_reference,
                        "column_mappings": st.session_state.column_mappings,
                        "fuzzy_threshold": st.session_state.fuzzy_threshold
                    }
                )
                
                # Store results in session state
                st.session_state.declaration = result["declaration"]
                st.session_state.export_formats = result["export_formats"]
                st.session_state.validation_results = result["validation_results"]
                st.session_state.progress = result["progress"]
                
                # Check result
                if result["success"]:
                    st.success("Declaration generated successfully")
                else:
                    st.error(f"Error generating declaration: {result['error']['error_message']}")
                    
                    # Show error details
                    with st.expander("Error Details"):
                        st.json(result["error"])
        
        except Exception as e:
            st.error(f"Error generating declaration: {str(e)}")
    
    # Display declaration if available
    if st.session_state.declaration is not None:
        declaration = st.session_state.declaration
        
        st.subheader("Declaration Summary")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"Registration Number: {declaration.registration_number}")
            st.write(f"Declaration Type: {declaration.declaration_type}")
            st.write(f"Customs Office: {declaration.customs_office}")
            st.write(f"Exporter: {declaration.exporter.name}")
            st.write(f"Declarant: {declaration.declarant.name}")
        
        with col2:
            st.write(f"Total Items: {len(declaration.items)}")
            st.write(f"Total Gross Weight: {declaration.total_gross_weight:.2f} kg")
            st.write(f"Total Net Weight: {declaration.total_net_weight:.2f} kg")
            st.write(f"Total Value: {declaration.total_value:.2f} {declaration.currency_code}")
        
        # Display items
        st.subheader("Declaration Items")
        
        # Create a DataFrame from items
        items_data = []
        for item in declaration.items:
            items_data.append({
                "Item #": item.item_number,
                "HS Code": item.hs_code,
                "Description": item.description,
                "Origin": item.country_of_origin,
                "Quantity": f"{item.quantity:.2f} {item.statistical_unit}",
                "Gross Weight": f"{item.gross_weight:.2f} kg",
                "Net Weight": f"{item.net_weight:.2f} kg",
                "Value": f"{item.customs_value:.2f} {declaration.currency_code}"
            })
        
        items_df = pd.DataFrame(items_data)
        st.dataframe(items_df)
        
        # Display validation results if available
        if st.session_state.validation_results:
            st.subheader("Validation Results")
            
            # Format validation results
            formatted_results = UXHelper.format_validation_results(st.session_state.validation_results)
            
            # Display overall status
            overall = formatted_results.get("overall", {})
            if overall.get("is_valid", False):
                st.success("✅ Validation passed")
            else:
                st.error(f"❌ Validation failed: {overall.get('error_count', 0)} errors, {overall.get('warning_count', 0)} warnings")
            
            # Display errors and warnings
            for context, result in formatted_results.items():
                if context != "overall":
                    with st.expander(f"{context.capitalize()} Validation"):
                        if result.get("is_valid", False):
                            st.success(f"✅ {context.capitalize()} validation passed")
                        else:
                            st.error(f"❌ {context.capitalize()} validation failed: {result.get('error_count', 0)} errors, {result.get('warning_count', 0)} warnings")
                        
                        # Display errors
                        if result.get("errors"):
                            st.subheader("Errors")
                            for error in result.get("errors", []):
                                st.error(error)
                        
                        # Display warnings
                        if result.get("warnings"):
                            st.subheader("Warnings")
                            for warning in result.get("warnings", []):
                                st.warning(warning)
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Back to Configure Settings"):
            st.session_state.page = "configure_settings"
            st.experimental_rerun()
    
    with col2:
        if st.button("Continue to Export Results"):
            st.session_state.page = "export_results"
            st.experimental_rerun()

# Export results page
def render_export_results():
    st.title("Export Results")
    
    st.markdown("""
    Export your ASYCUDA declaration in various formats:
    
    - **XML**: For direct import into ASYCUDA World
    - **Pipe-delimited Text (.txt)**: Alternative import format
    - **Excel**: For review and manual editing
    - **PDF**: Printable declaration similar to ASYCUDA's interface
    
    You can download individual formats or all formats as a ZIP archive.
    """)
    
    # Check if declaration is generated
    if st.session_state.declaration is None:
        st.warning("Please generate a declaration first")
        
        if st.button("Go to Generate Declaration"):
            st.session_state.page = "generate_declaration"
            st.experimental_rerun()
        
        return
    
    # Check if export formats are generated
    if not st.session_state.export_formats:
        st.warning("No export formats available. Please regenerate the declaration.")
        
        if st.button("Regenerate Declaration"):
            st.session_state.page = "generate_declaration"
            st.experimental_rerun()
        
        return
    
    # Display export options
    st.subheader("Export Options")
    
    # XML export
    if "xml" in st.session_state.export_formats and st.session_state.export_formats["xml"]:
        xml_content = st.session_state.export_formats["xml"]
        
        with st.expander("XML Format"):
            st.code(xml_content, language="xml")
        
        # Download button
        st.download_button(
            label="Download XML",
            data=xml_content,
            file_name=f"declaration_{st.session_state.declaration.registration_number}.xml",
            mime="application/xml"
        )
    
    # Pipe-delimited text export
    if "txt" in st.session_state.export_formats and st.session_state.export_formats["txt"]:
        txt_content = st.session_state.export_formats["txt"]
        
        with st.expander("Pipe-delimited Text Format"):
            st.code(txt_content, language="text")
        
        # Download button
        st.download_button(
            label="Download Text",
            data=txt_content,
            file_name=f"declaration_{st.session_state.declaration.registration_number}.txt",
            mime="text/plain"
        )
    
    # Excel export
    if "excel" in st.session_state.export_formats and st.session_state.export_formats["excel"]:
        excel_content = st.session_state.export_formats["excel"]
        
        # Download button
        st.download_button(
            label="Download Excel",
            data=excel_content,
            file_name=f"declaration_{st.session_state.declaration.registration_number}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # PDF export
    if "pdf" in st.session_state.export_formats and st.session_state.export_formats["pdf"]:
        pdf_content = st.session_state.export_formats["pdf"]
        
        # Download button
        st.download_button(
            label="Download PDF",
            data=pdf_content,
            file_name=f"declaration_{st.session_state.declaration.registration_number}.pdf",
            mime="application/pdf"
        )
    
    # Download all formats as ZIP
    if st.session_state.export_formats:
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            # Add XML
            if "xml" in st.session_state.export_formats and st.session_state.export_formats["xml"]:
                zip_file.writestr(
                    f"declaration_{st.session_state.declaration.registration_number}.xml",
                    st.session_state.export_formats["xml"]
                )
            
            # Add TXT
            if "txt" in st.session_state.export_formats and st.session_state.export_formats["txt"]:
                zip_file.writestr(
                    f"declaration_{st.session_state.declaration.registration_number}.txt",
                    st.session_state.export_formats["txt"]
                )
            
            # Add Excel
            if "excel" in st.session_state.export_formats and st.session_state.export_formats["excel"]:
                zip_file.writestr(
                    f"declaration_{st.session_state.declaration.registration_number}.xlsx",
                    st.session_state.export_formats["excel"].getvalue()
                )
            
            # Add PDF
            if "pdf" in st.session_state.export_formats and st.session_state.export_formats["pdf"]:
                zip_file.writestr(
                    f"declaration_{st.session_state.declaration.registration_number}.pdf",
                    st.session_state.export_formats["pdf"].getvalue()
                )
        
        # Reset buffer position
        zip_buffer.seek(0)
        
        # Download button
        st.download_button(
            label="Download All Formats (ZIP)",
            data=zip_buffer,
            file_name=f"declaration_{st.session_state.declaration.registration_number}_all_formats.zip",
            mime="application/zip"
        )
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Back to Generate Declaration"):
            st.session_state.page = "generate_declaration"
            st.experimental_rerun()
    
    with col2:
        if st.button("Go to Home"):
            st.session_state.page = "home"
            st.experimental_rerun()

# Reference data page
def render_reference_data():
    st.title("Reference Data")
    
    st.markdown("""
    View and manage reference data for HS code matching.
    
    Reference data is used to match product descriptions to HS codes, countries of origin,
    and other required fields for ASYCUDA declarations.
    """)
    
    # Display reference data if available
    if st.session_state.reference_data is not None:
        st.subheader("Reference Data")
        
        # Display reference data
        st.dataframe(st.session_state.reference_data)
        
        # Export reference data
        if st.button("Export Reference Data"):
            # Convert to Excel
            output = io.BytesIO()
            st.session_state.reference_data.to_excel(output, index=False)
            output.seek(0)
            
            # Download button
            st.download_button(
                label="Download Reference Data",
                data=output,
                file_name="reference_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("No reference data available")
        
        st.info("""
        To add reference data:
        1. Go to the Upload Data page
        2. Upload a reference data file in ANSE CHASTANET STOCK format
        """)
    
    # Common HS codes
    st.subheader("Common HS Codes for Duty-Free Shops")
    
    common_hs_codes = {
        "71179000": "Imitation jewelry",
        "62053000": "Men's or boys' shirts",
        "65040000": "Hats and other headgear",
        "42022900": "Handbags and similar containers",
        "64052000": "Footwear with outer soles of textile materials",
        "62111200": "Women's or girls' swimwear",
        "62044900": "Women's or girls' dresses",
        "62064000": "Women's or girls' blouses, shirts",
        "62034990": "Men's or boys' trousers, shorts",
        "96159000": "Hair accessories"
    }
    
    # Create DataFrame
    common_hs_df = pd.DataFrame({
        "HS Code": common_hs_codes.keys(),
        "Description": common_hs_codes.values()
    })
    
    # Display common HS codes
    st.dataframe(common_hs_df)
    
    # Country codes
    st.subheader("Common Country Codes")
    
    common_countries = {
        "LC": "Saint Lucia",
        "VC": "Saint Vincent and the Grenadines",
        "US": "United States",
        "GB": "United Kingdom",
        "CA": "Canada",
        "FR": "France",
        "IT": "Italy",
        "DE": "Germany",
        "JP": "Japan",
        "CN": "China"
    }
    
    # Create DataFrame
    common_countries_df = pd.DataFrame({
        "Country Code": common_countries.keys(),
        "Country Name": common_countries.values()
    })
    
    # Display common country codes
    st.dataframe(common_countries_df)

# Automation page
def render_automation():
    st.title("Automation")
    
    st.markdown("""
    Set up automated processing of sales reports on a daily, weekly, or monthly basis.
    
    This feature allows you to:
    1. Configure a schedule for automatic processing
    2. Specify the sales file pattern and output directory
    3. Set up notifications for completed exports
    4. Monitor the status of scheduled tasks
    """)
    
    # Create tabs for different automation features
    tab1, tab2, tab3 = st.tabs(["Create Schedule", "Manage Schedules", "Run Now"])
    
    # Create Schedule tab
    with tab1:
        st.subheader("Create Schedule")
        
        # Schedule type
        schedule_type = st.selectbox(
            "Schedule Type",
            options=["daily", "weekly", "monthly"],
            index=0
        )
        
        # Sales file pattern
        sales_file_pattern = st.text_input(
            "Sales File Pattern",
            value=os.path.join(DATA_DIR, "sales_*.xlsx"),
            help="Pattern for sales files to process (e.g., /path/to/sales_*.xlsx)"
        )
        
        # Output directory
        output_dir = st.text_input(
            "Output Directory",
            value=os.path.join(OUTPUT_DIR, f"schedule_{datetime.datetime.now().strftime('%Y%m%d')}"),
            help="Directory for output files"
        )
        
        # Reference data
        use_reference_data = st.checkbox("Use Reference Data", value=True)
        reference_data_path = None
        if use_reference_data:
            if hasattr(st.session_state, "reference_file_path"):
                reference_data_path = st.session_state.reference_file_path
            else:
                st.warning("No reference data available. Please upload reference data first.")
        
        # Create schedule button
        if st.button("Create Schedule"):
            try:
                # Create schedule
                result = automation_service.create_schedule(
                    schedule_type=schedule_type,
                    sales_file_pattern=sales_file_pattern,
                    output_dir=output_dir,
                    reference_data_path=reference_data_path,
                    exporter=st.session_state.exporter,
                    declarant=st.session_state.declarant,
                    settings={
                        **st.session_state.settings,
                        "column_mappings": st.session_state.column_mappings,
                        "fuzzy_threshold": st.session_state.fuzzy_threshold
                    }
                )
                
                # Check result
                if result["success"]:
                    st.success(f"Schedule created successfully. Task ID: {result['task_id']}")
                    
                    # Show next run time
                    if result.get("next_run"):
                        st.info(f"Next run: {result['next_run']}")
                    
                    # Show script files
                    if result.get("script_files"):
                        st.subheader("Script Files")
                        
                        for script_type, script_path in result["script_files"].items():
                            st.write(f"{script_type.capitalize()}: {script_path}")
                else:
                    st.error(f"Error creating schedule: {result['error']['error_message']}")
                    
                    # Show error details
                    with st.expander("Error Details"):
                        st.json(result["error"])
            
            except Exception as e:
                st.error(f"Error creating schedule: {str(e)}")
    
    # Manage Schedules tab
    with tab2:
        st.subheader("Manage Schedules")
        
        # Refresh button
        if st.button("Refresh Schedules"):
            st.experimental_rerun()
        
        # Get schedule status
        try:
            result = automation_service.get_schedule_status()
            
            # Check result
            if result["success"]:
                if result.get("tasks"):
                    # Display tasks
                    for task_id, task_status in result["tasks"].items():
                        with st.expander(f"Task: {task_id}"):
                            # Status
                            status = task_status.get("status", "unknown")
                            if status == "completed":
                                st.success(f"Status: {status}")
                            elif status == "running":
                                st.info(f"Status: {status}")
                            elif status == "failed":
                                st.error(f"Status: {status}")
                            else:
                                st.warning(f"Status: {status}")
                            
                            # Last run
                            if task_status.get("last_run"):
                                st.write(f"Last run: {task_status['last_run']}")
                            
                            # Next run
                            if task_status.get("next_run"):
                                st.write(f"Next run: {task_status['next_run']}")
                            
                            # Error
                            if task_status.get("error"):
                                st.error(f"Error: {task_status['error']}")
                            
                            # Config
                            if task_status.get("config"):
                                with st.expander("Configuration"):
                                    st.json(task_status["config"])
                            
                            # Remove button
                            if st.button(f"Remove Task {task_id}", key=f"remove_{task_id}"):
                                try:
                                    remove_result = automation_service.remove_schedule(task_id)
                                    
                                    if remove_result["success"]:
                                        st.success(f"Task {task_id} removed successfully")
                                        st.experimental_rerun()
                                    else:
                                        st.error(f"Error removing task: {remove_result['error']['error_message']}")
                                
                                except Exception as e:
                                    st.error(f"Error removing task: {str(e)}")
                else:
                    st.info("No scheduled tasks found")
            else:
                st.error(f"Error getting schedule status: {result['error']['error_message']}")
        
        except Exception as e:
            st.error(f"Error getting schedule status: {str(e)}")
    
    # Run Now tab
    with tab3:
        st.subheader("Run Task Now")
        
        # Get tasks
        try:
            result = automation_service.get_schedule_status()
            
            # Check result
            if result["success"] and result.get("tasks"):
                # Task selection
                task_ids = list(result["tasks"].keys())
                selected_task = st.selectbox("Select Task", options=task_ids)
                
                # Run button
                if st.button("Run Task Now"):
                    try:
                        run_result = automation_service.run_schedule_now(selected_task)
                        
                        # Check result
                        if run_result["success"]:
                            st.success(f"Task {selected_task} started successfully")
                            
                            # Show status
                            st.write(f"Status: {run_result['status']}")
                            
                            # Show last run
                            if run_result.get("last_run"):
                                st.write(f"Last run: {run_result['last_run']}")
                            
                            # Show error
                            if run_result.get("error"):
                                st.error(f"Error: {run_result['error']}")
                        else:
                            st.error(f"Error running task: {run_result['error']['error_message']}")
                    
                    except Exception as e:
                        st.error(f"Error running task: {str(e)}")
            else:
                st.info("No scheduled tasks found")
        
        except Exception as e:
            st.error(f"Error getting schedule status: {str(e)}")

# About page
def render_about():
    st.title("About")
    
    st.markdown("""
    # ASYCUDA Export Declaration Automation Tool
    
    This tool automates the creation of ASYCUDA-compliant export declarations for duty-free shops in Saint Lucia.
    
    ## Features
    
    - **Sales Data Import**: Upload Excel sales reports containing raw product descriptions and quantities
    - **Intelligent Mapping**: Automatically match sales descriptions to HS codes using fuzzy matching
    - **Complete Field Coverage**: Auto-fill all required ASYCUDA fields, not just HS Code, Origin, Customs Office, and Value
    - **Multiple Export Formats**:
      - XML for direct ASYCUDA import
      - Pipe-delimited text (.txt) for alternative import
      - Structured Excel for review
      - PDF-style declaration similar to ASYCUDA's interface
    - **Validation System**: Ensure all declarations meet ASYCUDA requirements
    - **Scheduling**: Automate daily, weekly, or monthly export declaration generation
    
    ## System Requirements
    
    - Python 3.8 or higher
    - Required Python packages:
      - streamlit
      - pandas
      - openpyxl
      - fuzzywuzzy
      - python-Levenshtein
      - reportlab (for PDF generation)
      - schedule (for automation)
    
    ## Documentation
    
    For more information, please refer to the documentation.
    """)
    
    # Documentation
    if os.path.exists(os.path.join(BASE_DIR, "documentation.md")):
        with open(os.path.join(BASE_DIR, "documentation.md"), "r") as f:
            documentation = f.read()
        
        with st.expander("Documentation"):
            st.markdown(documentation)
    
    # Version information
    st.subheader("Version Information")
    
    st.write("Version: 1.0.0")
    st.write("Last Updated: April 2, 2025")
    
    # Contact information
    st.subheader("Contact Information")
    
    st.write("For support or questions, please contact the system administrator.")

# Render the selected page
if st.session_state.page == "home":
    render_home()
elif st.session_state.page == "upload_data":
    render_upload_data()
elif st.session_state.page == "configure_settings":
    render_configure_settings()
elif st.session_state.page == "generate_declaration":
    render_generate_declaration()
elif st.session_state.page == "export_results":
    render_export_results()
elif st.session_state.page == "reference_data":
    render_reference_data()
elif st.session_state.page == "automation":
    render_automation()
elif st.session_state.page == "about":
    render_about()
