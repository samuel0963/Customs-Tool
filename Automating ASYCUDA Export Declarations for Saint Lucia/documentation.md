# ASYCUDA Export Declaration Automation Tool

## User Documentation

### Introduction

The ASYCUDA Export Declaration Automation Tool is a comprehensive solution designed for duty-free shops in Saint Lucia to automate the creation of ASYCUDA-compliant export declarations. This tool streamlines the process of converting sales reports into properly formatted declarations that can be directly imported into ASYCUDA World without manual re-entry.

### Key Features

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

### System Requirements

- Python 3.8 or higher
- Required Python packages (installed automatically):
  - streamlit
  - pandas
  - openpyxl
  - fuzzywuzzy
  - python-Levenshtein
  - reportlab (for PDF generation)
  - schedule (for automation)
- Internet connection (for web deployment)

### Installation

#### Local Installation

1. Clone or download the repository
2. Navigate to the project directory
3. Install required packages:
   ```
   pip install -r requirements.txt
   ```
4. Run the application:
   ```
   streamlit run app.py
   ```

#### Web Deployment

The application can be deployed to Streamlit Cloud or any other Python web hosting service:

1. Push the code to a GitHub repository
2. Connect your Streamlit Cloud account to your GitHub repository
3. Deploy the application by selecting the repository and `app.py` as the main file

### Using the Application

#### 1. Upload Data

1. Navigate to the "Upload Data" page
2. Upload your duty-free sales report Excel file
3. Optionally upload reference data in ANSE CHASTANET STOCK format to improve HS code matching

#### 2. Configure Settings

1. Navigate to the "Configure Settings" page
2. Enter exporter and declarant information
3. Configure default values for declaration fields
4. Set up column mappings for your sales data
5. Adjust fuzzy matching settings if needed

#### 3. Generate Declaration

1. Navigate to the "Generate Declaration" page
2. Enter registration number and commercial reference (or use auto-generated values)
3. Click "Generate Declaration" to process your sales data
4. Review the generated declaration summary and items

#### 4. Export Results

1. Navigate to the "Export Results" page
2. Generate the desired export formats (XML, text, Excel, PDF)
3. Download individual formats or all formats as a ZIP archive

#### 5. Schedule Automation (Optional)

1. Configure a schedule for automatic processing
2. Set up daily, weekly, or monthly processing
3. Specify the sales file pattern and output directory
4. Use the provided scripts to set up system scheduling

### Troubleshooting

#### Common Issues

1. **Sales data not mapping correctly**:
   - Check column mappings in Configure Settings
   - Upload reference data to improve matching
   - Adjust fuzzy matching threshold

2. **Validation errors**:
   - Review validation error messages
   - Check exporter and declarant information
   - Verify HS codes and other required fields

3. **Export formats not importing into ASYCUDA**:
   - Ensure all validation checks pass
   - Check format compatibility with your ASYCUDA version
   - Verify all required fields are properly filled

#### Error Logs

Error logs are stored in the `logs` directory and can be helpful for diagnosing issues:

- Application logs: General application errors and warnings
- Validation logs: Detailed validation results
- Processing logs: Information about sales data processing
- Scheduler logs: Information about automated scheduling

### Contact and Support

For support or questions, please contact the system administrator.

## Administrator Guide

### System Architecture

The ASYCUDA Export Declaration Automation Tool is built with a modular architecture consisting of the following components:

1. **Data Model**: Core classes and data structures
2. **Field Mapping System**: Converts sales data to ASYCUDA fields
3. **Export Format Generators**: Creates various output formats
4. **Validation System**: Ensures data integrity and format compliance
5. **Error Handling**: Provides user-friendly error messages and logging
6. **Automation System**: Schedules and manages automated processing
7. **Web Interface**: Streamlit-based user interface

### Component Details

#### Data Model (`data_model/asycuda_data_model.py`)

The data model defines the core classes for ASYCUDA declarations:

- `Declaration`: Represents a complete ASYCUDA declaration
- `Item`: Represents an item within a declaration
- `Entity`: Represents an exporter or declarant
- `ReferenceData`: Manages reference data for lookups

#### Field Mapping System

The field mapping system includes several specialized components:

- `fuzzy_matcher.py`: Provides fuzzy matching for product descriptions
- `hs_code_lookup.py`: Manages HS code reference data and lookups
- `weight_estimator.py`: Estimates gross and net weights for products
- `document_reference.py`: Generates document references
- `field_mapper.py`: Main component that integrates all mapping functionality

#### Export Format Generators (`format_generators.py`)

