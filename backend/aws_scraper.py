#!/usr/bin/env python3
"""
AWS Architecture Scraper - MongoDB Version

This module handles scraping AWS architectures using aws-list-all
and manages the scraping process with MongoDB storage and temporary files.
"""
import os
import shutil
import subprocess
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pathlib import Path
from mongodb_manager import MongoDBManager
from file_watcher import FileWatcherService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AWSArchitectureScraper:
    """AWS Architecture Scraper with MongoDB storage"""
    
    def __init__(self, mongo_connection_string: str = "mongodb://localhost:27017",
                 temp_base_directory: str = "/tmp"):
        """Initialize scraper with MongoDB connection"""
        self.mongo_manager = MongoDBManager(mongo_connection_string)
        self.file_watcher = FileWatcherService(self.mongo_manager)
        self.temp_base_directory = temp_base_directory
        
        logger.info("AWS Architecture Scraper initialized with MongoDB storage")
    
    def generate_scrape_id(self) -> str:
        """Generate unique scrape identifier"""
        timestamp = datetime.now(timezone.utc)
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        return f"scrape_{timestamp_str}_{unique_id}"
    
    def scrape_aws_architecture(self, 
                               services: Optional[List[str]] = None,
                               regions: Optional[List[str]] = None,
                               profile: Optional[str] = None) -> Dict[str, Any]:
        """Execute complete scraping workflow with MongoDB storage"""
        
        scrape_id = self.generate_scrape_id()
        start_time = datetime.now(timezone.utc)
        temp_dir = os.path.join(self.temp_base_directory, scrape_id)
        
        logger.info(f"Starting AWS scrape: {scrape_id}")
        
        # Create initial scrape metadata
        scrape_metadata = {
            'scrape_id': scrape_id,
            'start_time': start_time,
            'end_time': None,
            'duration_seconds': None,
            'success': False,
            'return_code': None,
            'command': None,
            'services': services or "all",
            'regions': regions or [],
            'profile': profile,
            'scraped_files_count': 0,
            'total_resources_saved': 0,
            'temp_directory': temp_dir,
            'files_processed_to_mongo': 0,
            'temp_files_cleaned': False
        }
        
        try:
            # Save initial metadata to MongoDB
            self.mongo_manager.save_scrape_metadata(scrape_metadata)
            
            # Start file watcher
            self.file_watcher.start_watching(temp_dir, scrape_id)
            
            # Execute aws-list-all
            result = self._execute_aws_list_all(temp_dir, services, regions, profile)
            
            # Update command in metadata
            scrape_metadata['command'] = result['command']
            scrape_metadata['return_code'] = result['return_code']
            
            # Wait for file processing completion
            files_in_dir = self._count_json_files(temp_dir)
            logger.info(f"Found {files_in_dir} JSON files to process")
            
            if files_in_dir > 0:
                processing_complete = self.file_watcher.wait_for_completion(
                    expected_files=files_in_dir, 
                    timeout=120
                )
                
                if not processing_complete:
                    logger.warning("File processing did not complete within timeout")
                    # Don't fail the entire scrape just because processing took too long
            else:
                # If no files were generated, give it a moment for any delayed file creation
                import time
                time.sleep(2)
                files_in_dir = self._count_json_files(temp_dir)
                logger.info(f"After waiting, found {files_in_dir} JSON files to process")

            # Update final metadata
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            processed_files = self.file_watcher.get_processed_files_count()
            
            scrape_metadata.update({
                'end_time': end_time,
                'duration_seconds': duration,
                'success': result['return_code'] == 0 if result['return_code'] is not None else False,
                'scraped_files_count': files_in_dir,
                'files_processed_to_mongo': processed_files,
                'total_resources_saved': processed_files  # Each file = one resource doc
            })
            
            # Update metadata in MongoDB
            self.mongo_manager.update_scrape_metadata(scrape_id, scrape_metadata)
            
            # Cleanup temporary files
            cleanup_success = self._cleanup_temp_directory(temp_dir)
            self.mongo_manager.update_scrape_metadata(scrape_id, {'temp_files_cleaned': cleanup_success})
            
            logger.info(f"Scrape completed: {scrape_id} (Success: {scrape_metadata['success']})")
            
            return {
                'scrape_id': scrape_id,
                'success': scrape_metadata['success'],
                'duration_seconds': duration,
                'files_processed': processed_files,
                'return_code': result['return_code']
            }
            
        except Exception as e:
            logger.error(f"Scrape failed: {e}")
            
            # Update metadata with error
            scrape_metadata.update({
                'end_time': datetime.now(timezone.utc),
                'success': False,
                'error': str(e)
            })
            self.mongo_manager.update_scrape_metadata(scrape_id, scrape_metadata)
            
            # Try to cleanup
            self._cleanup_temp_directory(temp_dir)
            
            raise
        
        finally:
            # Always stop file watcher
            self.file_watcher.stop_watching()
    
    def _execute_aws_list_all(self, temp_dir: str, services: Optional[List[str]], 
                             regions: Optional[List[str]], profile: Optional[str]) -> Dict[str, Any]:
        """Execute aws-list-all command"""
        
        # Build command
        command = ["aws-list-all", "query", "--directory", temp_dir]
        
        if regions:
            for region in regions:
                command.extend(["--region", region])
        
        if services and services != "all":
            for service in services:
                command.extend(["--service", service])
        
        if profile:
            command.extend(["--profile", profile])
        
        logger.info(f"Executing command: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            logger.info(f"aws-list-all completed with return code: {result.returncode}")
            
            if result.stdout:
                logger.debug(f"STDOUT: {result.stdout}")
            if result.stderr:
                logger.warning(f"STDERR: {result.stderr}")
            
            return {
                'command': command,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            logger.error("aws-list-all command timed out")
            return {
                'command': command,
                'return_code': -1,
                'stdout': '',
                'stderr': 'Command timed out'
            }
        except Exception as e:
            logger.error(f"Failed to execute aws-list-all: {e}")
            return {
                'command': command,
                'return_code': -1,
                'stdout': '',
                'stderr': str(e)
            }
    
    def _count_json_files(self, directory: str) -> int:
        """Count JSON files in directory (excluding metadata)"""
        try:
            directory_path = Path(directory)
            if not directory_path.exists():
                return 0
            
            json_files = [f for f in directory_path.glob("*.json") 
                         if 'metadata' not in f.name]
            return len(json_files)
        except Exception as e:
            logger.error(f"Failed to count JSON files: {e}")
            return 0
    
    def _cleanup_temp_directory(self, temp_dir: str) -> bool:
        """Remove temporary directory and all contents"""
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup temporary directory {temp_dir}: {e}")
            return False
    
    def list_scrapes(self, limit: int = 50, offset: int = 0, success_only: bool = False) -> List[Dict[str, Any]]:
        """List scrapes from MongoDB"""
        filters = {}
        if success_only:
            filters['success'] = True
        
        return self.mongo_manager.query_scrapes(filters, limit, offset)
    
    def get_scrape_details(self, scrape_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific scrape"""
        return self.mongo_manager.get_scrape_by_id(scrape_id)
    
    def query_resources(self, scrape_id: str, service: Optional[str] = None,
                       region: Optional[str] = None, operation: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query AWS resources with filtering"""
        filters = {'scrape_id': scrape_id}
        
        if service:
            filters['service'] = service
        if region:
            filters['region'] = region
        if operation:
            filters['operation'] = operation
        
        return self.mongo_manager.query_resources(filters)
    
    def delete_scrape(self, scrape_id: str) -> bool:
        """Delete a scrape and all associated resources"""
        return self.mongo_manager.delete_scrape(scrape_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return self.mongo_manager.get_stats()
    
    def close(self):
        """Close connections"""
        self.file_watcher.stop_watching()
        self.mongo_manager.close()


def main():
    """Main function for testing the scraper"""
    # Use docker-compose MongoDB connection string
    mongo_uri = "mongodb://mongodb:27017/cloudculate"
    
    print("🧪 Testing AWS Architecture Scraper (MongoDB Version)")
    print("=" * 60)
    
    try:
        # Initialize scraper with docker-compose MongoDB
        scraper = AWSArchitectureScraper(mongo_uri)
        print(f"✅ Connected to MongoDB: {mongo_uri}")
        
        # Test basic functionality
        stats = scraper.get_stats()
        print(f"📊 Current Statistics:")
        print(f"   Total Scrapes: {stats.get('total_scrapes', 0)}")
        print(f"   Total Resources: {stats.get('total_resources', 0)}")
        print(f"   Services Discovered: {len(stats.get('services_discovered', []))}")
        
        # Test with IAM and EC2 services that we know generate files
        print(f"\n🚀 Testing scrape (IAM and EC2 services in us-east-1)...")
        print("   This should generate multiple JSON files based on our test...")
        
        result = scraper.scrape_aws_architecture(
            services=["iam", "ec2"],
            regions=["us-east-1"]
        )
        
        if result['success']:
            print(f"✅ Test scrape completed successfully!")
            print(f"   Scrape ID: {result['scrape_id']}")
            print(f"   Duration: {result.get('duration_seconds', 0):.2f} seconds")
            print(f"   Files processed: {result.get('files_processed', 0)}")
            
            # Show sample resources
            if result.get('files_processed', 0) > 0:
                resources = scraper.query_resources(result['scrape_id'])[:5]  # Get first 5
                print(f"   Sample resources saved to MongoDB:")
                for i, resource in enumerate(resources, 1):
                    service = resource.get('service', 'unknown')
                    operation = resource.get('operation', 'unknown')
                    region = resource.get('region', 'unknown')
                    print(f"     {i}. {service} - {operation} ({region})")
        else:
            print(f"❌ Test scrape failed")
            print(f"   Scrape ID: {result['scrape_id']}")
            print(f"   Return code: {result.get('return_code', 'N/A')}")
        
        scraper.close()
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"\n💡 Make sure MongoDB is running: docker-compose up -d mongodb")
        return 1

if __name__ == "__main__":
    exit(main())
