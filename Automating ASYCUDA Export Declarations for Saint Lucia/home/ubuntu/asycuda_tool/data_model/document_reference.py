"""
Document reference mapping for ASYCUDA export declarations.

This module provides functionality to map products to previous document references
required by ASYCUDA, based on reference data from ANSE CHASTANET STOCK format.
"""

from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import logging
import re
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DocumentReferenceMapper:
    """
    Maps products to previous document references required by ASYCUDA.
    """
    
    def __init__(self):
        """Initialize the document reference mapper."""
        self.product_to_document = {}
        self.description_to_document = {}
        self.hs_to_office = {
            '42': 'LCCAP',  # Bags
            '62': 'LCVGC',  # Clothing
            '64': 'LCVFP',  # Footwear
            '65': 'LCCAP',  # Headwear
            '71': 'LCCAP',  # Jewelry
        }
    
    def load_from_anse_chastanet_format(self, df: pd.DataFrame):
        """
        Load reference data from ANSE CHASTANET STOCK format.
        
        Args:
            df: DataFrame in ANSE CHASTANET STOCK format
        """
        logger.info(f"Loading document references from DataFrame with {len(df)} rows")
        
        for _, row in df.iterrows():
            try:
                # Check for required columns
                if not all(col in df.columns for col in ['C Nbr', 'Office', 'Year']):
                    logger.warning("Required columns not found in ANSE CHASTANET STOCK data")
                    continue
                
                # Extract key fields
                product_code = str(row.get('Product', '')).strip()
                description = str(row.get('Description', '')).strip()
                c_nbr = str(row.get('C Nbr', '')).strip()
                office = str(row.get('Office', '')).strip()
                year = str(row.get('Year', '')).strip()
                line = str(row.get('Line', '')).strip()
                
                if not c_nbr or not office or not year:
                    continue
                
                # Create document reference
                document_ref = f"{office} {year} C {c_nbr}"
                if line:
                    document_ref += f" art. {line}"
                
                # Store mappings
                if product_code:
                    self.product_to_document[product_code.upper()] = document_ref
                
                if description:
                    self.description_to_document[description.upper()] = document_ref
                
            except Exception as e:
                logger.warning(f"Error processing document reference: {e}")
        
        logger.info(f"Loaded {len(self.product_to_document)} product code mappings and {len(self.description_to_document)} description mappings")
    
    def add_document_reference(self, product_code: str, document_ref: str):
        """
        Add a document reference mapping for a product code.
        
        Args:
            product_code: Product code
            document_ref: Document reference
        """
        self.product_to_document[product_code.upper()] = document_ref
    
    def add_description_mapping(self, description: str, document_ref: str):
        """
        Add a document reference mapping for a product description.
        
        Args:
            description: Product description
            document_ref: Document reference
        """
        self.description_to_document[description.upper()] = document_ref
    
    def add_hs_office_mapping(self, hs_prefix: str, office_code: str):
        """
        Add a mapping from HS code prefix to customs office code.
        
        Args:
            hs_prefix: HS code prefix (first 2 digits)
            office_code: Customs office code
        """
        self.hs_to_office[hs_prefix] = office_code
    
    def get_document_reference(self, product_code: Optional[str] = None, 
                             description: Optional[str] = None, 
                             hs_code: Optional[str] = None) -> Optional[str]:
        """
        Get previous document reference for a product.
        
        Args:
            product_code: Product code to look up
            description: Product description to use as fallback
            hs_code: HS code to use for generating a default reference
            
        Returns:
            Document reference if found, generated default if not
        """
        # Try direct lookup by product code
        if product_code:
            product_code_upper = product_code.upper()
            if product_code_upper in self.product_to_document:
                logger.debug(f"Found document reference for product code: {product_code}")
                return self.product_to_document[product_code_upper]
        
        # Try lookup by description
        if description:
            description_upper = description.upper()
            if description_upper in self.description_to_document:
                logger.debug(f"Found document reference for description: {description}")
                return self.description_to_document[description_upper]
            
            # Try partial matching for descriptions
            for ref_desc, doc_ref in self.description_to_document.items():
                if ref_desc in description_upper or description_upper in ref_desc:
                    logger.debug(f"Found partial match for description: {description} -> {ref_desc}")
                    return doc_ref
        
        # Generate a default reference based on HS code
        if hs_code:
            logger.debug(f"Generating default document reference for HS code: {hs_code}")
            return self._generate_default_reference(hs_code)
        
        # Last resort default
        logger.debug("No matching document reference found, using generic default")
        return "LCCAP 2025 C 10000 art. 1"
    
    def _generate_default_reference(self, hs_code: str) -> str:
        """
        Generate a default document reference based on HS code.
        
        Args:
            hs_code: HS code
            
        Returns:
            Generated document reference
        """
        # Get office code based on HS code prefix
        office = "LCCAP"  # Default office
        if len(hs_code) >= 2:
            hs_prefix = hs_code[:2]
            if hs_prefix in self.hs_to_office:
                office = self.hs_to_office[hs_prefix]
        
        # Get current year
        current_year = datetime.now().year
        
        # Generate reference number based on HS code
        # Use last 4 digits of HS code if available, otherwise use 10000
        ref_number = "10000"
        if len(hs_code) >= 6:
            ref_number = hs_code[-4:]
        
        # Generate article number (use last 2 digits of HS code or 1)
        article = "1"
        if len(hs_code) >= 4:
            article = hs_code[-2:]
        
        return f"{office} {current_year} C {ref_number} art. {article}"
    
    def analyze_document_references(self, products_df: pd.DataFrame,
                                  product_code_col: Optional[str] = None,
                                  description_col: Optional[str] = None,
                                  hs_code_col: Optional[str] = None) -> pd.DataFrame:
        """
        Analyze and generate document references for a set of products.
        
        Args:
            products_df: DataFrame containing product data
            product_code_col: Column name for product codes
            description_col: Column name for product descriptions
            hs_code_col: Column name for HS codes
            
        Returns:
            DataFrame with added document reference column
        """
        # Create a copy to avoid modifying the original
        result_df = products_df.copy()
        
        # Add document reference column
        result_df['document_reference'] = None
        
        # Process each product
        for idx, row in result_df.iterrows():
            product_code = None
            if product_code_col and product_code_col in row and not pd.isna(row[product_code_col]):
                product_code = str(row[product_code_col])
            
            description = None
            if description_col and description_col in row and not pd.isna(row[description_col]):
                description = str(row[description_col])
            
            hs_code = None
            if hs_code_col and hs_code_col in row and not pd.isna(row[hs_code_col]):
                hs_code = str(row[hs_code_col])
            
            document_ref = self.get_document_reference(product_code, description, hs_code)
            result_df.at[idx, 'document_reference'] = document_ref
        
        return result_df
