"""
Field validation and constraints for ASYCUDA export declarations.

This module defines validation rules and constraints for ASYCUDA fields,
ensuring that all data meets the requirements for successful import into
ASYCUDA World.
"""

from typing import Dict, List, Any, Optional, Tuple
import re
from datetime import datetime


class FieldValidationError(Exception):
    """Exception raised for field validation errors."""
    pass


class FieldConstraints:
    """
    Defines constraints and validation rules for ASYCUDA fields.
    """
    
    # Maximum field lengths
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
    
    # Regular expression patterns for field validation
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
    
    # Required fields for declaration
    REQUIRED_DECLARATION_FIELDS = [
        'registration_number',
        'declaration_type',
        'customs_office',
        'exporter',
        'declarant',
        'general_procedure_code',
        'extended_procedure_code',
        'country_of_destination',
        'mode_of_transport',
        'office_of_entry_exit',
        'currency_code',
        'exchange_rate',
        'commercial_reference',
        'date',
    ]
    
    # Required fields for items
    REQUIRED_ITEM_FIELDS = [
        'item_number',
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
    
    @classmethod
    def validate_length(cls, field_name: str, value: str) -> bool:
        """
        Validate field length against maximum allowed.
        
        Args:
            field_name: Name of the field to validate
            value: Value to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        max_length = cls.MAX_LENGTHS.get(field_name)
        if max_length and len(str(value)) > max_length:
            raise FieldValidationError(
                f"Field '{field_name}' exceeds maximum length of {max_length} characters"
            )
        return True
    
    @classmethod
    def validate_pattern(cls, pattern_name: str, value: str) -> bool:
        """
        Validate field value against a regular expression pattern.
        
        Args:
            pattern_name: Name of the pattern to use
            value: Value to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        pattern = cls.PATTERNS.get(pattern_name)
        if pattern and not re.match(pattern, str(value)):
            raise FieldValidationError(
                f"Value '{value}' does not match required pattern for {pattern_name}"
            )
        return True
    
    @classmethod
    def validate_numeric(cls, field_name: str, value: Any) -> bool:
        """
        Validate numeric field.
        
        Args:
            field_name: Name of the field to validate
            value: Value to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        try:
            float_value = float(value)
            if float_value < 0:
                raise FieldValidationError(
                    f"Field '{field_name}' must be a positive number"
                )
        except (ValueError, TypeError):
            raise FieldValidationError(
                f"Field '{field_name}' must be a valid number"
            )
        return True
    
    @classmethod
    def validate_date(cls, field_name: str, value: Any) -> bool:
        """
        Validate date field.
        
        Args:
            field_name: Name of the field to validate
            value: Value to validate (string or datetime)
            
        Returns:
            True if valid, raises exception otherwise
        """
        if isinstance(value, datetime):
            return True
        
        if isinstance(value, str):
            try:
                # Try to parse date string in DD/MM/YYYY format
                if re.match(r'^\d{2}/\d{2}/\d{4}$', value):
                    day, month, year = map(int, value.split('/'))
                    datetime(year, month, day)
                    return True
                # Try to parse ISO format
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return True
            except (ValueError, TypeError):
                pass
        
        raise FieldValidationError(
            f"Field '{field_name}' must be a valid date"
        )
    
    @classmethod
    def validate_required_fields(cls, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Validate that all required fields are present and not empty.
        
        Args:
            data: Dictionary of field values
            required_fields: List of required field names
            
        Returns:
            True if valid, raises exception otherwise
        """
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                missing_fields.append(field)
        
        if missing_fields:
            raise FieldValidationError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )
        return True
    
    @classmethod
    def validate_declaration(cls, declaration_data: Dict[str, Any]) -> List[str]:
        """
        Validate all fields in a declaration.
        
        Args:
            declaration_data: Dictionary of declaration field values
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check required fields
        try:
            cls.validate_required_fields(declaration_data, cls.REQUIRED_DECLARATION_FIELDS)
        except FieldValidationError as e:
            errors.append(str(e))
        
        # Validate individual fields
        field_validations = [
            ('registration_number', 'validate_length', 'registration_number'),
            ('registration_number', 'validate_pattern', 'registration_number'),
            ('declaration_type', 'validate_pattern', 'declaration_type'),
            ('customs_office', 'validate_pattern', 'customs_office'),
            ('general_procedure_code', 'validate_pattern', 'general_procedure_code'),
            ('extended_procedure_code', 'validate_pattern', 'extended_procedure_code'),
            ('country_of_destination', 'validate_pattern', 'country_code'),
            ('mode_of_transport', 'validate_length', 'mode_of_transport'),
            ('office_of_entry_exit', 'validate_length', 'office_of_entry_exit'),
            ('currency_code', 'validate_pattern', 'currency_code'),
            ('exchange_rate', 'validate_numeric', None),
            ('commercial_reference', 'validate_length', 'commercial_reference'),
            ('date', 'validate_date', None),
        ]
        
        for field, validation_method, validation_param in field_validations:
            if field in declaration_data and declaration_data[field] is not None:
                try:
                    if validation_param:
                        getattr(cls, validation_method)(validation_param, declaration_data[field])
                    else:
                        getattr(cls, validation_method)(field, declaration_data[field])
                except FieldValidationError as e:
                    errors.append(str(e))
        
        return errors
    
    @classmethod
    def validate_item(cls, item_data: Dict[str, Any]) -> List[str]:
        """
        Validate all fields in a declaration item.
        
        Args:
            item_data: Dictionary of item field values
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check required fields
        try:
            cls.validate_required_fields(item_data, cls.REQUIRED_ITEM_FIELDS)
        except FieldValidationError as e:
            errors.append(str(e))
        
        # Validate individual fields
        field_validations = [
            ('item_number', 'validate_numeric', None),
            ('hs_code', 'validate_pattern', 'hs_code'),
            ('description', 'validate_length', 'description'),
            ('country_of_origin', 'validate_pattern', 'country_code'),
            ('gross_weight', 'validate_numeric', None),
            ('net_weight', 'validate_numeric', None),
            ('quantity', 'validate_numeric', None),
            ('customs_value', 'validate_numeric', None),
            ('package_type', 'validate_length', 'package_type'),
            ('package_count', 'validate_numeric', None),
        ]
        
        for field, validation_method, validation_param in field_validations:
            if field in item_data and item_data[field] is not None:
                try:
                    if validation_param:
                        getattr(cls, validation_method)(validation_param, item_data[field])
                    else:
                        getattr(cls, validation_method)(field, item_data[field])
                except FieldValidationError as e:
                    errors.append(str(e))
        
        # Additional cross-field validations
        if 'gross_weight' in item_data and 'net_weight' in item_data:
            try:
                gross = float(item_data['gross_weight'])
                net = float(item_data['net_weight'])
                if net > gross:
                    errors.append("Net weight cannot exceed gross weight")
            except (ValueError, TypeError):
                # Already caught by individual field validations
                pass
        
        return errors
