"""
Error handling and user experience improvements for ASYCUDA export declarations.

This module provides enhanced error handling, user feedback, and UX improvements
for the ASYCUDA export declaration automation tool.
"""

from typing import Dict, List, Optional, Tuple, Any
import logging
import traceback
import pandas as pd
import json
from datetime import datetime
import os

from .asycuda_data_model import Declaration, Item, Entity
from .validation import ValidationResult, ValidationService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Handles errors and provides user-friendly feedback.
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize the error handler.
        
        Args:
            log_dir: Optional directory for error logs
        """
        self.log_dir = log_dir
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
    
    def handle_exception(self, exception: Exception, context: str = "") -> Dict[str, Any]:
        """
        Handle an exception and provide user-friendly feedback.
        
        Args:
            exception: Exception to handle
            context: Context where the exception occurred
            
        Returns:
            Dictionary with error details
        """
        # Log the error
        logger.error(f"Error in {context}: {str(exception)}")
        logger.debug(traceback.format_exc())
        
        # Create error details
        error_details = {
            'error': str(exception),
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc(),
            'type': exception.__class__.__name__
        }
        
        # Log to file if log_dir is set
        if self.log_dir:
            self._log_to_file(error_details)
        
        # Return user-friendly error message
        return {
            'success': False,
            'error_message': self._get_user_friendly_message(exception, context),
            'error_details': error_details,
            'suggestions': self._get_error_suggestions(exception, context)
        }
    
    def handle_validation_result(self, validation_result: ValidationResult, context: str = "") -> Dict[str, Any]:
        """
        Handle a validation result and provide user-friendly feedback.
        
        Args:
            validation_result: ValidationResult to handle
            context: Context where the validation occurred
            
        Returns:
            Dictionary with validation details
        """
        # Log validation issues
        if not validation_result.is_valid:
            logger.warning(f"Validation failed in {context}: {len(validation_result.errors)} errors, {len(validation_result.warnings)} warnings")
            for error in validation_result.errors:
                logger.error(f"Validation error: {error}")
            for warning in validation_result.warnings:
                logger.warning(f"Validation warning: {warning}")
        
        # Create validation details
        validation_details = {
            'is_valid': validation_result.is_valid,
            'errors': validation_result.errors,
            'warnings': validation_result.warnings,
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
        
        # Log to file if log_dir is set and validation failed
        if self.log_dir and not validation_result.is_valid:
            self._log_to_file(validation_details, prefix="validation")
        
        # Return user-friendly validation message
        return {
            'success': validation_result.is_valid,
            'validation_message': self._get_validation_message(validation_result, context),
            'validation_details': validation_details,
            'suggestions': self._get_validation_suggestions(validation_result, context)
        }
    
    def _log_to_file(self, details: Dict[str, Any], prefix: str = "error"):
        """
        Log details to a file.
        
        Args:
            details: Details to log
            prefix: Prefix for the log file name
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.json"
            filepath = os.path.join(self.log_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(details, f, indent=2)
            
            logger.info(f"Logged details to {filepath}")
        
        except Exception as e:
            logger.error(f"Error logging to file: {str(e)}")
    
    def _get_user_friendly_message(self, exception: Exception, context: str) -> str:
        """
        Get a user-friendly error message.
        
        Args:
            exception: Exception to handle
            context: Context where the exception occurred
            
        Returns:
            User-friendly error message
        """
        # Map exception types to user-friendly messages
        exception_messages = {
            'FileNotFoundError': "The specified file could not be found. Please check the file path and try again.",
            'PermissionError': "You don't have permission to access this file or directory.",
            'ValueError': "Invalid value provided. Please check your input and try again.",
            'TypeError': "Incorrect data type provided. Please check your input and try again.",
            'KeyError': "Required field or key is missing. Please check your input and try again.",
            'IndexError': "Index out of range. Please check your input and try again.",
            'ImportError': "Required module could not be imported. Please check your installation.",
            'AttributeError': "Required attribute is missing. Please check your input and try again.",
            'ValidationError': "Validation failed. Please check the validation details and fix the issues."
        }
        
        # Get exception type
        exception_type = exception.__class__.__name__
        
        # Get context-specific message
        context_messages = {
            "sales_data_processing": "Error processing sales data. Please check your sales report format.",
            "reference_data_loading": "Error loading reference data. Please check your reference data format.",
            "declaration_generation": "Error generating declaration. Please check your input data and settings.",
            "export_format_generation": "Error generating export format. Please check your declaration data.",
            "validation": "Validation failed. Please check the validation details and fix the issues."
        }
        
        # Build message
        message = exception_messages.get(exception_type, f"An error occurred: {str(exception)}")
        
        if context in context_messages:
            message = f"{context_messages[context]} {message}"
        
        return message
    
    def _get_error_suggestions(self, exception: Exception, context: str) -> List[str]:
        """
        Get suggestions for fixing an error.
        
        Args:
            exception: Exception to handle
            context: Context where the exception occurred
            
        Returns:
            List of suggestions
        """
        # Map exception types to suggestions
        exception_suggestions = {
            'FileNotFoundError': [
                "Check if the file exists at the specified location",
                "Verify the file path is correct",
                "Ensure the file has not been moved or deleted"
            ],
            'PermissionError': [
                "Check if you have the necessary permissions to access the file",
                "Try running the application with administrator privileges",
                "Verify the file is not locked by another process"
            ],
            'ValueError': [
                "Check the format of your input data",
                "Ensure numeric fields contain valid numbers",
                "Verify date fields are in the correct format"
            ],
            'TypeError': [
                "Check the data types of your input",
                "Ensure required fields are provided",
                "Verify object properties are correctly defined"
            ],
            'KeyError': [
                "Check if the required field exists in your data",
                "Verify column names in your Excel file",
                "Ensure all required fields are provided"
            ],
            'ValidationError': [
                "Review the validation errors and fix each issue",
                "Check field formats and constraints",
                "Verify all required fields are provided"
            ]
        }
        
        # Get context-specific suggestions
        context_suggestions = {
            "sales_data_processing": [
                "Check your Excel file format and column names",
                "Ensure your sales data contains all required fields",
                "Verify numeric values are properly formatted"
            ],
            "reference_data_loading": [
                "Check your reference data file format",
                "Ensure your reference data contains all required columns",
                "Verify the reference data is in the expected format"
            ],
            "declaration_generation": [
                "Check your entity information (exporter and declarant)",
                "Verify default values are correctly set",
                "Ensure your sales data contains all required information"
            ],
            "export_format_generation": [
                "Check your declaration data for completeness",
                "Verify all required fields are provided",
                "Ensure the declaration is valid before generating export formats"
            ],
            "validation": [
                "Review each validation error and fix the corresponding issue",
                "Check field formats and constraints",
                "Verify all required fields are provided"
            ]
        }
        
        # Get exception type
        exception_type = exception.__class__.__name__
        
        # Combine suggestions
        suggestions = exception_suggestions.get(exception_type, [])
        
        if context in context_suggestions:
            suggestions.extend(context_suggestions[context])
        
        # Add general suggestions
        suggestions.append("Check the error logs for more details")
        suggestions.append("If the issue persists, contact support")
        
        return suggestions
    
    def _get_validation_message(self, validation_result: ValidationResult, context: str) -> str:
        """
        Get a user-friendly validation message.
        
        Args:
            validation_result: ValidationResult to handle
            context: Context where the validation occurred
            
        Returns:
            User-friendly validation message
        """
        if validation_result.is_valid:
            return "Validation passed successfully."
        
        error_count = len(validation_result.errors)
        warning_count = len(validation_result.warnings)
        
        message = f"Validation failed with {error_count} errors and {warning_count} warnings."
        
        # Add context-specific message
        context_messages = {
            "declaration": "The declaration contains validation errors that must be fixed before it can be submitted to ASYCUDA.",
            "xml_format": "The XML format contains validation errors that must be fixed before it can be imported into ASYCUDA.",
            "txt_format": "The pipe-delimited text format contains validation errors that must be fixed before it can be imported into ASYCUDA."
        }
        
        if context in context_messages:
            message = f"{message} {context_messages[context]}"
        
        return message
    
    def _get_validation_suggestions(self, validation_result: ValidationResult, context: str) -> List[str]:
        """
        Get suggestions for fixing validation issues.
        
        Args:
            validation_result: ValidationResult to handle
            context: Context where the validation occurred
            
        Returns:
            List of suggestions
        """
        if validation_result.is_valid:
            return ["No issues found."]
        
        # Start with general suggestions
        suggestions = [
            "Review each validation error and fix the corresponding issue",
            "Check field formats and constraints",
            "Verify all required fields are provided"
        ]
        
        # Add context-specific suggestions
        context_suggestions = {
            "declaration": [
                "Check exporter and declarant information",
                "Verify HS codes are in the correct format",
                "Ensure all items have the required fields",
                "Check numeric values are positive and in the correct range"
            ],
            "xml_format": [
                "Verify XML structure follows ASYCUDA requirements",
                "Check all required XML elements are present",
                "Ensure XML is well-formed and valid"
            ],
            "txt_format": [
                "Check pipe-delimited format follows ASYCUDA requirements",
                "Verify header line starts with 'H|'",
                "Ensure item lines start with 'I|'",
                "Check all lines have the correct number of fields"
            ]
        }
        
        if context in context_suggestions:
            suggestions.extend(context_suggestions[context])
        
        # Add specific suggestions based on common errors
        error_patterns = {
            "required field": "Provide values for all required fields",
            "maximum length": "Shorten field values that exceed maximum length",
            "pattern": "Correct field values to match required patterns",
            "numeric": "Ensure numeric fields contain valid positive numbers",
            "date": "Verify date fields are in the correct format",
            "net weight": "Ensure net weight does not exceed gross weight",
            "sequential": "Fix item numbers to be sequential starting from 1"
        }
        
        for error in validation_result.errors:
            for pattern, suggestion in error_patterns.items():
                if pattern.lower() in error.lower() and suggestion not in suggestions:
                    suggestions.append(suggestion)
        
        return suggestions


class UserFeedback:
    """
    Provides user feedback and progress updates.
    """
    
    def __init__(self):
        """Initialize the user feedback."""
        self.progress_steps = {}
        self.current_step = None
    
    def set_progress_steps(self, steps: List[str]):
        """
        Set the progress steps.
        
        Args:
            steps: List of progress step names
        """
        self.progress_steps = {step: {'status': 'pending', 'message': ''} for step in steps}
    
    def update_progress(self, step: str, status: str, message: str = ""):
        """
        Update progress for a step.
        
        Args:
            step: Step name
            status: Status ('pending', 'in_progress', 'completed', 'failed')
            message: Optional message
        """
        if step in self.progress_steps:
            self.progress_steps[step] = {'status': status, 'message': message}
            self.current_step = step
    
    def get_progress(self) -> Dict[str, Any]:
        """
        Get current progress.
        
        Returns:
            Dictionary with p
(Content truncated due to size limit. Use line ranges to read in chunks)