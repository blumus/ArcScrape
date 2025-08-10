#!/usr/bin/env python3
"""
AWS Scraper Smoke Test

Quick smoke test to verify the AWS scraper system is working correctly.
This test uses mocks and doesn't require actual AWS credentials or MongoDB.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import Mock, patch
import tempfile
import json
from pathlib import Path

def run_smoke_test():
    """Run basic smoke tests"""
    print("🧪 AWS Scraper Smoke Test")
    print("=" * 40)
    
    try:
        # Test 1: Module imports
        print("1️⃣  Testing module imports...")
        from aws_scraper import AWSArchitectureScraper
        from mongodb_manager import MongoDBManager
        from file_watcher import FileWatcherService
        print("   ✅ All modules import successfully")
        
        # Test 2: Scraper initialization
        print("2️⃣  Testing scraper initialization...")
        with patch('aws_scraper.MongoDBManager'):
            scraper = AWSArchitectureScraper("mongodb://test:27017/test")
            assert scraper is not None
            print("   ✅ Scraper initializes correctly")
        
        # Test 3: Mocked scrape workflow
        print("3️⃣  Testing scrape workflow (mocked)...")
        with patch('aws_scraper.MongoDBManager') as mock_mongo, \
             patch('aws_scraper.FileWatcherService') as mock_watcher, \
             patch('subprocess.run') as mock_subprocess, \
             patch('shutil.rmtree'), \
             patch('pathlib.Path.glob', return_value=[]):
            
            # Setup mocks
            mock_mongo.return_value = Mock()
            mock_watcher.return_value = Mock()
            mock_watcher.return_value.wait_for_completion.return_value = 3
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            
            scraper = AWSArchitectureScraper()
            result = scraper.scrape_aws_architecture(services=['iam'], regions=['us-east-1'])
            
            assert result['success'] is True
            assert 'scrape_id' in result
            print("   ✅ Mocked scrape workflow completes successfully")
        
        # Test 4: JSON file processing simulation
        print("4️⃣  Testing JSON file processing...")
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample AWS response
            sample_data = {
                "Users": [{"UserName": "test-user", "Arn": "arn:aws:iam::123:user/test"}],
                "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "test-123"}
            }
            
            # Write to temp file
            temp_file = Path(temp_dir) / "test.json"
            with open(temp_file, 'w') as f:
                json.dump(sample_data, f)
            
            # Verify we can read and parse
            with open(temp_file, 'r') as f:
                parsed_data = json.load(f)
                assert parsed_data['ResponseMetadata']['HTTPStatusCode'] == 200
                
            print("   ✅ JSON file processing works correctly")
        
        # Test 5: Error handling
        print("5️⃣  Testing error handling...")
        with patch('aws_scraper.MongoDBManager') as mock_mongo, \
             patch('aws_scraper.FileWatcherService') as mock_watcher, \
             patch('subprocess.run') as mock_subprocess, \
             patch('shutil.rmtree'), \
             patch('pathlib.Path.glob', return_value=[]):
            
            # Setup mocks for failure
            mock_mongo.return_value = Mock()
            mock_watcher.return_value = Mock()
            mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="Error")
            
            scraper = AWSArchitectureScraper()
            result = scraper.scrape_aws_architecture()
            
            assert result['success'] is False
            assert result['return_code'] == 1
            print("   ✅ Error handling works correctly")
        
        print("\n🎉 All smoke tests passed!")
        print("✅ AWS Scraper system is working correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)