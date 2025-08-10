#!/usr/bin/env python3
"""
File Watcher Service for AWS Architecture Scraper

Monitors temporary directories for new JSON files and processes them
in real-time by saving to MongoDB collections.
"""
import os
import time
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread, Event
from typing import Dict, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from mongodb_manager import MongoDBManager

logger = logging.getLogger(__name__)

class FileWatcherHandler(FileSystemEventHandler):
    """Handle file system events for AWS JSON files"""
    
    def __init__(self, mongo_manager: MongoDBManager, scrape_id: str):
        self.mongo_manager = mongo_manager
        self.scrape_id = scrape_id
        self.processed_files = set()
        self.processing_files = set()  # Track files currently being processed
        
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
            
        file_path = event.src_path
        if file_path.endswith('.json') and 'metadata' not in file_path:
            logger.info(f"File created: {file_path}")
            # Don't process immediately, wait for file to be stable
            self._schedule_file_processing(file_path)
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
            
        file_path = event.src_path
        if file_path.endswith('.json') and 'metadata' not in file_path:
            # File is being modified, reschedule processing
            self._schedule_file_processing(file_path)
    
    def _schedule_file_processing(self, file_path: str):
        """Schedule file processing after ensuring file is stable"""
        if file_path in self.processing_files:
            return  # Already being processed
            
        self.processing_files.add(file_path)
        
        # Start a thread to wait for file stability and then process
        thread = Thread(
            target=self._wait_and_process_file, 
            args=(file_path,), 
            daemon=True
        )
        thread.start()
    
    def _wait_and_process_file(self, file_path: str):
        """Wait for file to be stable, then process it"""
        try:
            # Wait for file to be stable (no size changes for a period)
            stable_count = 0
            last_size = -1
            max_wait_time = 30  # Maximum wait time in seconds
            wait_start = time.time()
            
            while stable_count < 3 and (time.time() - wait_start) < max_wait_time:
                if not os.path.exists(file_path):
                    time.sleep(0.5)
                    continue
                    
                try:
                    current_size = os.path.getsize(file_path)
                    if current_size == last_size and current_size > 0:
                        stable_count += 1
                    else:
                        stable_count = 0
                        last_size = current_size
                    
                    time.sleep(0.5)  # Wait 500ms between checks
                except OSError:
                    # File might be locked, wait and try again
                    time.sleep(0.5)
                    continue
            
            # Additional wait to ensure file is completely written
            time.sleep(1)
            
            # Verify file is readable and contains valid JSON
            if self._is_file_ready(file_path):
                self._process_file(file_path)
            else:
                logger.warning(f"File {file_path} is not ready for processing after waiting")
                
        except Exception as e:
            logger.error(f"Error waiting for file stability {file_path}: {e}")
        finally:
            self.processing_files.discard(file_path)
    
    def _is_file_ready(self, file_path: str) -> bool:
        """Check if file is ready for processing"""
        try:
            # Check if file exists and has content
            if not os.path.exists(file_path):
                return False
                
            size = os.path.getsize(file_path)
            if size == 0:
                return False
            
            # Try to read and parse as JSON to ensure it's complete
            with open(file_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    return False
                    
                # Try to parse JSON to ensure it's valid
                json.loads(content)
                return True
                
        except (json.JSONDecodeError, OSError, IOError) as e:
            logger.debug(f"File {file_path} not ready: {e}")
            return False
    
    def _process_file(self, file_path: str):
        """Process a single JSON file"""
        if file_path in self.processed_files:
            return  # Already processed
            
        try:
            logger.info(f"Processing file: {file_path}")
            
            # Parse filename to extract metadata
            filename = os.path.basename(file_path)
            service, operation, region, account = self._parse_filename(filename)
            
            # Read and parse JSON content
            with open(file_path, 'r') as f:
                content = f.read().strip()
                
            if not content:
                logger.warning(f"Empty file: {file_path}")
                return
                
            try:
                json_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {file_path}: {e}")
                # Try to read file again after a short wait
                time.sleep(1)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read().strip()
                    json_data = json.loads(content)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON after retry: {file_path}")
                    return
            
            # Create resource document
            resource_doc = {
                'scrape_id': self.scrape_id,
                'service': service,
                'operation': operation,
                'region': region,
                'account': account,
                'filename': filename,
                'file_path': file_path,
                'scraped_at': datetime.now(timezone.utc),
                'data': json_data
            }
            
            # Save to MongoDB
            self.mongo_manager.save_resource(resource_doc)
            self.processed_files.add(file_path)
            
            logger.info(f"Successfully processed: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
    
    def _parse_filename(self, filename: str) -> tuple:
        """Parse AWS filename to extract service, operation, region, account"""
        # Remove .json extension
        name = filename.replace('.json', '')
        
        # Split by underscore
        parts = name.split('_')
        
        if len(parts) >= 4:
            service = parts[0]
            operation = parts[1]
            region = parts[2] if parts[2] != 'None' else None
            account = parts[3] if parts[3] != 'None' else None
        elif len(parts) >= 3:
            service = parts[0]
            operation = parts[1]
            region = parts[2] if parts[2] != 'None' else None
            account = None
        else:
            service = parts[0] if parts else 'unknown'
            operation = '_'.join(parts[1:]) if len(parts) > 1 else 'unknown'
            region = None
            account = None
            
        return service, operation, region, account
    
    def get_processed_count(self) -> int:
        """Get count of processed files"""
        return len(self.processed_files)


class FileWatcherService:
    """Service to watch directory for new AWS JSON files and process them"""
    
    def __init__(self, mongo_manager: MongoDBManager):
        self.mongo_manager = mongo_manager
        self.observer = None
        self.handler = None
        self.is_watching = False
        self.stop_event = Event()
        
    def start_watching(self, directory: str, scrape_id: str):
        """Start watching directory for new files"""
        if self.is_watching:
            self.stop_watching()
        
        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)
        
        self.handler = FileWatcherHandler(self.mongo_manager, scrape_id)
        self.observer = Observer()
        self.observer.schedule(self.handler, directory, recursive=False)
        
        self.observer.start()
        self.is_watching = True
        self.stop_event.clear()
        
        logger.info(f"Started watching directory: {directory}")
    
    def stop_watching(self):
        """Stop watching directory"""
        if self.observer and self.is_watching:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.is_watching = False
            self.stop_event.set()
            logger.info("Stopped file watching")
    
    def wait_for_completion(self, expected_files: int, timeout: int = 120) -> bool:
        """Wait for all files to be processed"""
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            if self.handler and self.handler.get_processed_count() >= expected_files:
                logger.info(f"All {expected_files} files processed successfully")
                return True
            
            if self.stop_event.is_set():
                break
                
            time.sleep(1)
        
        if self.handler:
            processed = self.handler.get_processed_count()
            logger.warning(f"Timeout: Only {processed}/{expected_files} files processed")
        
        return False
    
    def get_processed_files_count(self) -> int:
        """Get number of files processed"""
        if self.handler:
            return self.handler.get_processed_count()
        return 0