Generates various export formats:

- XML generator for ASYCUDA import
- Pipe-delimited text generator
- Excel generator for review
- PDF generator for printable declarations

#### Validation System (`validation.py`)

Ensures data integrity and format compliance:

- Field validation against ASYCUDA requirements
- Data consistency checks
- Format validation for export files
- Validation reporting

#### Error Handling (`error_handling.py`)

Provides user-friendly error handling:

- Error messages and suggestions
- Progress tracking
- Logging system
- User experience improvements

#### Automation System (`automation.py`)

Manages scheduled processing:

- Schedule configuration
- Task execution
- Notification system
- Script generation for system integration

#### Web Interface (`app.py`)

Streamlit-based user interface with pages for:

- Home/welcome
- Data upload
- Settings configuration
- Declaration generation
- Export management
- Reference data viewing
- About/help

### Customization

#### Adding New Field Mappings

To add new field mappings:

1. Edit `field_mapper.py` to add new mapping methods
2. Update the `map_sales_to_declaration` method to use the new mappings
3. Add any necessary reference data to the lookup system

#### Modifying Export Formats

To modify export formats:

1. Edit the corresponding generator in `format_generators.py`
2. Update the format templates to match your requirements
3. Test the new format with the validation system

#### Changing Default Values

To change default values:

1. Edit the `defaults` dictionary in `field_mapper.py`
2. Update the UI defaults in `app.py` to match

### Deployment Guide

#### Local Deployment

For local deployment:

1. Install Python 3.8 or higher
2. Clone the repository
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the application:
   ```
   streamlit run app.py
   ```

#### Server Deployment

For server deployment:

1. Set up a Python environment on your server
2. Clone the repository
3. Install dependencies
4. Set up a service to run the application
5. Configure a reverse proxy (e.g., Nginx) if needed

#### Cloud Deployment

For cloud deployment (e.g., Streamlit Cloud):

1. Push the code to a GitHub repository
2. Connect your Streamlit Cloud account
3. Deploy the application
4. Configure sharing and access settings

### Maintenance

#### Updating Reference Data

To update reference data:

1. Prepare a new reference data file in ANSE CHASTANET STOCK format
2. Upload the file through the UI or place it in the reference_data directory
3. Restart the application if necessary

#### Monitoring Logs

Log files are stored in the `logs` directory:

- Check logs regularly for errors and warnings
- Monitor validation results for common issues
- Review scheduler logs for automation problems

#### Backup and Recovery

To back up the system:

1. Back up the entire application directory
2. Specifically back up the reference_data and config directories
3. Store backups securely and test recovery procedures

### Security Considerations

- The application does not include authentication by default
- Consider adding authentication for production use
- Secure access to the server and application
- Regularly update dependencies for security patches

## Developer Guide

### Code Structure

```
asycuda_tool/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── data_model/                 # Data model and processing components
│   ├── asycuda_data_model.py   # Core data structures
│   ├── field_mapper.py         # Main field mapping system
│   ├── fuzzy_matcher.py        # Fuzzy matching for product descriptions
│   ├── hs_code_lookup.py       # HS code lookup functionality
│   ├── weight_estimator.py     # Weight estimation for products
│   ├── document_reference.py   # Document reference generation
│   ├── format_generators.py    # Export format generators
│   ├── validation.py           # Validation system
│   ├── error_handling.py       # Error handling and UX improvements
│   └── automation.py           # Automation scheduling system
├── reference_data/             # Reference data files
├── config/                     # Configuration files
├── logs/                       # Log files
└── output/                     # Output files
```

### Development Environment Setup

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install development dependencies:
   ```
   pip install -r requirements-dev.txt
   ```
4. Install pre-commit hooks:
   ```
   pre-commit install
   ```

### Adding New Features

#### Adding a New Export Format

1. Create a new generator class in `format_generators.py`
2. Implement the `generate` method
3. Add the new generator to the `FormatGeneratorFactory`
4. Update the UI in `app.py` to include the new format

#### Enhancing Fuzzy Matching

1. Modify the `fuzzy_matcher.py` file to add new matching methods
2. Update the `get_best_match` method to use the new methods
3. Test with various product descriptions

#### Adding New Validation Rules

1. Add new validation methods to `validation.py`
2. Update the `validate_declaration` method to use the new validations
3. Add appropriate error messages and suggestions

### Testing

#### Manual Testing

1. Test with sample sales reports
2. Verify field mappings and HS code matching
3. Check export formats against ASYCUDA requirements
4. Validate error handling and user feedback

#### Automated Testing

