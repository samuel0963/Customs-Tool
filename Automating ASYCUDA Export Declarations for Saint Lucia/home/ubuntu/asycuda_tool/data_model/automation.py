"""
Automation scheduling system for ASYCUDA export declarations.

This module provides functionality to schedule automatic processing of sales reports
and generation of ASYCUDA-compliant export declarations on a daily, weekly, or monthly basis.
"""

import os
import glob
import json
import logging
import sys
from datetime import datetime
import traceback
import shutil
import time
import threading
import schedule
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from .asycuda_data_model import Declaration, Item, Entity
from .field_mapper import FieldMapper
from .format_generators import FormatGeneratorFactory
from .error_handling import AsycudaExportManager, ErrorHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ScheduleConfig:
    """
    Configuration for scheduled processing of sales reports.
    """
    
    def __init__(self, 
               schedule_type: str,
               sales_file_pattern: str,
               output_dir: str,
               reference_data_path: Optional[str] = None,
               exporter: Optional[Entity] = None,
               declarant: Optional[Entity] = None,
               settings: Optional[Dict[str, Any]] = None):
        """
        Initialize schedule configuration.
        
        Args:
            schedule_type: Type of schedule ('daily', 'weekly', 'monthly')
            sales_file_pattern: Pattern for sales files (e.g., '/path/to/sales_*.xlsx')
            output_dir: Directory for output files
            reference_data_path: Optional path to reference data file
            exporter: Optional exporter entity
            declarant: Optional declarant entity
            settings: Optional settings dictionary
        """
        self.schedule_type = schedule_type
        self.sales_file_pattern = sales_file_pattern
        self.output_dir = output_dir
        self.reference_data_path = reference_data_path
        self.exporter = exporter
        self.declarant = declarant
        self.settings = settings
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'schedule_type': self.schedule_type,
            'sales_file_pattern': self.sales_file_pattern,
            'output_dir': self.output_dir,
            'reference_data_path': self.reference_data_path,
            'exporter': self.exporter.to_dict() if self.exporter else None,
            'declarant': self.declarant.to_dict() if self.declarant else None,
            'settings': self.settings,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduleConfig':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            ScheduleConfig instance
        """
        # Create exporter entity if provided
        exporter = None
        if data.get('exporter'):
            exporter = Entity(
                id=data['exporter'].get('id', ''),
                name=data['exporter'].get('name', ''),
                address_line1=data['exporter'].get('address_line1', ''),
                address_line2=data['exporter'].get('address_line2', ''),
                city=data['exporter'].get('city', ''),
                country=data['exporter'].get('country', '')
            )
        
        # Create declarant entity if provided
        declarant = None
        if data.get('declarant'):
            declarant = Entity(
                id=data['declarant'].get('id', ''),
                name=data['declarant'].get('name', ''),
                address_line1=data['declarant'].get('address_line1', ''),
                address_line2=data['declarant'].get('address_line2', ''),
                city=data['declarant'].get('city', ''),
                country=data['declarant'].get('country', '')
            )
        
        # Create instance
        instance = cls(
            schedule_type=data.get('schedule_type', 'daily'),
            sales_file_pattern=data.get('sales_file_pattern', ''),
            output_dir=data.get('output_dir', ''),
            reference_data_path=data.get('reference_data_path'),
            exporter=exporter,
            declarant=declarant,
            settings=data.get('settings')
        )
        
        # Set created_at if provided
        if data.get('created_at'):
            try:
                instance.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass
        
        return instance
    
    def save(self, config_path: Optional[str] = None) -> str:
        """
        Save configuration to file.
        
        Args:
            config_path: Optional path to save configuration
            
        Returns:
            Path to saved configuration file
        """
        if not config_path:
            config_path = os.path.join(self.output_dir, 'schedule_config.json')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Save configuration
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        
        return config_path
    
    @classmethod
    def load(cls, config_path: str) -> 'ScheduleConfig':
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            ScheduleConfig instance
        """
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        return cls.from_dict(data)


