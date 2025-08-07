#!/usr/bin/env python3
"""
AWS Architecture Scraper Setup Script

This script sets up the AWS scraping system and runs initial tests.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_command_exists(command):
    """Check if a command exists in PATH"""
    try:
        subprocess.run([command, '--help'], 
                      capture_output=True, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_requirements():
    """Install Python requirements"""
    logger.info("📦 Installing Python requirements...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "-r", "requirements_scraper.txt"
        ])
        logger.info("✅ Python requirements installed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install requirements: {e}")
        return False


def install_aws_list_all():
    """Install aws-list-all"""
    logger.info("📦 Installing aws-list-all...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "aws-list-all"
        ])
        logger.info("✅ aws-list-all installed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install aws-list-all: {e}")
        return False


def check_aws_credentials():
    """Check if AWS credentials are configured"""
    logger.info("🔑 Checking AWS credentials...")
    
    # Check if AWS CLI is installed
    if not check_command_exists('aws'):
        logger.warning("⚠️  AWS CLI not found. Install with: pip install awscli")
        return False
    
    # Check if credentials are configured
    try:
        result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                              capture_output=True, 
                              text=True,
                              timeout=10)
        
        if result.returncode == 0:
            logger.info("✅ AWS credentials configured")
            return True
        else:
            logger.warning("⚠️  AWS credentials not configured or invalid")
            logger.info("💡 Configure with: aws configure")
            return False
            
    except subprocess.TimeoutExpired:
        logger.warning("⚠️  AWS credential check timed out")
        return False
    except Exception as e:
        logger.warning(f"⚠️  Could not check AWS credentials: {e}")
        return False


def setup_directories():
    """Create necessary directories"""
    logger.info("📁 Setting up directories...")
    
    base_dir = Path("./aws-inventory")
    
    directories = [
        base_dir,
        base_dir / "scrapes",
        base_dir / "logs", 
        base_dir / "status"
    ]
    
    for directory in directories:
        directory.mkdir(exist_ok=True)
        logger.info(f"   Created: {directory}")
    
    logger.info("✅ Directories created")
    return True


def test_scraper():
    """Run a basic test of the scraper"""
    logger.info("🧪 Testing scraper functionality...")
    
    try:
        from aws_scraper import AWSArchitectureScraper
        scraper = AWSArchitectureScraper("./aws-inventory")
        
        # Test basic functionality
        scrapes = scraper.list_scrapes()
        logger.info(f"✅ Scraper initialized, found {len(scrapes)} existing scrapes")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Could not import scraper: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Scraper test failed: {e}")
        return False


def run_demo_scrape():
    """Run a small demo scrape to test everything works"""
    logger.info("🎯 Running demo scrape...")
    
    if not check_aws_credentials():
        logger.warning("⚠️  Skipping demo scrape - AWS credentials not configured")
        return False
    
    try:
        from aws_scraper import AWSArchitectureScraper
        scraper = AWSArchitectureScraper("./aws-inventory")
        
        # Run a minimal scrape - just IAM (usually available in all accounts)
        result = scraper.scrape_aws_architecture(
            services=["iam"],
            regions=["us-east-1"]  # IAM is global, but specify region anyway
        )
        
        if result['success']:
            logger.info(f"✅ Demo scrape successful!")
            logger.info(f"   Scrape ID: {result['scrape_id']}")
            logger.info(f"   Files: {result.get('scraped_files_count', 0)}")
            logger.info(f"   Duration: {result.get('duration_seconds', 0):.2f}s")
            return True
        else:
            logger.warning(f"⚠️  Demo scrape completed but failed")
            logger.info(f"   Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Demo scrape failed: {e}")
        return False


def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup AWS Architecture Scraper')
    parser.add_argument('--skip-install', action='store_true', 
                       help='Skip installing requirements')
    parser.add_argument('--skip-demo', action='store_true', 
                       help='Skip running demo scrape')
    parser.add_argument('--start-server', action='store_true',
                       help='Start the web server after setup')
    
    args = parser.parse_args()
    
    print("🚀 AWS Architecture Scraper Setup")
    print("=" * 50)
    
    success_steps = 0
    total_steps = 6
    
    # Step 1: Install requirements
    if not args.skip_install:
        if install_requirements():
            success_steps += 1
        
        # Step 2: Install aws-list-all
        if install_aws_list_all():
            success_steps += 1
    else:
        logger.info("⏭️  Skipping installation steps")
        success_steps += 2
    
    # Step 3: Check aws-list-all
    if check_command_exists('aws-list-all'):
        logger.info("✅ aws-list-all is available")
        success_steps += 1
    else:
        logger.error("❌ aws-list-all not found")
    
    # Step 4: Setup directories
    if setup_directories():
        success_steps += 1
    
    # Step 5: Test scraper
    if test_scraper():
        success_steps += 1
    
    # Step 6: Check AWS credentials
    if check_aws_credentials():
        success_steps += 1
    
    # Optional: Demo scrape
    if not args.skip_demo and success_steps >= 5:  # Only if most things work
        logger.info("\n🎯 Running demo scrape...")
        if run_demo_scrape():
            logger.info("✅ Demo scrape successful!")
        else:
            logger.warning("⚠️  Demo scrape had issues (but setup is still OK)")
    
    # Summary
    print(f"\n📊 Setup Summary")
    print(f"Completed steps: {success_steps}/{total_steps}")
    
    if success_steps >= 5:
        print("✅ Setup completed successfully!")
        print("\n🎉 Ready to use!")
        print("\nNext steps:")
        print("1. Configure AWS credentials: aws configure")
        print("2. Run your first scrape: python scrape_cli.py --service ec2 --region us-east-1")
        print("3. Start web dashboard: python scraper_api.py")
        print("4. View dashboard: http://localhost:8000")
        
        if args.start_server:
            print("\n🌐 Starting web server...")
            try:
                import uvicorn
                from scraper_api import app
                uvicorn.run(app, host="0.0.0.0", port=8000)
            except Exception as e:
                logger.error(f"❌ Failed to start server: {e}")
                print("Start manually with: python scraper_api.py")
        
        return 0
    else:
        print("❌ Setup incomplete - please resolve the issues above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