1. Run unit tests:
   ```
   pytest tests/
   ```
2. Run integration tests:
   ```
   pytest tests/integration/
   ```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

### API Documentation

#### Data Model

```python
# Create a declaration
declaration = Declaration(
    registration_number="A20250402001",
    declaration_type="EX3",
    customs_office="LCVFP",
    exporter=exporter,
    declarant=declarant,
    # ... other fields
)

# Add items to the declaration
item = Item(
    item_number=1,
    hs_code="71179000",
    description="Silver Bracelet",
    country_of_origin="US",
    # ... other fields
)
declaration.add_item(item)
```

#### Field Mapping

```python
# Create a field mapper
field_mapper = FieldMapper(reference_data_path="reference_data.xlsx")

# Process a sales file
declaration = field_mapper.process_sales_file(
    sales_file_path="sales_report.xlsx",
    exporter=exporter,
    declarant=declarant
)
```

#### Export Formats

```python
# Create an export generator
xml_generator = FormatGeneratorFactory.create_generator('xml')

# Generate XML
xml_buffer = io.StringIO()
xml_generator.generate(declaration, xml_buffer)
xml_content = xml_buffer.getvalue()
```

#### Validation

```python
# Create a validation service
validation_service = ValidationService()

# Validate a declaration
validation_result = validation_service.validate_declaration(declaration)

# Check validation result
if validation_result.is_valid:
    print("Declaration is valid")
else:
    print(f"Validation errors: {validation_result.errors}")
```

#### Automation

```python
# Create an automation service
automation_service = AutomationService(base_dir="/path/to/base/dir")

# Create a schedule
result = automation_service.create_schedule(
    schedule_type="daily",
    sales_file_pattern="/path/to/sales_*.xlsx",
    reference_data_path="reference_data.xlsx",
    exporter=exporter,
    declarant=declarant
)

# Run a scheduled task immediately
result = automation_service.run_schedule_now(task_id)
```

## Appendix

### ASYCUDA Field Reference

| Field | Description | Format | Required |
|-------|-------------|--------|----------|
| Registration Number | Unique identifier | Alphanumeric, max 20 chars | Yes |
| Declaration Type | Type of declaration | EX1, EX2, EX3 | Yes |
| Customs Office | Customs office code | LC + 2-3 letters | Yes |
| General Procedure Code | General procedure | 4 digits | Yes |
| Extended Procedure Code | Extended procedure | 3 digits | Yes |
| Country of Destination | Destination country | 2 letters | Yes |
| Mode of Transport | Transport mode | 2 letters | Yes |
| Office of Entry/Exit | Entry/exit office | LC + 2-3 letters | Yes |
| Currency Code | Currency code | 3 letters | Yes |
| Exchange Rate | Exchange rate | Positive number | Yes |
| HS Code | Harmonized System code | 6-10 digits | Yes |
| Description | Item description | Text, max 280 chars | Yes |
| Country of Origin | Origin country | 2 letters | Yes |
| Gross Weight | Gross weight in kg | Positive number | Yes |
| Net Weight | Net weight in kg | Positive number | Yes |
| Statistical Unit | Statistical unit | 3 letters | Yes |
| Quantity | Quantity | Positive number | Yes |
| Customs Value | Customs value | Positive number | Yes |
| Package Type | Package type code | 2 letters | Yes |
| Package Count | Number of packages | Positive integer | Yes |

### Common HS Codes for Duty-Free Shops

| HS Code | Description | Category |
|---------|-------------|----------|
| 71179000 | Imitation jewelry | Jewelry |
| 62053000 | Men's or boys' shirts | Clothing |
| 65040000 | Hats and other headgear | Headwear |
| 42022900 | Handbags and similar containers | Bags |
| 64052000 | Footwear with outer soles of textile materials | Footwear |
| 62111200 | Women's or girls' swimwear | Swimwear |
| 62044900 | Women's or girls' dresses | Clothing |
| 62064000 | Women's or girls' blouses, shirts | Clothing |
| 62034990 | Men's or boys' trousers, shorts | Clothing |
| 96159000 | Hair accessories | Accessories |

### Glossary

- **ASYCUDA**: Automated System for Customs Data, a computerized customs management system
- **HS Code**: Harmonized System code, an international nomenclature for classifying products
- **EX1/EX2/EX3**: Export declaration types in ASYCUDA
- **Fuzzy Matching**: Technique to find approximate matches between strings
- **XML**: Extensible Markup Language, a format used for ASYCUDA import
- **Pipe-delimited**: Text format where fields are separated by the pipe character (|)
