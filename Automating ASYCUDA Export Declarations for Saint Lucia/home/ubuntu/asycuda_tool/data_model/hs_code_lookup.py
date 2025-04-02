"""
HS code lookup functionality for ASYCUDA export declarations.

This module provides functionality to look up HS codes based on product descriptions,
manage a reference database of HS codes, and validate HS code assignments.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import re
import logging
import os
import json
from .fuzzy_matcher import FuzzyMatcher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HSCodeLookup:
    """
    Provides HS code lookup functionality based on reference data.
    """
    
    def __init__(self, reference_data_path: Optional[str] = None):
        """
        Initialize the HS code lookup.
        
        Args:
            reference_data_path: Optional path to reference data file
        """
        self.fuzzy_matcher = FuzzyMatcher()
        self.hs_code_database = {}
        self.country_of_origin_map = {}
        self.previous_document_map = {}
        
        # Load reference data if provided
        if reference_data_path and os.path.exists(reference_data_path):
            self.load_reference_data(reference_data_path)
    
    def load_reference_data(self, file_path: str):
        """
        Load reference data from file.
        
        Args:
            file_path: Path to reference data file (CSV, Excel, or JSON)
        """
        logger.info(f"Loading reference data from {file_path}")
        
        try:
            # Determine file type from extension
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            if ext == '.csv':
                df = pd.read_csv(file_path)
            elif ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            elif ext == '.json':
                with open(file_path, 'r') as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
            else:
                logger.error(f"Unsupported file format: {ext}")
                return
            
            # Process the DataFrame
            self._process_reference_dataframe(df)
            
        except Exception as e:
            logger.error(f"Error loading reference data: {e}")
    
    def _process_reference_dataframe(self, df: pd.DataFrame):
        """
        Process reference data from DataFrame.
        
        Args:
            df: DataFrame containing reference data
        """
        # Check if this is ANSE CHASTANET STOCK format
        if all(col in df.columns for col in ['HS Code', 'Description', 'Origin']):
            logger.info("Detected ANSE CHASTANET STOCK format")
            self._process_anse_chastanet_format(df)
        else:
            logger.info("Processing generic reference data format")
            self._process_generic_format(df)
        
        # Load data into fuzzy matcher
        self.fuzzy_matcher.load_reference_data(df)
    
    def _process_anse_chastanet_format(self, df: pd.DataFrame):
        """
        Process reference data in ANSE CHASTANET STOCK format.
        
        Args:
            df: DataFrame in ANSE CHASTANET STOCK format
        """
        # Build HS code database
        for _, row in df.iterrows():
            try:
                hs_code = str(row.get('HS Code', '')).strip().replace('000000', '')
                description = str(row.get('Description', '')).strip()
                origin = str(row.get('Origin', 'US')).strip()
                office = str(row.get('Office', '')).strip()
                product_code = str(row.get('Product', '')).strip()
                c_nbr = str(row.get('C Nbr', '')).strip()
                line = str(row.get('Line', '')).strip()
                year = str(row.get('Year', '')).strip()
                
                if not hs_code or not description:
                    continue
                
                # Add to HS code database
                if hs_code not in self.hs_code_database:
                    self.hs_code_database[hs_code] = {
                        'description': description,
                        'products': []
                    }
                
                # Add product details
                product_info = {
                    'product_code': product_code,
                    'description': description,
                    'origin': origin,
                    'office': office,
                    'c_nbr': c_nbr,
                    'line': line,
                    'year': year
                }
                
                self.hs_code_database[hs_code]['products'].append(product_info)
                
                # Add to country of origin map
                if product_code:
                    self.country_of_origin_map[product_code.upper()] = origin
                
                # Add to previous document map
                if product_code and c_nbr and office and year:
                    document_ref = f"{office} {year} C {c_nbr}"
                    if line:
                        document_ref += f" art. {line}"
                    
                    self.previous_document_map[product_code.upper()] = document_ref
                
            except Exception as e:
                logger.warning(f"Error processing row: {e}")
    
    def _process_generic_format(self, df: pd.DataFrame):
        """
        Process reference data in generic format.
        
        Args:
            df: DataFrame containing reference data
        """
        # Try to identify key columns
        hs_col = next((col for col in df.columns if 'hs' in col.lower() or 'code' in col.lower()), None)
        desc_col = next((col for col in df.columns if 'desc' in col.lower() or 'product' in col.lower()), None)
        origin_col = next((col for col in df.columns if 'origin' in col.lower() or 'country' in col.lower()), None)
        
        if not hs_col or not desc_col:
            logger.warning("Could not identify required columns in reference data")
            return
        
        # Build HS code database
        for _, row in df.iterrows():
            try:
                hs_code = str(row[hs_col]).strip()
                description = str(row[desc_col]).strip()
                origin = str(row[origin_col]).strip() if origin_col else 'US'
                
                if not hs_code or not description:
                    continue
                
                # Add to HS code database
                if hs_code not in self.hs_code_database:
                    self.hs_code_database[hs_code] = {
                        'description': description,
                        'products': []
                    }
                
                # Add product details
                product_info = {
                    'description': description,
                    'origin': origin
                }
                
                # Add any additional columns as properties
                for col in df.columns:
                    if col not in [hs_col, desc_col, origin_col]:
                        product_info[col] = row[col]
                
                self.hs_code_database[hs_code]['products'].append(product_info)
                
            except Exception as e:
                logger.warning(f"Error processing row: {e}")
    
    def lookup_hs_code(self, description: str) -> Dict[str, Any]:
        """
        Look up HS code for a product description.
        
        Args:
            description: Product description to look up
            
        Returns:
            Dictionary with HS code match details
        """
        return self.fuzzy_matcher.get_best_match(description)
    
    def lookup_country_of_origin(self, product_code: Optional[str] = None, description: Optional[str] = None) -> str:
        """
        Look up country of origin for a product.
        
        Args:
            product_code: Product code to look up
            description: Product description to use as fallback
            
        Returns:
            Country of origin code (2-letter)
        """
        # Try direct lookup by product code
        if product_code and product_code.upper() in self.country_of_origin_map:
            return self.country_of_origin_map[product_code.upper()]
        
        # Try lookup via HS code match
        if description:
            match = self.lookup_hs_code(description)
            if match and 'details' in match and 'origin' in match['details']:
                return match['details']['origin']
        
        # Default to US
        return 'US'
    
    def lookup_previous_document(self, product_code: Optional[str] = None, description: Optional[str] = None, hs_code: Optional[str] = None) -> Optional[str]:
        """
        Look up previous document reference for a product.
        
        Args:
            product_code: Product code to look up
            description: Product description to use as fallback
            hs_code: HS code to use for generating a default reference
            
        Returns:
            Document reference if found, generated default if not
        """
        # Try direct lookup by product code
        if product_code and product_code.upper() in self.previous_document_map:
            return self.previous_document_map[product_code.upper()]
        
        # Try lookup via HS code match
        if description:
            match = self.lookup_hs_code(description)
            if match and 'details' in match:
                details = match['details']
                if 'office' in details and 'year' in details and 'c_nbr' in details:
                    document_ref = f"{details['office']} {details['year']} C {details['c_nbr']}"
                    if 'line' in details:
                        document_ref += f" art. {details['line']}"
                    return document_ref
        
        # Generate a default reference based on HS code
        if hs_code:
            # Map HS code prefixes to common customs offices
            hs_prefix = hs_code[:2]
            office_mapping = {
                '42': 'LCCAP',  # Bags
                '62': 'LCVGC',  # Clothing
                '64': 'LCVFP',  # Footwear
                '65': 'LCCAP',  # Headwear
                '71': 'LCCAP',  # Jewelry
            }
            
            office = office_mapping.get(hs_prefix, 'LCCAP')
            current_year = pd.Timestamp.now().year
            
            # Generate a plausible document reference
            return f"{office} {current_year} C 10000 art. 1"
        
        return None
    
    def validate_hs_code(self, hs_code: str) -> bool:
        """
        Validate an HS code.
        
        Args:
            hs_code: HS code to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check format (6-10 digits)
        if not re.match(r'^\d{6,10}$', hs_code):
            return False
        
        # Check if in database (optional)
        if self.hs_code_database and hs_code not in self.hs_code_database:
            logger.warning(f"HS code {hs_code} not found in reference database")
            # Still return True as it might be valid even if not in our database
        
        return True
    
    def get_hs_code_details(self, hs_code: str) -> Dict[str, Any]:
        """
        Get details for an HS code.
        
        Args:
            hs_code: HS code to look up
            
        Returns:
            Dictionary with HS code details
        """
        return self.hs_code_database.get(hs_code, {})
    
    def export_reference_data(self, file_path: str):
        """
        Export reference data to file.
        
        Args:
            file_path: Path to export file (CSV, Excel, or JSON)
        """
        try:
            # Convert database to DataFrame
            data = []
            for hs_code, details in self.hs_code_database.items():
                for product in details['products']:
                    row = {'HS Code': hs_code, 'Description': details['description']}
                    row.update(product)
                    data.append(row)
            
            df = pd.DataFrame(data)
            
            # Determine file type from extension
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            if ext == '.csv':
                df.to_csv(file_path, index=False)
            elif ext == '.xlsx':
                df.to_excel(file_path, index=False)
            elif ext == '.json':
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
            else:
                logger.error(f"Unsupported file format: {ext}")
                return
            
            logger.info(f"Reference data exported to {file_path}")
            
        except Exception as e:
            logger.error(f"Error exporting reference data: {e}")
