"""
ASYCUDA Data Model for Saint Lucia Export Declarations

This module defines the core data structures for ASYCUDA-compliant export declarations.
It includes classes for the main declaration and its components, with validation rules
and data type constraints based on ASYCUDA requirements.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union
from datetime import datetime
from enum import Enum
import re


class DeclarationType(Enum):
    """
    ASYCUDA declaration types for exports.
    """
    EX1 = "EX1"  # Permanent export
    EX2 = "EX2"  # Temporary export
    EX3 = "EX3"  # Re-export


class CustomsOffice(Enum):
    """
    Customs office codes for Saint Lucia.
    """
    LCVFP = "VIEUX-FORT PORT"
    LCHB = "HEWANORRA"
    LCCAP = "CASTRIES PORT"
    LCVGC = "VIGIE CUSTOMS"


class PackageType(Enum):
    """
    Package types used in ASYCUDA.
    """
    PE = "PIECES"
    BX = "BOX"
    CT = "CARTON"
    PK = "PACKAGE"


class UnitOfMeasurement(Enum):
    """
    Units of measurement used in ASYCUDA.
    """
    NMB = "NUMBER"
    KGM = "KILOGRAM"
    LTR = "LITER"
    MTR = "METER"
    SQM = "SQUARE METER"


class CountryCode(Enum):
    """
    ISO country codes commonly used in Saint Lucia exports.
    """
    US = "UNITED STATES"
    ES = "SPAIN"
    GB = "UNITED KINGDOM"
    CA = "CANADA"
    LC = "SAINT LUCIA"
    VC = "VARIOUS"


class TransportMode(Enum):
    """
    Transport modes used in ASYCUDA.
    """
    VC = "VARIOUS AIRLINES"
    AA = "AMERICAN AIRLINES"
    DL = "DELTA AIRLINES"
    BA = "BRITISH AIRWAYS"
    VS = "VIRGIN ATLANTIC"
    BW = "CARIBBEAN AIRLINES"


class ValidationError(Exception):
    """
    Exception raised for validation errors in the ASYCUDA data model.
    """
    pass


@dataclass
class Entity:
    """
    Represents an entity such as exporter, importer, or declarant.
    """
    id: str
    name: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str = ""
    country: str = "LC"  # Default to Saint Lucia

    def validate(self):
        """Validate entity data."""
        if not self.id or not self.name or not self.address_line1:
            raise ValidationError("Entity ID, name, and address are required")
        if len(self.id) > 20:
            raise ValidationError("Entity ID must be 20 characters or less")
        return True


@dataclass
class Item:
    """
    Represents a single item in the declaration.
    """
    item_number: int
    hs_code: str
    description: str
    country_of_origin: str
    gross_weight: float
    net_weight: float
    statistical_unit: str = "NMB"  # Default to NUMBER
    quantity: float = 1.0
    customs_value: float = 0.0
    package_type: str = "PE"  # Default to PIECES
    package_count: int = 1
    marks_and_numbers: str = "NO MARKS"
    previous_document: Optional[str] = None
    
    def validate(self):
        """Validate item data."""
        # HS Code validation (6-10 digits)
        if not re.match(r'^\d{6,10}$', self.hs_code):
            raise ValidationError(f"Invalid HS Code format: {self.hs_code}")
        
        # Country code validation (2 letters)
        if not re.match(r'^[A-Z]{2}$', self.country_of_origin):
            raise ValidationError(f"Invalid country code: {self.country_of_origin}")
        
        # Weight validation
        if self.gross_weight <= 0:
            raise ValidationError("Gross weight must be positive")
        if self.net_weight <= 0:
            raise ValidationError("Net weight must be positive")
        if self.net_weight > self.gross_weight:
            raise ValidationError("Net weight cannot exceed gross weight")
        
        # Quantity validation
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        # Package count validation
        if self.package_count <= 0:
            raise ValidationError("Package count must be positive")
        
        # Description validation
        if not self.description or len(self.description) < 3:
            raise ValidationError("Description is required and must be meaningful")
        
        return True


@dataclass
class Declaration:
    """
    Represents a complete ASYCUDA export declaration.
    """
    # Core declaration fields
    registration_number: str
    declaration_type: str  # EX1, EX2, EX3
    customs_office: str  # LCVFP, LCHB, etc.
    exporter: Entity
    declarant: Entity
    general_procedure_code: str = "3071"  # Default for duty-free exports
    extended_procedure_code: str = "113"  # Default for duty-free exports
    country_of_destination: str = "VC"  # Default to VARIOUS
    mode_of_transport: str = "VC"  # Default to VARIOUS AIRLINES
    office_of_entry_exit: str = "LCHB"  # Default to HEWANORRA
    currency_code: str = "XCD"  # Default to East Caribbean Dollar
    exchange_rate: float = 1.0  # Default exchange rate
    total_packages: int = 0  # Will be calculated
    commercial_reference: str = ""
    date: datetime = field(default_factory=datetime.now)
    
    # Additional fields
    valuation_method: str = "1"  # Default method
    delivery_terms: str = "CIF"  # Default to CIF
    place_of_loading: Optional[str] = None
    manifest_reference: Optional[str] = None
    warehouse_identification: Optional[str] = None
    declarant_signature: Optional[str] = None
    
    # Items in the declaration
    items: List[Item] = field(default_factory=list)
    
    def add_item(self, item: Item):
        """Add an item to the declaration."""
        # Assign item number if not already set
        if item.item_number <= 0:
            item.item_number = len(self.items) + 1
        self.items.append(item)
        self.total_packages += item.package_count
    
    def calculate_totals(self):
        """Calculate declaration totals."""
        self.total_packages = sum(item.package_count for item in self.items)
        return {
            'total_value': sum(item.customs_value for item in self.items),
            'total_gross_weight': sum(item.gross_weight for item in self.items),
            'total_net_weight': sum(item.net_weight for item in self.items),
            'total_packages': self.total_packages,
            'total_items': len(self.items)
        }
    
    def validate(self):
        """Validate the entire declaration."""
        # Validate core fields
        if not self.registration_number:
            raise ValidationError("Registration number is required")
        
        if self.declaration_type not in [t.value for t in DeclarationType]:
            raise ValidationError(f"Invalid declaration type: {self.declaration_type}")
        
        if self.customs_office not in [o.name for o in CustomsOffice]:
            raise ValidationError(f"Invalid customs office: {self.customs_office}")
        
        # Validate entities
        self.exporter.validate()
        self.declarant.validate()
        
        # Validate procedure codes
        if not re.match(r'^\d{4}$', self.general_procedure_code):
            raise ValidationError(f"Invalid general procedure code: {self.general_procedure_code}")
        
        if not re.match(r'^\d{3}$', self.extended_procedure_code):
            raise ValidationError(f"Invalid extended procedure code: {self.extended_procedure_code}")
        
        # Validate country codes
        if self.country_of_destination not in [c.name for c in CountryCode]:
            raise ValidationError(f"Invalid country of destination: {self.country_of_destination}")
        
        # Validate transport mode
        if self.mode_of_transport not in [m.name for m in TransportMode]:
            raise ValidationError(f"Invalid mode of transport: {self.mode_of_transport}")
        
        # Validate items
        if not self.items:
            raise ValidationError("Declaration must have at least one item")
        
        for item in self.items:
            item.validate()
        
        return True


@dataclass
class ReferenceData:
    """
    Reference data for HS codes, product descriptions, and other lookup values.
    """
    hs_code_mappings: Dict[str, str] = field(default_factory=dict)  # description -> HS code
    country_of_origin_mappings: Dict[str, str] = field(default_factory=dict)  # product -> country
    weight_estimates: Dict[str, Dict[str, float]] = field(default_factory=dict)  # HS code -> {gross, net}
    previous_document_mappings: Dict[str, str] = field(default_factory=dict)  # product -> document reference
    
    def add_hs_mapping(self, description: str, hs_code: str):
        """Add a mapping from product description to HS code."""
        self.hs_code_mappings[description.upper()] = hs_code
    
    def add_country_mapping(self, product: str, country: str):
        """Add a mapping from product to country of origin."""
        self.country_of_origin_mappings[product.upper()] = country
    
    def add_weight_estimate(self, hs_code: str, gross: float, net: float):
        """Add weight estimates for a product category."""
        self.weight_estimates[hs_code] = {'gross': gross, 'net': net}
    
    def add_document_reference(self, product: str, document_ref: str):
        """Add a previous document reference for a product."""
        self.previous_document_mappings[product.upper()] = document_ref
    
    def get_hs_code(self, description: str) -> Optional[str]:
        """Get HS code for a product description using fuzzy matching."""
        # Simple exact match for now - will be enhanced with fuzzy matching
        return self.hs_code_mappings.get(description.upper())
    
    def get_country_of_origin(self, product: str) -> str:
        """Get country of origin for a product."""
        # Default to US if not found
        return self.country_of_origin_mappings.get(product.upper(), "US")
    
    def get_weight_estimates(self, hs_code: str) -> Dict[str, float]:
        """Get weight estimates for a product category."""
        # Default weights if not found
        return self.weight_estimates.get(hs_code, {'gross': 0.5, 'net': 0.3})
    
    def get_document_reference(self, product: str) -> Optional[str]:
        """Get previous document reference for a product."""
        return self.previous_document_mappings.get(product.upper())


@dataclass
class AsycudaExportManager:
    """
    Main manager class for ASYCUDA export declarations.
    """
    reference_data: ReferenceData = field(default_factory=ReferenceData)
    
    def create_declaration(self, 
                          registration_number: str,
                          declaration_type: str,
                          customs_office: str,
                          exporter: Entity,
                          declarant: Entity,
                          commercial_reference: str = "",
                          **kwargs) -> Declaration:
        """Create a new declaration with the required fields."""
        return Declaration(
            registration_number=registration_number,
            declaration_type=declaration_type,
            customs_office=customs_office,
            exporter=exporter,
            declarant=declarant,
            commercial_reference=commercial_reference,
            **kwargs
        )
    
    def process_sales_data(self, 
                          sales_data: List[Dict],
                          declaration: Declaration) -> Declaration:
        """
        Process sales data and add items to the declaration.
        
        Args:
            sales_data: List of dictionaries containing sales data
            declaration: The declaration to add items to
            
        Returns:
            Updated declaration with items added
        """
        for idx, sale in enumerate(sales_data, start=1):
            # Extract data from sale record
            description = sale.get('ITEM SOLD', '').strip()
            if not description:
                continue  # Skip empty items
                
            # Get or estimate required values
            hs_code = self.reference_data.get_hs_code(description) or "71179000"  # Default HS code
            country_of_origin = self.reference_data.get_country_of_origin(description)
            weight_estimates = self.reference_data.get_weight_estimates(hs_code)
            previous_document = self.reference_data.get_document_reference(description)
            
            # Create item
            item = Item(
                item_number=idx,
                hs_code=hs_code,
                description=description,
                country_of_origin=country_of_origin,
                gross_weight=weight_estimates['gross'],
                net_weight=weight_estimates['net'],
                customs_value=float(sale.get('DF US$', 0)),
                quantity=float(sale.get('number', 1)),
                previous_document=previous_document
            )
            
            # Add item to declaration
            declaration.add_item(item)
        
        return declaration
