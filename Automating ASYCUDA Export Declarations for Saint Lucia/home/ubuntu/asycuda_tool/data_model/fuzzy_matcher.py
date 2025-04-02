"""
Implementation of the fuzzy matching system for product descriptions to HS codes.

This module provides the core functionality for matching product descriptions
from sales reports to the appropriate HS codes using fuzzy matching algorithms.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from fuzzywuzzy import fuzz, process
import re
import difflib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FuzzyMatcher:
    """
    Provides fuzzy matching functionality for product descriptions.
    """
    
    def __init__(self):
        """Initialize the fuzzy matcher."""
        self.reference_data = {}
        self.description_to_hs = {}
        self.hs_to_details = {}
        self.keyword_mappings = {}
        
    def load_reference_data(self, anse_chastanet_df: pd.DataFrame):
        """
        Load reference data from ANSE CHASTANET STOCK format.
        
        Args:
            anse_chastanet_df: DataFrame containing reference data
        """
        logger.info(f"Loading reference data with {len(anse_chastanet_df)} rows")
        
        # Process each row in the reference data
        for _, row in anse_chastanet_df.iterrows():
            try:
                # Extract key fields
                description = str(row.get('Description', '')).strip().upper()
                hs_code = str(row.get('HS Code', '')).strip().replace('000000', '')
                origin = str(row.get('Origin', 'US')).strip()
                office = str(row.get('Office', '')).strip()
                product_code = str(row.get('Product', '')).strip()
                c_nbr = str(row.get('C Nbr', '')).strip()
                line = str(row.get('Line', '')).strip()
                
                if not description or not hs_code:
                    continue
                
                # Store in lookup dictionaries
                self.description_to_hs[description] = hs_code
                
                # Store details for this HS code
                details = {
                    'description': description,
                    'hs_code': hs_code,
                    'origin': origin,
                    'office': office,
                    'product_code': product_code,
                    'c_nbr': c_nbr,
                    'line': line
                }
                
                self.hs_to_details[hs_code] = details
                
                # Also add product code as a key if available
                if product_code:
                    self.description_to_hs[product_code.upper()] = hs_code
                
            except Exception as e:
                logger.error(f"Error processing reference data row: {e}")
        
        logger.info(f"Loaded {len(self.description_to_hs)} descriptions and {len(self.hs_to_details)} HS codes")
        
        # Initialize keyword mappings
        self._initialize_keyword_mappings()
    
    def _initialize_keyword_mappings(self):
        """Initialize keyword to HS code mappings for common product categories."""
        self.keyword_mappings = {
            'HAT': '65040000',
            'CAP': '65040000',
            'VISOR': '65040000',
            'SHIRT': '62053000',
            'POLO': '62053000',
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
    
    def exact_match(self, description: str) -> Optional[str]:
        """
        Find exact match for a product description.
        
        Args:
            description: Product description to match
            
        Returns:
            HS code if found, None otherwise
        """
        if not description:
            return None
            
        description = description.strip().upper()
        return self.description_to_hs.get(description)
    
    def keyword_match(self, description: str) -> Optional[str]:
        """
        Find match based on keywords in the description.
        
        Args:
            description: Product description to match
            
        Returns:
            HS code if found, None otherwise
        """
        if not description:
            return None
            
        description = description.strip().upper()
        
        # Check for exact keywords in the description
        for keyword, hs_code in self.keyword_mappings.items():
            if keyword in description:
                logger.debug(f"Keyword match found: '{keyword}' in '{description}' -> {hs_code}")
                return hs_code
        
        return None
    
    def fuzzy_match(self, description: str, threshold: int = 80) -> Optional[Tuple[str, int]]:
        """
        Find fuzzy match for a product description.
        
        Args:
            description: Product description to match
            threshold: Minimum similarity score (0-100) to consider a match
            
        Returns:
            Tuple of (HS code, score) if found, None otherwise
        """
        if not description or not self.description_to_hs:
            return None
            
        description = description.strip().upper()
        
        try:
            # Use fuzzywuzzy for fuzzy matching
            match, score = process.extractOne(
                description,
                self.description_to_hs.keys(),
                scorer=fuzz.token_sort_ratio
            )
            
            if score >= threshold:
                hs_code = self.description_to_hs[match]
                logger.debug(f"Fuzzy match found: '{description}' -> '{match}' (score: {score}) -> {hs_code}")
                return (hs_code, score)
                
        except Exception as e:
            logger.warning(f"Error in fuzzy matching: {e}")
            
            # Fall back to simpler matching if fuzzywuzzy fails
            best_score = 0
            best_match = None
            
            for ref_desc in self.description_to_hs.keys():
                # Use difflib for basic fuzzy matching
                score = difflib.SequenceMatcher(None, description, ref_desc).ratio() * 100
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = ref_desc
            
            if best_match:
                hs_code = self.description_to_hs[best_match]
                logger.debug(f"Fallback fuzzy match found: '{description}' -> '{best_match}' (score: {best_score}) -> {hs_code}")
                return (hs_code, best_score)
        
        return None
    
    def token_match(self, description: str, threshold: int = 2) -> Optional[str]:
        """
        Find match based on token overlap between description and reference data.
        
        Args:
            description: Product description to match
            threshold: Minimum number of matching tokens required
            
        Returns:
            HS code if found, None otherwise
        """
        if not description or not self.description_to_hs:
            return None
            
        description = description.strip().upper()
        
        # Tokenize the description
        tokens = set(re.findall(r'\b\w+\b', description))
        
        # Remove common words that don't help with matching
        stop_words = {'AND', 'WITH', 'THE', 'OF', 'IN', 'FOR', 'TO', 'A', 'AN'}
        tokens = tokens - stop_words
        
        best_match = None
        best_count = 0
        
        # Find reference description with most token overlap
        for ref_desc, hs_code in self.description_to_hs.items():
            ref_tokens = set(re.findall(r'\b\w+\b', ref_desc))
            ref_tokens = ref_tokens - stop_words
            
            # Count matching tokens
            common_tokens = tokens.intersection(ref_tokens)
            if len(common_tokens) > best_count and len(common_tokens) >= threshold:
                best_count = len(common_tokens)
                best_match = hs_code
        
        if best_match:
            logger.debug(f"Token match found: '{description}' -> {best_match} (common tokens: {best_count})")
            
        return best_match
    
    def get_best_match(self, description: str) -> Dict[str, Any]:
        """
        Get the best HS code match for a product description using multiple methods.
        
        Args:
            description: Product description to match
            
        Returns:
            Dictionary with match details including HS code, method, and confidence
        """
        if not description:
            return {
                'hs_code': '71179000',  # Default to jewelry category
                'method': 'default',
                'confidence': 0,
                'details': {}
            }
        
        description = description.strip()
        logger.info(f"Finding best match for: '{description}'")
        
        # Try exact match first (highest confidence)
        exact = self.exact_match(description)
        if exact:
            logger.info(f"Exact match found: {exact}")
            return {
                'hs_code': exact,
                'method': 'exact',
                'confidence': 100,
                'details': self.hs_to_details.get(exact, {})
            }
        
        # Try keyword match (high confidence)
        keyword = self.keyword_match(description)
        if keyword:
            logger.info(f"Keyword match found: {keyword}")
            return {
                'hs_code': keyword,
                'method': 'keyword',
                'confidence': 90,
                'details': self.hs_to_details.get(keyword, {})
            }
        
        # Try fuzzy match (medium confidence)
        fuzzy = self.fuzzy_match(description)
        if fuzzy:
            hs_code, score = fuzzy
            logger.info(f"Fuzzy match found: {hs_code} (score: {score})")
            return {
                'hs_code': hs_code,
                'method': 'fuzzy',
                'confidence': score,
                'details': self.hs_to_details.get(hs_code, {})
            }
        
        # Try token match (lower confidence)
        token = self.token_match(description)
        if token:
            logger.info(f"Token match found: {token}")
            return {
                'hs_code': token,
                'method': 'token',
                'confidence': 60,
                'details': self.hs_to_details.get(token, {})
            }
        
        # Default fallback based on product category keywords
        logger.info(f"No match found, using default fallback")
        default_hs = self._get_default_hs_code(description)
        return {
            'hs_code': default_hs,
            'method': 'default',
            'confidence': 30,
            'details': {}
        }
    
    def _get_default_hs_code(self, description: str) -> str:
        """
        Get a default HS code based on product category keywords.
        
        Args:
            description: Product description
            
        Returns:
            Default HS code
        """
        description = description.upper()
        
        # Check for category keywords
        if any(word in description for word in ['SHIRT', 'BLOUSE', 'TOP', 'TUNIC']):
            return '62053000'  # Shirts
        elif any(word in description for word in ['PANT', 'SHORT', 'TROUSER']):
            return '62034990'  # Pants
        elif any(word in description for word in ['HAT', 'CAP', 'VISOR']):
            return '65040000'  # Hats
        elif any(word in description for word in ['BAG', 'PURSE', 'CLUTCH', 'CROSSBODY']):
            return '42022900'  # Bags
        elif any(word in description for word in ['SANDAL', 'SHOE', 'FOOTWEAR']):
            return '64052000'  # Footwear
        elif any(word in description for word in ['BRACELET', 'NECKLACE', 'EARRING', 'RING', 'JEWELRY']):
            return '71179000'  # Jewelry
        elif any(word in description for word in ['SWIMSUIT', 'BIKINI', 'SWIM']):
            return '62111200'  # Swimwear
        
        # Default to jewelry as a safe fallback
        return '71179000'
