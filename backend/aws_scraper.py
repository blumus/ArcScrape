#!/usr/bin/env python3
"""
AWS Architecture Scraper

This module handles scraping AWS architectures using aws-list-all
and manages the scraping process with proper logging and tracking.
"""

import os
import subprocess
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pathlib import Path
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AWSArchitectureScraper:
    """AWS Architecture Scraper using aws-list-all"""
    
    def __init__(self, base_directory: str = "./aws-inventory"):
        """
        Initialize the scraper
        
        Args:
            base_directory: Base directory for storing scrapes
        """
        self.base_directory = Path(base_directory)
        self.base_directory.mkdir(exist_ok=True)
        
        # Create subdirectories for organization
        (self.base_directory / "scrapes").mkdir(exist_ok=True)
        (self.base_directory / "logs").mkdir(exist_ok=True)
        (self.base_directory / "status").mkdir(exist_ok=True)
        
    def generate_scrape_id(self) -> str:
        """Generate a unique scrape ID with timestamp"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"scrape_{timestamp}_{unique_id}"
    
    def scrape_aws_architecture(self, 
                               services: Optional[List[str]] = None,
                               regions: Optional[List[str]] = None,
                               profile: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape AWS architecture using aws-list-all
        
        Args:
            services: List of AWS services to scrape (if None, scrapes all)
            regions: List of AWS regions to scrape
            profile: AWS profile to use
            
        Returns:
            Dict with scrape results and metadata
        """
        scrape_id = self.generate_scrape_id()
        scrape_start_time = datetime.now(timezone.utc)
        
        logger.info(f"Starting AWS scrape: {scrape_id}")
        
        # Create directories for this scrape
        scrape_dir = self.base_directory / "scrapes" / scrape_id
        scrape_dir.mkdir(exist_ok=True)
        
        log_dir = self.base_directory / "logs" / scrape_id
        log_dir.mkdir(exist_ok=True)
        
        status_dir = self.base_directory / "status" / scrape_id
        status_dir.mkdir(exist_ok=True)
        
        # Build aws-list-all command
        cmd = ["aws-list-all", "query", "--directory", str(scrape_dir)]
        
        # Add services if specified
        if services:
            for service in services:
                cmd.extend(["--service", service])
        
        # Add regions if specified
        if regions:
            for region in regions:
                cmd.extend(["--region", region])
        
        # Add profile if specified
        if profile:
            cmd.extend(["--profile", profile])
        
        # Setup log files
        stdout_file = log_dir / "stdout.log"
        stderr_file = log_dir / "stderr.log"
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        try:
            # Run aws-list-all command
            with open(stdout_file, 'w') as stdout, open(stderr_file, 'w') as stderr:
                result = subprocess.run(
                    cmd,
                    stdout=stdout,
                    stderr=stderr,
                    text=True,
                    timeout=3600  # 1 hour timeout
                )
            
            scrape_end_time = datetime.now(timezone.utc)
            duration = (scrape_end_time - scrape_start_time).total_seconds()
            
            # Determine success/failure
            success = result.returncode == 0
            
            # Create status files
            if success:
                success_file = status_dir / "success"
                success_file.touch()
                logger.info(f"Scrape {scrape_id} completed successfully in {duration:.2f}s")
            else:
                fail_file = status_dir / "fail"
                fail_file.touch()
                logger.error(f"Scrape {scrape_id} failed with return code {result.returncode}")
            
            # Count scraped files
            scraped_files = list(scrape_dir.glob("**/*.json"))
            file_count = len(scraped_files)
            
            # Create metadata
            metadata = {
                "scrape_id": scrape_id,
                "start_time": scrape_start_time.isoformat(),
                "end_time": scrape_end_time.isoformat(),
                "duration_seconds": duration,
                "success": success,
                "return_code": result.returncode,
                "command": cmd,
                "services": services or "all",
                "regions": regions or "all",
                "profile": profile,
                "scraped_files_count": file_count,
                "scrape_directory": str(scrape_dir),
                "log_directory": str(log_dir),
                "status_directory": str(status_dir)
            }
            
            # Save metadata
            metadata_file = scrape_dir / "scrape_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Also save in status directory
            status_metadata_file = status_dir / "metadata.json"
            with open(status_metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return metadata
            
        except subprocess.TimeoutExpired:
            logger.error(f"Scrape {scrape_id} timed out")
            fail_file = status_dir / "fail"
            fail_file.touch()
            
            scrape_end_time = datetime.now(timezone.utc)
            duration = (scrape_end_time - scrape_start_time).total_seconds()
            
            metadata = {
                "scrape_id": scrape_id,
                "start_time": scrape_start_time.isoformat(),
                "end_time": scrape_end_time.isoformat(),
                "duration_seconds": duration,
                "success": False,
                "error": "timeout",
                "command": cmd,
                "services": services or "all",
                "regions": regions or "all",
                "profile": profile
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error during scrape {scrape_id}: {e}")
            fail_file = status_dir / "fail"
            fail_file.touch()
            
            scrape_end_time = datetime.now(timezone.utc)
            duration = (scrape_end_time - scrape_start_time).total_seconds()
            
            metadata = {
                "scrape_id": scrape_id,
                "start_time": scrape_start_time.isoformat(),
                "end_time": scrape_end_time.isoformat(),
                "duration_seconds": duration,
                "success": False,
                "error": str(e),
                "command": cmd,
                "services": services or "all",
                "regions": regions or "all",
                "profile": profile
            }
            
            return metadata
    
    def list_scrapes(self) -> List[Dict[str, Any]]:
        """
        List all scrapes with their status
        
        Returns:
            List of scrape metadata
        """
        scrapes = []
        
        scrapes_dir = self.base_directory / "scrapes"
        if not scrapes_dir.exists():
            return scrapes
        
        for scrape_dir in sorted(scrapes_dir.iterdir()):
            if scrape_dir.is_dir():
                metadata_file = scrape_dir / "scrape_metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        scrapes.append(metadata)
                    except Exception as e:
                        logger.warning(f"Could not read metadata for {scrape_dir}: {e}")
        
        return sorted(scrapes, key=lambda x: x.get('start_time', ''), reverse=True)
    
    def get_scrape_details(self, scrape_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific scrape
        
        Args:
            scrape_id: ID of the scrape
            
        Returns:
            Scrape metadata and details
        """
        scrape_dir = self.base_directory / "scrapes" / scrape_id
        metadata_file = scrape_dir / "scrape_metadata.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Add file listings
            scraped_files = []
            if scrape_dir.exists():
                for json_file in scrape_dir.glob("**/*.json"):
                    if json_file.name != "scrape_metadata.json":
                        file_info = {
                            "filename": json_file.name,
                            "relative_path": str(json_file.relative_to(scrape_dir)),
                            "size_bytes": json_file.stat().st_size,
                            "modified_time": datetime.fromtimestamp(
                                json_file.stat().st_mtime, tz=timezone.utc
                            ).isoformat()
                        }
                        scraped_files.append(file_info)
            
            metadata["scraped_files"] = scraped_files
            
            # Add log content if available
            log_dir = self.base_directory / "logs" / scrape_id
            if log_dir.exists():
                stdout_file = log_dir / "stdout.log"
                stderr_file = log_dir / "stderr.log"
                
                if stdout_file.exists():
                    with open(stdout_file, 'r') as f:
                        metadata["stdout"] = f.read()
                
                if stderr_file.exists():
                    with open(stderr_file, 'r') as f:
                        metadata["stderr"] = f.read()
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error reading scrape details for {scrape_id}: {e}")
            return None
    
    def get_successful_scrapes(self) -> List[Dict[str, Any]]:
        """Get list of successful scrapes"""
        return [scrape for scrape in self.list_scrapes() if scrape.get('success', False)]
    
    def get_failed_scrapes(self) -> List[Dict[str, Any]]:
        """Get list of failed scrapes"""
        return [scrape for scrape in self.list_scrapes() if not scrape.get('success', True)]
    
    def cleanup_old_scrapes(self, days_to_keep: int = 30):
        """
        Clean up old scrapes older than specified days
        
        Args:
            days_to_keep: Number of days to keep scrapes
        """
        cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_to_keep)
        
        cleaned_count = 0
        
        for scrape in self.list_scrapes():
            scrape_date = datetime.fromisoformat(scrape['start_time'].replace('Z', '+00:00'))
            if scrape_date < cutoff_date:
                scrape_id = scrape['scrape_id']
                try:
                    # Remove scrape directory
                    scrape_dir = self.base_directory / "scrapes" / scrape_id
                    if scrape_dir.exists():
                        import shutil
                        shutil.rmtree(scrape_dir)
                    
                    # Remove log directory
                    log_dir = self.base_directory / "logs" / scrape_id
                    if log_dir.exists():
                        shutil.rmtree(log_dir)
                    
                    # Remove status directory
                    status_dir = self.base_directory / "status" / scrape_id
                    if status_dir.exists():
                        shutil.rmtree(status_dir)
                    
                    cleaned_count += 1
                    logger.info(f"Cleaned up old scrape: {scrape_id}")
                    
                except Exception as e:
                    logger.error(f"Error cleaning up scrape {scrape_id}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} old scrapes")
        return cleaned_count


def main():
    """CLI interface for AWS scraping"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AWS Architecture Scraper')
    parser.add_argument('--directory', default='./aws-inventory', 
                       help='Base directory for scrapes')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Start a new scrape')
    scrape_parser.add_argument('--service', action='append', dest='services',
                              help='AWS service to scrape (can be used multiple times)')
    scrape_parser.add_argument('--region', action='append', dest='regions',
                              help='AWS region to scrape (can be used multiple times)')
    scrape_parser.add_argument('--profile', help='AWS profile to use')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all scrapes')
    
    # Details command
    details_parser = subparsers.add_parser('details', help='Get scrape details')
    details_parser.add_argument('scrape_id', help='Scrape ID to get details for')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old scrapes')
    cleanup_parser.add_argument('--days', type=int, default=30,
                               help='Number of days to keep scrapes')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    scraper = AWSArchitectureScraper(args.directory)
    
    if args.command == 'scrape':
        result = scraper.scrape_aws_architecture(
            services=args.services,
            regions=args.regions,
            profile=args.profile
        )
        print(json.dumps(result, indent=2))
    
    elif args.command == 'list':
        scrapes = scraper.list_scrapes()
        print(f"Total scrapes: {len(scrapes)}")
        print(f"Successful: {len([s for s in scrapes if s.get('success')])}")
        print(f"Failed: {len([s for s in scrapes if not s.get('success')])}")
        print()
        
        for scrape in scrapes[:10]:  # Show last 10
            status = "✅" if scrape.get('success') else "❌"
            print(f"{status} {scrape['scrape_id']} - {scrape['start_time']} "
                  f"({scrape.get('scraped_files_count', 0)} files)")
    
    elif args.command == 'details':
        details = scraper.get_scrape_details(args.scrape_id)
        if details:
            print(json.dumps(details, indent=2))
        else:
            print(f"Scrape not found: {args.scrape_id}")
    
    elif args.command == 'cleanup':
        cleaned = scraper.cleanup_old_scrapes(args.days)
        print(f"Cleaned up {cleaned} old scrapes")


if __name__ == "__main__":
    main()