class ScheduledTask:
    """
    Represents a scheduled task for processing sales reports.
    """
    
    def __init__(self, config: ScheduleConfig):
        """
        Initialize scheduled task.
        
        Args:
            config: Schedule configuration
        """
        self.config = config
        self.last_run = None
        self.next_run = None
        self.status = 'pending'
        self.error = None
        self.log_dir = os.path.join(config.output_dir, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
    
    def run(self):
        """Run the scheduled task."""
        try:
            logger.info(f"Running scheduled task for {self.config.schedule_type} processing")
            self.status = 'running'
            self.last_run = datetime.now()
            
            # Find sales files matching pattern
            sales_files = glob.glob(self.config.sales_file_pattern)
            logger.info(f"Found {len(sales_files)} sales files matching pattern")
            
            # Process each sales file
            for sales_file in sales_files:
                try:
                    logger.info(f"Processing sales file: {sales_file}")
                    
                    # Create output directory for this file
                    file_basename = os.path.splitext(os.path.basename(sales_file))[0]
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_subdir = os.path.join(self.config.output_dir, f"{file_basename}_{timestamp}")
                    os.makedirs(output_subdir, exist_ok=True)
                    
                    # Process sales file
                    export_manager = AsycudaExportManager(log_dir=self.log_dir)
                    result = export_manager.process_sales_file(
                        sales_file_path=sales_file,
                        reference_data_path=self.config.reference_data_path,
                        exporter=self.config.exporter,
                        declarant=self.config.declarant,
                        settings=self.config.settings
                    )
                    
                    # Check result
                    if result['success']:
                        logger.info(f"Successfully processed sales file: {sales_file}")
                        
                        # Save export formats
                        if result['export_formats'].get('xml'):
                            xml_path = os.path.join(output_subdir, f"{file_basename}.xml")
                            with open(xml_path, 'w') as f:
                                f.write(result['export_formats']['xml'])
                            logger.info(f"Saved XML to {xml_path}")
                        
                        if result['export_formats'].get('txt'):
                            txt_path = os.path.join(output_subdir, f"{file_basename}.txt")
                            with open(txt_path, 'w') as f:
                                f.write(result['export_formats']['txt'])
                            logger.info(f"Saved pipe-delimited text to {txt_path}")
                        
                        if result['export_formats'].get('excel'):
                            excel_path = os.path.join(output_subdir, f"{file_basename}.xlsx")
                            with open(excel_path, 'wb') as f:
                                f.write(result['export_formats']['excel'].getvalue())
                            logger.info(f"Saved Excel to {excel_path}")
                        
                        if result['export_formats'].get('pdf'):
                            pdf_path = os.path.join(output_subdir, f"{file_basename}.pdf")
                            with open(pdf_path, 'wb') as f:
                                f.write(result['export_formats']['pdf'].getvalue())
                            logger.info(f"Saved PDF to {pdf_path}")
                        
                        # Save validation results
                        validation_path = os.path.join(output_subdir, "validation_results.json")
                        validation_json = {}
                        for context, validation in result['validation_results'].items():
                            validation_json[context] = {
                                'is_valid': validation.is_valid,
                                'errors': validation.errors,
                                'warnings': validation.warnings
                            }
                        
                        with open(validation_path, 'w') as f:
                            json.dump(validation_json, f, indent=2)
                        logger.info(f"Saved validation results to {validation_path}")
                        
                        # Move processed file to archive if all validations passed
                        all_valid = all(v.is_valid for v in result['validation_results'].values())
                        if all_valid:
                            archive_dir = os.path.join(self.config.output_dir, 'archive')
                            os.makedirs(archive_dir, exist_ok=True)
                            archive_path = os.path.join(archive_dir, os.path.basename(sales_file))
                            
                            # Only move if not already in archive directory
                            if os.path.dirname(sales_file) != archive_dir:
                                shutil.move(sales_file, archive_path)
                                logger.info(f"Moved processed file to {archive_path}")
                    else:
                        logger.error(f"Failed to process sales file: {sales_file}")
                        if result.get('error'):
                            logger.error(f"Error: {result['error'].get('error_message', 'Unknown error')}")
                        
                        # Save error details
                        error_path = os.path.join(output_subdir, "error_details.json")
                        with open(error_path, 'w') as f:
                            json.dump(result.get('error', {'error_message': 'Unknown error'}), f, indent=2)
                        logger.info(f"Saved error details to {error_path}")
                
                except Exception as e:
                    logger.error(f"Error processing sales file {sales_file}: {str(e)}")
                    logger.error(traceback.format_exc())
            
            self.status = 'completed'
            logger.info("Completed scheduled task run")
            
        except Exception as e:
            self.status = 'failed'
            self.error = str(e)
            logger.error(f"Scheduled task error: {str(e)}")
            logger.error(traceback.format_exc())
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get task status.
        
        Returns:
            Dictionary with task status
        """
        return {
            'status': self.status,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'error': self.error,
            'config': self.config.to_dict()
        }


class ScheduleManager:
    """
    Manages scheduled tasks for processing sales reports.
    """
    
    def __init__(self):
        """Initialize schedule manager."""
        self.tasks = {}
        self.running = False
        self.thread = None
    
    def add_task(self, task_id: str, config: ScheduleConfig) -> str:
        """
        Add a scheduled task.
        
        Args:
            task_id: Task identifier
            config: Schedule configuration
            
        Returns:
            Task identifier
        """
        # Create task
        task = ScheduledTask(config)
        
        # Add to tasks
        self.tasks[task_id] = task
        
        # Schedule task
        self._schedule_task(task_id, task)
        
        return task_id
    
    def remove_task(self, task_id: str):
        """
        Remove a scheduled task.
        
        Args:
            task_id: Task identifier
        """
        if task_id in self.tasks:
            # Clear schedule
            schedule.clear(task_id)
            
            # Remove from tasks
            del self.tasks[task_id]
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """
        Get a scheduled task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            ScheduledTask if found, None otherwise
        """
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, ScheduledTask]:
        """
        Get all scheduled tasks.
        
        Returns:
            Dictionary of task identifier to ScheduledTask
        """
        return self.tasks
    
    def start(self):
        """Start the schedule manager."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler)
            self.thread.daemon = True
            self.thread.start()
    
    def stop(self):
        """Stop the schedule manager."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
    
    def _schedule_task(self, task_id: str, task: ScheduledTask):
        """
        Schedule a task.
        
        Args:
            task_id: Task identifier
            task: ScheduledTask to schedule
        """
        # Define job function
        def job():
            task.run()
        
        # Schedule based on type
        if task.config.schedule_type == 'daily':
            schedule.every().day.at("01:00").do(job).tag(task_id)
            task.next_run = schedule.next_run()
        elif task.config.schedule_type == 'weekly':
            schedule.every().monday.at("01:00").do(job).tag(task_id)
            task.next_run = schedule.next_run()
        elif task.con
(Content truncated due to size limit. Use line ranges to read in chunks)