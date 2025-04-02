"""
Main field mapping system for ASYCUDA export declarations.

This module integrates all the specialized mapping components to provide a complete
system for transforming sales data into ASYCUDA-compliant export declarations.
"""

from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import logging
from datetime import datetime
import os

from .asycuda_data_model import Declaration, Item, Entity, ReferenceData
from .fuzzy_matcher import FuzzyMatcher
from .hs_code_lookup import HSCodeLookup
from .weight_estimator import WeightEstimator
from .document_reference import DocumentReferenceMapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FieldMapper:
    """
    Main field mapping system for ASYCUDA export declarations.
    """
    
    def __init__(self, reference_data_path: Optional[str] = None):
        """
        Initialize the field mapper.
        
        Args:
            reference_data_path: Optional path to reference data file
        """
        self.fuzzy_matcher = FuzzyMatcher()
        self.hs_lookup = HSCodeLookup(reference_data_path)
        self.weight_estimator = WeightEstimator()
        self.document_mapper = DocumentReferenceMapper()
        
        # Default values for required fields
        self.defaults = {
            'declaration_type': 'EX3',
            'customs_office': 'LCVFP',
            'general_procedure_code': '3071',
            'extended_procedure_code': '113',
            'country_of_destination': 'VC',
            'mode_of_transport': 'VC',
            'office_of_entry_exit': 'LCHB',
            'currency_code': 'XCD',
            'exchange_rate': 1.0,
            'valuation_method': '1',
            'delivery_terms': 'CIF',
            'statistical_unit': 'NMB',
            'package_type': 'PE',
            'marks_and_numbers': 'NO MARKS',
            'country_of_origin': 'US'
        }
        
        # Load reference data if provided
        if reference_data_path and os.path.exists(reference_data_path):
            self.load_reference_data(reference_data_path)
    
    def load_reference_data(self, file_path: str):
        """
        Load reference data from file.
        
        Args:
            file_path: Path to reference data file
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
            else:
                logger.error(f"Unsupported file format: {ext}")
                return
            
            # Load data into all components
            self.fuzzy_matcher.load_reference_data(df)
            self.hs_lookup.load_reference_data(file_path)
            self.document_mapper.load_from_anse_chastanet_format(df)
            
        except Exception as e:
            logger.error(f"Error loading reference data: {e}")
    
    def set_default(self, field: str, value: Any):
        """
        Set a default value for a field.
        
        Args:
            field: Field name
            value: Default value
        """
        self.defaults[field] = value
    
    def map_sales_to_declaration(self, 
                               sales_df: pd.DataFrame,
                               exporter: Entity,
                               declarant: Entity,
                               registration_number: str,
                               commercial_reference: str = None) -> Declaration:
        """
        Map sales data to an ASYCUDA declaration.
        
        Args:
            sales_df: DataFrame containing sales data
            exporter: Exporter entity
            declarant: Declarant entity
            registration_number: Registration number for the declaration
            commercial_reference: Optional commercial reference
            
        Returns:
            Populated Declaration object
        """
        logger.info(f"Mapping sales data with {len(sales_df)} rows to declaration")
        
        # Create a new declaration with default values
        declaration = Declaration(
            registration_number=registration_number,
            declaration_type=self.defaults['declaration_type'],
            customs_office=self.defaults['customs_office'],
            exporter=exporter,
            declarant=declarant,
            general_procedure_code=self.defaults['general_procedure_code'],
            extended_procedure_code=self.defaults['extended_procedure_code'],
            country_of_destination=self.defaults['country_of_destination'],
            mode_of_transport=self.defaults['mode_of_transport'],
            office_of_entry_exit=self.defaults['office_of_entry_exit'],
            currency_code=self.defaults['currency_code'],
            exchange_rate=self.defaults['exchange_rate'],
            valuation_method=self.defaults['valuation_method'],
            delivery_terms=self.defaults['delivery_terms'],
            commercial_reference=commercial_reference or "",
            date=datetime.now()
        )
        
        # Process each sales record
        for idx, row in sales_df.iterrows():
            try:
                # Skip rows with missing essential data
                if pd.isna(row.get('ITEM SOLD ')) or pd.isna(row.get('DF US$')):
                    logger.debug(f"Skipping row {idx} due to missing essential data")
                    continue
                
                # Extract basic item data
                description = str(row.get('ITEM SOLD ', '')).strip()
                bar_code = str(row.get('BAR CODE', '')).strip() if not pd.isna(row.get('BAR CODE')) else ""
                value = float(row.get('DF US$', 0))
                quantity = float(row.get('number', 1)) if not pd.isna(row.get('number')) else 1
                
                logger.debug(f"Processing item: {description}, barcode: {bar_code}, value: {value}, quantity: {quantity}")
                
                # Get HS code and related details
                hs_match = self.hs_lookup.lookup_hs_code(description)
                hs_code = hs_match['hs_code']
                origin = hs_match.get('details', {}).get('origin', self.defaults['country_of_origin'])
                
                logger.debug(f"HS code match: {hs_code}, origin: {origin}, method: {hs_match['method']}, confidence: {hs_match['confidence']}")
                
                # Estimate weights
                weights = self.weight_estimator.estimate_weights(hs_code, description, quantity)
                logger.debug(f"Estimated weights: gross={weights['gross']}, net={weights['net']}")
                
                # Get previous document reference
                prev_doc = self.document_mapper.get_document_reference(
                    product_code=bar_code,
                    description=description,
                    hs_code=hs_code
                )
                logger.debug(f"Document reference: {prev_doc}")
                
                # Create and add the item
                item = Item(
                    item_number=idx + 1,
                    hs_code=hs_code,
                    description=description,
                    country_of_origin=origin,
                    gross_weight=weights['gross'],
                    net_weight=weights['net'],
                    statistical_unit=self.defaults['statistical_unit'],
                    quantity=quantity,
                    customs_value=value,
                    package_type=self.defaults['package_type'],
                    package_count=int(quantity),
                    marks_and_numbers=self.defaults['marks_and_numbers'],
                    previous_document=prev_doc
                )
                
                declaration.add_item(item)
                
            except Exception as e:
                logger.error(f"Error processing row {idx}: {e}")
        
        logger.info(f"Created declaration with {len(declaration.items)} items")
        return declaration
    
    def map_vessel_to_transport(self, vessel_name: str) -> str:
        """
        Map vessel name to ASYCUDA transport code.
        
        Args:
            vessel_name: Vessel name from sales data
            
        Returns:
            Transport code for ASYCUDA
        """
        if not vessel_name or pd.isna(vessel_name):
            return self.defaults['mode_of_transport']
        
        vessel_upper = vessel_name.upper()
        
        # Map common airlines/vessels to codes
        transport_mapping = {
            'AMERICAN': 'AA',
            'DELTA': 'DL',
            'BRITISH': 'BA',
            'VIRGIN': 'VS',
            'CARIBBEAN': 'BW',
            'JETBLUE': 'B6',
            'UNITED': 'UA',
            'AIR CANADA': 'AC',
            'PRINCESS': 'VC',  # Cruise line
            'CARNIVAL': 'VC',  # Cruise line
            'ROYAL CARIBBEAN': 'VC',  # Cruise line
            'CELEBRITY': 'VC',  # Cruise line
            'NORWEGIAN': 'VC',  # Cruise line
        }
        
        for key, code in transport_mapping.items():
            if key in vessel_upper:
                return code
        
        return self.defaults['mode_of_transport']
    
    def map_port_to_office(self, port: str) -> str:
        """
        Map departure port to ASYCUDA office code.
        
        Args:
            port: Departure port from sales data
            
        Returns:
            Office code for ASYCUDA
        """
        if not port or pd.isna(port):
            return self.defaults['office_of_entry_exit']
        
        port_upper = port.upper()
        
        # Map common ports to office codes
        office_mapping = {
            'UVF': 'LCHB',  # Hewanorra International Airport
            'SLU': 'LCVGC',  # George F. L. Charles Airport
            'CASTRIES': 'LCCAP',  # Castries Port
            'VIEUX FORT': 'LCVFP',  # Vieux Fort Port
        }
        
        for key, code in office_mapping.items():
            if key in port_upper:
                return code
        
        return self.defaults['office_of_entry_exit']
    
    def map_place_to_country(self, place: str) -> str:
        """
        Map place of issue to country code.
        
        Args:
            place: Place of issue from sales data
            
        Returns:
            Country code for ASYCUDA
        """
        if not place or pd.isna(place):
            return self.defaults['country_of_destination']
        
        place_upper = place.upper()
        
        # Map common places to country codes
        country_mapping = {
            'USA': 'US',
            'UNITED STATES': 'US',
            'CANADA': 'CA',
            'UK': 'GB',
            'UNITED KINGDOM': 'GB',
            'ENGLAND': 'GB',
            'FRANCE': 'FR',
            'GERMANY': 'DE',
            'ITALY': 'IT',
            'SPAIN': 'ES',
            'SAINT LUCIA': 'LC',
            'ST LUCIA': 'LC',
            'ST. LUCIA': 'LC',
        }
        
        for key, code in country_mapping.items():
            if key in place_upper:
                return code
        
        return self.defaults['country_of_destination']
    
    def process_sales_file(self, 
                         sales_file_path: str, 
                         exporter: Entity,
                         declarant: Entity,
                         registration_number: str = None,
                         commercial_reference: str = None) -> Declaration:
        """
        Process a sales file and create an ASYCUDA declaration.
        
        Args:
            sales_file_path: Path to sales file (Excel)
            exporter: Exporter entity
            declarant: Declarant entity
            registration_number: Optional registration number (generated if not provided)
            commercial_reference: Optional commercial reference
            
        Returns:
            Populated Declaration object
        """
        logger.info(f"Processing sales file: {sales_file_path}")
        
        try:
            # Read sales data
            sales_df = pd.read_excel(sales_file_path)
            
            # Generate registration number if not provided
            if not registration_number:
                registration_number = f"A{datetime.now().strftime('%Y%m%d%H%M')}"
            
            # Generate commercial reference if not provided
            if not commercial_reference:
                commercial_reference = f"REF-{datetime.now().strftime('%Y%m%d')}"
            
            # Map sales data to declaration
            declaration = self.map_sales_to_declaration(
                sales_df=sales_df,
                exporter=exporter,
                declarant=declarant,
                registration_number=registration_number,
                commercial_reference=commercial_reference
            )
            
            return declaration
            
        except Exception as e:
            logger.error(f"Error processing sales file: {e}")
            raise
