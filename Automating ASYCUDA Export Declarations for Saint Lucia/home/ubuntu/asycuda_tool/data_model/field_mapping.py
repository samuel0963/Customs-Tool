"""
Field mapping system for connecting sales data to ASYCUDA fields.

This module provides functionality to map raw sales data to ASYCUDA-compliant
fields, including fuzzy matching for product descriptions, HS code lookup,
and reference data management.
"""

from typing import Dict, List, Any, Optional, Tuple
import re
import difflib
import pandas as pd
from fuzzywuzzy import fuzz, process
from .asycuda_data_model import Declaration, Item, Entity, ReferenceData


class FieldMappingError(Exception):
    """Exception raised for field mapping errors."""
    pass


class HSCodeMatcher:
    """
    Provides fuzzy matching functionality to connect product descriptions to HS codes.
    """
    
    def __init__(self, reference_data: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize the HS code matcher.
        
        Args:
            reference_data: Optional dictionary of reference data with product descriptions and HS codes
        """
        self.reference_data = reference_data or {}
        self.description_to_hs = {}
        self.hs_to_details = {}
        
        # Initialize from reference data if provided
        if reference_data:
            self._initialize_from_reference()
    
    def _initialize_from_reference(self):
        """Initialize lookup dictionaries from reference data."""
        for product_id, details in self.reference_data.items():
            description = details.get('description', '').upper()
            hs_code = details.get('hs_code', '')
            if description and hs_code:
                self.description_to_hs[description] = hs_code
                self.hs_to_details[hs_code] = details
    
    def load_from_dataframe(self, df: pd.DataFrame, 
                           description_col: str, 
                           hs_code_col: str,
                           additional_cols: Optional[List[str]] = None):
        """
        Load reference data from a pandas DataFrame.
        
        Args:
            df: DataFrame containing reference data
            description_col: Column name for product descriptions
            hs_code_col: Column name for HS codes
            additional_cols: Optional list of additional columns to include in details
        """
        additional_cols = additional_cols or []
        
        for _, row in df.iterrows():
            description = str(row[description_col]).upper()
            hs_code = str(row[hs_code_col])
            
            if not description or not hs_code:
                continue
                
            details = {'description': description, 'hs_code': hs_code}
            
            # Add additional columns to details
            for col in additional_cols:
                if col in row:
                    details[col] = row[col]
            
            self.description_to_hs[description] = hs_code
            self.hs_to_details[hs_code] = details
    
    def load_from_anse_chastanet_format(self, df: pd.DataFrame):
        """
        Load reference data from ANSE CHASTANET STOCK format.
        
        Args:
            df: DataFrame in ANSE CHASTANET STOCK format
        """
        # Expected columns: HS Code, Description, Origin, Office, etc.
        for _, row in df.iterrows():
            if 'HS Code' not in df.columns or 'Description' not in df.columns:
                raise FieldMappingError("Required columns not found in ANSE CHASTANET STOCK data")
                
            description = str(row['Description']).upper()
            hs_code = str(row['HS Code']).replace('000000', '')  # Clean up HS code
            
            if not description or not hs_code:
                continue
                
            details = {
                'description': description,
                'hs_code': hs_code,
                'origin': row.get('Origin', 'US'),
                'office': row.get('Office', ''),
                'product_code': row.get('Product', ''),
                'c_nbr': row.get('C Nbr', ''),
                'line': row.get('Line', ''),
                'year': row.get('Year', ''),
                'expiry': row.get('Expiry', '')
            }
            
            self.description_to_hs[description] = hs_code
            self.hs_to_details[hs_code] = details
            
            # Also add product code as a key for direct lookup
            if 'Product' in row and row['Product']:
                product_code = str(row['Product']).upper()
                self.description_to_hs[product_code] = hs_code
    
    def exact_match(self, description: str) -> Optional[str]:
        """
        Find exact match for a product description.
        
        Args:
            description: Product description to match
            
        Returns:
            HS code if found, None otherwise
        """
        return self.description_to_hs.get(description.upper())
    
    def fuzzy_match(self, description: str, threshold: int = 80) -> Optional[Tuple[str, int]]:
        """
        Find fuzzy match for a product description.
        
        Args:
            description: Product description to match
            threshold: Minimum similarity score (0-100) to consider a match
            
        Returns:
            Tuple of (HS code, score) if found, None otherwise
        """
        if not description:
            return None
            
        # Try exact match first
        exact = self.exact_match(description)
        if exact:
            return (exact, 100)
        
        # Use fuzzywuzzy for fuzzy matching
        try:
            # Get the best match
            match, score = process.extractOne(
                description.upper(),
                self.description_to_hs.keys(),
                scorer=fuzz.token_sort_ratio
            )
            
            if score >= threshold:
                return (self.description_to_hs[match], score)
        except Exception as e:
            # Fall back to simpler matching if fuzzywuzzy fails
            best_score = 0
            best_match = None
            
            for ref_desc in self.description_to_hs.keys():
                # Use difflib for basic fuzzy matching
                score = difflib.SequenceMatcher(None, description.upper(), ref_desc).ratio() * 100
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = ref_desc
            
            if best_match:
                return (self.description_to_hs[best_match], best_score)
        
        return None
    
    def keyword_match(self, description: str) -> Optional[str]:
        """
        Find match based on keywords in the description.
        
        Args:
            description: Product description to match
            
        Returns:
            HS code if found, None otherwise
        """
        # Define keyword to HS code mappings for common product categories
        keyword_mappings = {
            'HAT': '65040000',
            'CAP': '65040000',
            'VISOR': '65040000',
            'SHIRT': '62053000',
            'PANT': '62034990',
            'SHORT': '62034990',
            'BERMUDA': '62034990',
            'SWIMSUIT': '62111200',
            'BIKINI': '62111200',
            'BATHING': '62111200',
            'BAG': '42022900',
            'CROSSBODY': '42022900',
            'SHOULDER BAG': '42022900',
            'CLUTCH': '42022900',
            'COSMETIC BAG': '42023210',
            'SANDAL': '64052000',
            'BRACELET': '71179000',
            'NECKLACE': '71179000',
            'EARRING': '71179000',
            'RING': '71179000',
            'SCRUNCHIE': '96159000',
            'SARONG': '62114300',
            'PAREO': '62114300',
            'DRESS': '62044900',
            'TUNIC': '62064000',
            'TOP': '62064000',
            'BOTTOM': '62089290',
            'RASHGUARD': '62111200'
        }
        
        # Check for keywords in the description
        description_upper = description.upper()
        for keyword, hs_code in keyword_mappings.items():
            if keyword in description_upper:
                return hs_code
        
        return None
    
    def get_best_match(self, description: str) -> Dict[str, Any]:
        """
        Get the best HS code match for a product description using multiple methods.
        
        Args:
            description: Product description to match
            
        Returns:
            Dictionary with match details including HS code, method, and confidence
        """
        result = {
            'hs_code': None,
            'method': None,
            'confidence': 0,
            'details': {}
        }
        
        # Try exact match
        exact = self.exact_match(description)
        if exact:
            result['hs_code'] = exact
            result['method'] = 'exact'
            result['confidence'] = 100
            result['details'] = self.hs_to_details.get(exact, {})
            return result
        
        # Try fuzzy match
        fuzzy = self.fuzzy_match(description)
        if fuzzy:
            hs_code, score = fuzzy
            result['hs_code'] = hs_code
            result['method'] = 'fuzzy'
            result['confidence'] = score
            result['details'] = self.hs_to_details.get(hs_code, {})
            return result
        
        # Try keyword match
        keyword = self.keyword_match(description)
        if keyword:
            result['hs_code'] = keyword
            result['method'] = 'keyword'
            result['confidence'] = 70  # Lower confidence for keyword matching
            result['details'] = self.hs_to_details.get(keyword, {})
            return result
        
        # Default fallback
        result['hs_code'] = '71179000'  # Default to jewelry category
        result['method'] = 'default'
        result['confidence'] = 30
        return result


class WeightEstimator:
    """
    Estimates gross and net weights for products based on HS codes and descriptions.
    """
    
    def __init__(self):
        """Initialize the weight estimator with default weight mappings."""
        # Default weights by HS code prefix (kg)
        self.default_weights = {
            # Clothing
            '6205': {'gross': 0.3, 'net': 0.25},  # Shirts
            '6206': {'gross': 0.2, 'net': 0.15},  # Women's blouses
            '6203': {'gross': 0.5, 'net': 0.45},  # Men's suits, pants
            '6204': {'gross': 0.4, 'net': 0.35},  # Women's suits, dresses
            '6211': {'gross': 0.3, 'net': 0.25},  # Swimwear
            '6208': {'gross': 0.1, 'net': 0.08},  # Women's undergarments
            
            # Headwear
            '6504': {'gross': 0.2, 'net': 0.15},  # Hats and caps
            
            # Bags
            '4202': {'gross': 0.5, 'net': 0.45},  # Bags, wallets
            
            # Footwear
            '6402': {'gross': 0.6, 'net': 0.5},  # Footwear with outer soles
            '6405': {'gross': 0.5, 'net': 0.4},  # Other footwear
            
            # Jewelry
            '7117': {'gross': 0.05, 'net': 0.03},  # Imitation jewelry
            
            # Default for unknown categories
            'default': {'gross': 0.3, 'net': 0.25}
        }
    
    def add_weight_mapping(self, hs_prefix: str, gross: float, net: float):
        """
        Add a weight mapping for an HS code prefix.
        
        Args:
            hs_prefix: HS code prefix (first 4 digits)
            gross: Gross weight in kg
            net: Net weight in kg
        """
        self.default_weights[hs_prefix] = {'gross': gross, 'net': net}
    
    def estimate_weights(self, hs_code: str, description: str = None) -> Dict[str, float]:
        """
        Estimate gross and net weights for a product.
        
        Args:
            hs_code: HS code of the product
            description: Optional product description for additional context
            
        Returns:
            Dictionary with gross and net weights
        """
        # Try to match by HS code prefix (first 4 digits)
        for prefix_length in [4, 2]:
            if len(hs_code) >= prefix_length:
                prefix = hs_code[:prefix_length]
                for mapping_prefix, weights in self.default_weights.items():
                    if mapping_prefix.startswith(prefix):
                        return weights
        
        # Use description-based estimation if HS code doesn't match
        if description:
            description_upper = description.upper()
            
            # Check for keywords indicating heavy items
            if any(keyword in description_upper for keyword in ['BAG', 'SANDAL', 'SHOE', 'PANT']):
                return {'gross': 0.5, 'net': 0.45}
            
            # Check for keywords indicating light items
            if any(keyword in description_upper for keyword in ['RING', 'EARRING', 'BRACELET', 'NECKLACE']):
                return {'gross': 0.05, 'net': 0.03}
        
        # Default fallback
        return self.default_weights['default']


class PreviousDocumentMapper:
    """
    Maps products to previous document references required by ASYCUDA.
    """
    
    def __init__(self, reference_data: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize the previous document mapper.
        
        Args:
            reference_data: Optional dictionary of reference data with product details
        """
        self.reference_data = reference_data or {}
        self.product_to_document = {}
        
        # Initialize from reference data if provided
        if reference_data:
            self._initialize_from_reference()
    
    def _initialize_from_reference(self):
        """Initialize lookup dictionaries from reference data."""
        for product_id, details in self.reference_data.items():
            if 'c_nbr' in details and 'office' in details and 'year' in details:
                document_ref = f"{details['office']} {details['year']} C {details['c_nbr']}"
                if 'line' in details:
                    document_ref += f" art. {details['line']}"
                
                self.product_to_document[product_id] = document_ref
    
    def load_from_anse_chastanet_format(self, df: pd.DataFrame):
        """
        Load reference data from ANSE CHASTANET STOCK format.
        
        Args:
            df: DataFrame in ANSE CHASTANET STOCK format
        """
        for _, row in df.iterrows():
            if 'C Nbr' not in df.columns or 'Office' not in df.columns or 'Year' not in df.columns:
                continue
                
            product_id = str(row.get('Product', '')).upper()
            if not product_id:
                continue
                
            c_nbr = row.get('C Nbr', '')
            office = row.get('Office', '')
            year = row.get('Year', '')
            line = row.get('Line', '')
            
            document_ref = f"{office} {year} C {c_nbr}"
            if line:
                document_ref += f" art. {line}"
                
            self.product_to_document[product_id] = document_ref
            
            # Also add description as a key
            description = str(row.get('Description', '')).upper()
            if description:
                self.product_to_document[description] = document_ref
    
    def get_document_reference(self, product_id: str = None, description: str = None, hs_code: str = None) -> Optional[str]:
        """
        Get previous document reference for a product.
        
        Args:
            product_id: Product ID to look up
            description: Product description to use as fallback
            hs_code: HS code to use for generating a default reference
            
        Returns:
            Document reference if found, generated default if not
        """
        # Try direct lookup by product ID
        if product_id and product
(Content truncated due to size limit. Use line ranges to read in chunks)