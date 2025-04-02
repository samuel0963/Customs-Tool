"""
Weight estimation functionality for ASYCUDA export declarations.

This module provides functionality to estimate gross and net weights for products
based on HS codes and descriptions, which are required fields in ASYCUDA declarations.
"""

from typing import Dict, List, Optional, Tuple, Any
import re
import logging
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
        
        # Keyword-based weight estimates
        self.keyword_weights = {
            'SHIRT': {'gross': 0.3, 'net': 0.25},
            'BLOUSE': {'gross': 0.2, 'net': 0.15},
            'PANT': {'gross': 0.5, 'net': 0.45},
            'SHORT': {'gross': 0.3, 'net': 0.25},
            'DRESS': {'gross': 0.4, 'net': 0.35},
            'SWIMSUIT': {'gross': 0.3, 'net': 0.25},
            'BIKINI': {'gross': 0.2, 'net': 0.15},
            'HAT': {'gross': 0.2, 'net': 0.15},
            'CAP': {'gross': 0.2, 'net': 0.15},
            'VISOR': {'gross': 0.15, 'net': 0.1},
            'BAG': {'gross': 0.5, 'net': 0.45},
            'CROSSBODY': {'gross': 0.4, 'net': 0.35},
            'CLUTCH': {'gross': 0.3, 'net': 0.25},
            'SANDAL': {'gross': 0.5, 'net': 0.4},
            'SHOE': {'gross': 0.6, 'net': 0.5},
            'BRACELET': {'gross': 0.05, 'net': 0.03},
            'NECKLACE': {'gross': 0.05, 'net': 0.03},
            'EARRING': {'gross': 0.02, 'net': 0.01},
            'RING': {'gross': 0.02, 'net': 0.01},
            'SCRUNCHIE': {'gross': 0.05, 'net': 0.03},
            'SARONG': {'gross': 0.3, 'net': 0.25},
            'PAREO': {'gross': 0.3, 'net': 0.25},
            'TUNIC': {'gross': 0.3, 'net': 0.25},
            'TOP': {'gross': 0.2, 'net': 0.15},
            'BOTTOM': {'gross': 0.3, 'net': 0.25},
            'RASHGUARD': {'gross': 0.3, 'net': 0.25}
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
    
    def add_keyword_mapping(self, keyword: str, gross: float, net: float):
        """
        Add a weight mapping for a product keyword.
        
        Args:
            keyword: Product keyword (uppercase)
            gross: Gross weight in kg
            net: Net weight in kg
        """
        self.keyword_weights[keyword.upper()] = {'gross': gross, 'net': net}
    
    def load_weight_mappings_from_dataframe(self, df: pd.DataFrame, 
                                          hs_col: str, 
                                          gross_col: str, 
                                          net_col: str):
        """
        Load weight mappings from a DataFrame.
        
        Args:
            df: DataFrame containing weight mappings
            hs_col: Column name for HS codes
            gross_col: Column name for gross weights
            net_col: Column name for net weights
        """
        for _, row in df.iterrows():
            try:
                hs_code = str(row[hs_col]).strip()
                gross = float(row[gross_col])
                net = float(row[net_col])
                
                if len(hs_code) >= 4:
                    hs_prefix = hs_code[:4]
                    self.add_weight_mapping(hs_prefix, gross, net)
            except Exception as e:
                logger.warning(f"Error loading weight mapping: {e}")
    
    def estimate_by_hs_code(self, hs_code: str) -> Dict[str, float]:
        """
        Estimate weights based on HS code.
        
        Args:
            hs_code: HS code of the product
            
        Returns:
            Dictionary with gross and net weights
        """
        if not hs_code:
            return self.default_weights['default']
        
        # Try to match by HS code prefix (first 4 digits)
        for prefix_length in [4, 2]:
            if len(hs_code) >= prefix_length:
                prefix = hs_code[:prefix_length]
                for mapping_prefix, weights in self.default_weights.items():
                    if mapping_prefix.startswith(prefix):
                        return weights
        
        # Default fallback
        return self.default_weights['default']
    
    def estimate_by_description(self, description: str) -> Dict[str, float]:
        """
        Estimate weights based on product description.
        
        Args:
            description: Product description
            
        Returns:
            Dictionary with gross and net weights
        """
        if not description:
            return self.default_weights['default']
        
        description_upper = description.upper()
        
        # Check for keywords in the description
        for keyword, weights in self.keyword_weights.items():
            if keyword in description_upper:
                return weights
        
        # Default fallback
        return self.default_weights['default']
    
    def estimate_weights(self, hs_code: Optional[str] = None, description: Optional[str] = None, quantity: float = 1.0) -> Dict[str, float]:
        """
        Estimate gross and net weights for a product.
        
        Args:
            hs_code: HS code of the product
            description: Product description for additional context
            quantity: Quantity of the product
            
        Returns:
            Dictionary with gross and net weights
        """
        # Try HS code-based estimation first
        if hs_code:
            weights = self.estimate_by_hs_code(hs_code)
        # Fall back to description-based estimation
        elif description:
            weights = self.estimate_by_description(description)
        # Use default weights if neither is available
        else:
            weights = self.default_weights['default']
        
        # Adjust for quantity
        return {
            'gross': weights['gross'] * quantity,
            'net': weights['net'] * quantity
        }
    
    def analyze_product_weights(self, products_df: pd.DataFrame, 
                              description_col: str, 
                              hs_code_col: Optional[str] = None) -> pd.DataFrame:
        """
        Analyze and estimate weights for a set of products.
        
        Args:
            products_df: DataFrame containing product data
            description_col: Column name for product descriptions
            hs_code_col: Optional column name for HS codes
            
        Returns:
            DataFrame with added weight columns
        """
        # Create a copy to avoid modifying the original
        result_df = products_df.copy()
        
        # Add weight columns
        result_df['estimated_gross_weight'] = 0.0
        result_df['estimated_net_weight'] = 0.0
        
        # Process each product
        for idx, row in result_df.iterrows():
            description = str(row[description_col]) if not pd.isna(row[description_col]) else ""
            hs_code = str(row[hs_code_col]) if hs_code_col and not pd.isna(row[hs_code_col]) else None
            quantity = float(row['quantity']) if 'quantity' in row and not pd.isna(row['quantity']) else 1.0
            
            weights = self.estimate_weights(hs_code, description, quantity)
            
            result_df.at[idx, 'estimated_gross_weight'] = weights['gross']
            result_df.at[idx, 'estimated_net_weight'] = weights['net']
        
        return result_df
