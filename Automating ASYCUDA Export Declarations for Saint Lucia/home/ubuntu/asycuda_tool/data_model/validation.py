"""
Validation system for ASYCUDA export declarations.

This module provides functionality to validate ASYCUDA declarations against
field requirements, data consistency rules, and format specifications.
"""

from typing import Dict, List, Optional, Tuple, Any
import re
import logging
import pandas as pd
from datetime import datetime

from .asycuda_data_model import Declaration, Item, Entity

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


class ValidationResult:
    """
    Represents the result of a validation operation.
    """
    
    def __init__(self, is_valid: bool = True, errors: List[str] = None, warnings: List[str] = None):
        """
        Initialize validation result.
        
        Args:
            is_valid: Whether the validation passed
            errors: List of error messages
            warnings: List of warning messages
        """
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def add_error(self, error: str):
        """
        Add an error message and set is_valid to False.
        
        Args:
            error: Error message
        """
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """
        Add a warning message.
        
        Args:
            warning: Warning message
        """
        self.warnings.append(warning)
    
    def merge(self, other: 'ValidationResult'):
        """
        Merge with another validation result.
        
        Args:
            other: ValidationResult to merge with
        """
        self.is_valid = self.is_valid and other.is_valid
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
    
    def __str__(self) -> str:
        """String representation of validation result."""
        status = "Valid" if self.is_valid else "Invalid"
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        
        return f"ValidationResult: {status} ({error_count} errors, {warning_count} warnings)"


class FieldValidator:
    """
    Validates individual fields against ASYCUDA requirements.
    """
    
    # Field constraints
    MAX_LENGTHS = {
        'registration_number': 20,
        'declaration_type': 3,
        'customs_office': 5,
        'exporter_id': 20,
        'exporter_name': 70,
        'declarant_id': 20,
        'declarant_name': 70,
        'general_procedure_code': 4,
        'extended_procedure_code': 3,
        'country_of_destination': 2,
        'mode_of_transport': 2,
        'office_of_entry_exit': 5,
        'currency_code': 3,
        'commercial_reference': 35,
        'hs_code': 10,
        'description': 280,
        'country_of_origin': 2,
        'package_type': 2,
        'marks_and_numbers': 140,
        'previous_document': 50,
    }
    
    # Regular expression patterns
    PATTERNS = {
        'registration_number': r'^[A-Z0-9]+$',
        'declaration_type': r'^EX[1-3]$',
        'customs_office': r'^LC[A-Z]{2,3}$',
        'general_procedure_code': r'^\d{4}$',
        'extended_procedure_code': r'^\d{3}$',
        'country_code': r'^[A-Z]{2}$',
        'currency_code': r'^[A-Z]{3}$',
        'hs_code': r'^\d{6,10}$',
        'numeric': r'^\d+(\.\d+)?$',
        'date': r'^\d{2}/\d{2}/\d{4}$',
    }
    
    @classmethod
    def validate_length(cls, field_name: str, value: str) -> ValidationResult:
        """
        Validate field length against maximum allowed.
        
        Args:
            field_name: Name of the field to validate
            value: Value to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        max_length = cls.MAX_LENGTHS.get(field_name)
        if max_length and len(str(value)) > max_length:
            result.add_error(
                f"Field '{field_name}' exceeds maximum length of {max_length} characters"
            )
        
        return result
    
    @classmethod
    def validate_pattern(cls, pattern_name: str, value: str) -> ValidationResult:
        """
        Validate field value against a regular expression pattern.
        
        Args:
            pattern_name: Name of the pattern to use
            value: Value to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        pattern = cls.PATTERNS.get(pattern_name)
        if pattern and not re.match(pattern, str(value)):
            result.add_error(
                f"Value '{value}' does not match required pattern for {pattern_name}"
            )
        
        return result
    
    @classmethod
    def validate_numeric(cls, field_name: str, value: Any) -> ValidationResult:
        """
        Validate numeric field.
        
        Args:
            field_name: Name of the field to validate
            value: Value to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        try:
            float_value = float(value)
            if float_value < 0:
                result.add_error(
                    f"Field '{field_name}' must be a positive number"
                )
        except (ValueError, TypeError):
            result.add_error(
                f"Field '{field_name}' must be a valid number"
            )
        
        return result
    
    @classmethod
    def validate_date(cls, field_name: str, value: Any) -> ValidationResult:
        """
        Validate date field.
        
        Args:
            field_name: Name of the field to validate
            value: Value to validate (string or datetime)
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        if isinstance(value, datetime):
            return result
        
        if isinstance(value, str):
            try:
                # Try to parse date string in DD/MM/YYYY format
                if re.match(r'^\d{2}/\d{2}/\d{4}$', value):
                    day, month, year = map(int, value.split('/'))
                    datetime(year, month, day)
                    return result
                # Try to parse ISO format
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return result
            except (ValueError, TypeError):
                pass
        
        result.add_error(
            f"Field '{field_name}' must be a valid date"
        )
        
        return result


class DeclarationValidator:
    """
    Validates ASYCUDA declarations against field requirements and data consistency rules.
    """
    
    def __init__(self):
        """Initialize the declaration validator."""
        pass
    
    def validate_declaration(self, declaration: Declaration) -> ValidationResult:
        """
        Validate a complete declaration.
        
        Args:
            declaration: Declaration to validate
            
        Returns:
            ValidationResult
        """
        logger.info(f"Validating declaration {declaration.registration_number}")
        
        result = ValidationResult()
        
        # Validate header fields
        header_result = self._validate_header(declaration)
        result.merge(header_result)
        
        # Validate exporter
        exporter_result = self._validate_entity(declaration.exporter, "exporter")
        result.merge(exporter_result)
        
        # Validate declarant
        declarant_result = self._validate_entity(declaration.declarant, "declarant")
        result.merge(declarant_result)
        
        # Validate items
        for idx, item in enumerate(declaration.items):
            item_result = self._validate_item(item, idx + 1)
            result.merge(item_result)
        
        # Validate cross-field consistency
        consistency_result = self._validate_consistency(declaration)
        result.merge(consistency_result)
        
        return result
    
    def _validate_header(self, declaration: Declaration) -> ValidationResult:
        """
        Validate declaration header fields.
        
        Args:
            declaration: Declaration to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        # Check required fields
        required_fields = [
            'registration_number',
            'declaration_type',
            'customs_office',
            'general_procedure_code',
            'extended_procedure_code',
            'country_of_destination',
            'mode_of_transport',
            'office_of_entry_exit',
            'currency_code',
            'exchange_rate',
            'date',
        ]
        
        for field in required_fields:
            if not hasattr(declaration, field) or getattr(declaration, field) is None or getattr(declaration, field) == '':
                result.add_error(f"Required field '{field}' is missing")
        
        # Validate field formats
        if hasattr(declaration, 'registration_number') and declaration.registration_number:
            length_result = FieldValidator.validate_length('registration_number', declaration.registration_number)
            result.merge(length_result)
            
            pattern_result = FieldValidator.validate_pattern('registration_number', declaration.registration_number)
            result.merge(pattern_result)
        
        if hasattr(declaration, 'declaration_type') and declaration.declaration_type:
            pattern_result = FieldValidator.validate_pattern('declaration_type', declaration.declaration_type)
            result.merge(pattern_result)
        
        if hasattr(declaration, 'customs_office') and declaration.customs_office:
            pattern_result = FieldValidator.validate_pattern('customs_office', declaration.customs_office)
            result.merge(pattern_result)
        
        if hasattr(declaration, 'general_procedure_code') and declaration.general_procedure_code:
            pattern_result = FieldValidator.validate_pattern('general_procedure_code', declaration.general_procedure_code)
            result.merge(pattern_result)
        
        if hasattr(declaration, 'extended_procedure_code') and declaration.extended_procedure_code:
            pattern_result = FieldValidator.validate_pattern('extended_procedure_code', declaration.extended_procedure_code)
            result.merge(pattern_result)
        
        if hasattr(declaration, 'country_of_destination') and declaration.country_of_destination:
            pattern_result = FieldValidator.validate_pattern('country_code', declaration.country_of_destination)
            result.merge(pattern_result)
        
        if hasattr(declaration, 'currency_code') and declaration.currency_code:
            pattern_result = FieldValidator.validate_pattern('currency_code', declaration.currency_code)
            result.merge(pattern_result)
        
        if hasattr(declaration, 'exchange_rate') and declaration.exchange_rate is not None:
            numeric_result = FieldValidator.validate_numeric('exchange_rate', declaration.exchange_rate)
            result.merge(numeric_result)
        
        # Check for items
        if not declaration.items:
            result.add_error("Declaration must have at least one item")
        
        return result
    
    def _validate_entity(self, entity: Entity, entity_type: str) -> ValidationResult:
        """
        Validate an entity (exporter or declarant).
        
        Args:
            entity: Entity to validate
            entity_type: Type of entity ('exporter' or 'declarant')
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        # Check required fields
        required_fields = ['id', 'name', 'address_line1']
        
        for field in required_fields:
            if not hasattr(entity, field) or getattr(entity, field) is None or getattr(entity, field) == '':
                result.add_error(f"Required field '{field}' is missing for {entity_type}")
        
        # Validate field formats
        if hasattr(entity, 'id') and entity.id:
            length_result = FieldValidator.validate_length(f'{entity_type}_id', entity.id)
            result.merge(length_result)
        
        if hasattr(entity, 'name') and entity.name:
            length_result = FieldValidator.validate_length(f'{entity_type}_name', entity.name)
            result.merge(length_result)
        
        if hasattr(entity, 'country') and entity.country:
            pattern_result = FieldValidator.validate_pattern('country_code', entity.country)
            result.merge(pattern_result)
        
        return result
    
    def _validate_item(self, item: Item, item_number: int) -> ValidationResult:
        """
        Validate a declaration item.
        
        Args:
            item: Item to validate
            item_number: Item number for error messages
            
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        # Check required fields
        required_fields = [
            'hs_code',
            'description',
            'country_of_origin',
            'gross_weight',
            'net_weight',
            'statistical_unit',
            'quantity',
            'customs_value',
            'package_type',
            'package_count',
        ]
        
        for field in required_fields:
            if not hasattr(item, field) or getattr(item, field) is None or getattr(item, field) == '':
                result.add_error(f"Required field '{field}' is missing for item {item_number}")
        
        # Validate field formats
        if hasattr(item, 'hs_code') and item.hs_code:
            pattern_result = FieldValidator.validate_pattern('hs_code', item.hs_code)
            result.merge(pattern_result)
        
        if hasattr(item, 'description') and item.description:
            length_result = FieldValidator.validate_length('description', item.description)
            result.merge(length_result)
        
        if hasattr(item, 'country_of_origin') and item.country_of_origin:
            pattern_result = FieldValidator.validate_pattern('country_code', item.country_of_origin)
            result.merge(pattern_result)
        
        if hasattr(item, 'gross_weight') and item.gross_weight is not None:
            numeric_result = FieldValidator.validate_numeric('gross_weight', item.gross_weight)
            result.merge(numeric_result)
        
        if hasattr(item, 'net_weight') and item.net_weight is not None:
            numeric_result = FieldValidator.validate_numeric('net_weight', item.net_weight)
            result.merge(numeric_result)
        
        if hasattr(item, 'quantity') and item.quantity is not None:
            numeric_result = FieldValidator.validate_numeric('quantity', item.quantity)
            result.merge(numeric_result)
        
        if hasattr(item, 'customs_value') and item.customs_value is not None:
            numeric_result = FieldValidator.validate_numeric('customs_value', item.customs_value)
            result.merge(numeric_result)
        
        if hasattr(item, 'package_count') and item.package_count is not None:
            numeric_result = FieldValidator.validate_numeric('package_count', item.package_count)
            result.merge(numeric_result)
        
        # Cross-field validations
        if (hasattr(item, 'gross_weight') and item.gross_weight is not None and 
            hasattr(item, 'net_weight') and item.net_weight is not None):
            if item.net
(Content truncated due to size limit. Use line ranges to read in chunks)