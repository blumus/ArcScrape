#!/usr/bin/env python3
"""
Simple CLI wrapper for AWS Architecture Scraping

This script provides an easy command-line interface that mimics
the aws-list-all usage pattern you specified.
"""

import sys
import argparse
from aws_scraper import AWSArchitectureScraper
import json

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description='AWS Architecture Scraper - Cloud infrastructure discovery',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape specific services and regions
  %(prog)s --service ec2 --service s3 --region eu-west-1 --region us-east-1
  
  # Scrape all services in specific regions  
  %(prog)s --region eu-west-1 --region us-east-1
  
  # Scrape everything (all services, all regions)
  %(prog)s
  
  # List all scrapes
  %(prog)s --list
  
  # Get details for a specific scrape
  %(prog)s --details scrape_20250806_143022_abc12345
        """
    )
    
    # Scraping options
    parser.add_argument('--service', action='append', dest='services',
                       help='AWS service to scrape (can be used multiple times). If not specified, scrapes all services.')
    parser.add_argument('--region', action='append', dest='regions', 
                       help='AWS region to scrape (can be used multiple times). If not specified, scrapes all regions.')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--directory', default='./aws-inventory', 
                       help='Directory to store scrapes (default: ./aws-inventory)')
    
    # Management options
    parser.add_argument('--list', action='store_true', help='List all scrapes')
    parser.add_argument('--list-successful', action='store_true', help='List successful scrapes only')
    parser.add_argument('--list-failed', action='store_true', help='List failed scrapes only')
    parser.add_argument('--details', metavar='SCRAPE_ID', help='Show details for a specific scrape')
    parser.add_argument('--cleanup', type=int, metavar='DAYS', nargs='?', const=30,
                       help='Clean up scrapes older than N days (default: 30)')
    
    # Output options
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--quiet', action='store_true', help='Suppress non-error output')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = AWSArchitectureScraper(args.directory)
    
    try:
        # Handle management commands
        if args.list:
            scrapes = scraper.list_scrapes()
            if args.json:
                print(json.dumps(scrapes, indent=2))
            else:
                print_scrapes_table(scrapes)
            return 0
        
        elif args.list_successful:
            scrapes = scraper.get_successful_scrapes()
            if args.json:
                print(json.dumps(scrapes, indent=2))
            else:
                print_scrapes_table(scrapes, "Successful Scrapes")
            return 0
        
        elif args.list_failed:
            scrapes = scraper.get_failed_scrapes()
            if args.json:
                print(json.dumps(scrapes, indent=2))
            else:
                print_scrapes_table(scrapes, "Failed Scrapes")
            return 0
        
        elif args.details:
            details = scraper.get_scrape_details(args.details)
            if not details:
                print(f"❌ Scrape not found: {args.details}", file=sys.stderr)
                return 1
            
            if args.json:
                print(json.dumps(details, indent=2))
            else:
                print_scrape_details(details)
            return 0
        
        elif args.cleanup is not None:
            if not args.quiet:
                print(f"🧹 Cleaning up scrapes older than {args.cleanup} days...")
            
            cleaned_count = scraper.cleanup_old_scrapes(args.cleanup)
            
            if args.json:
                print(json.dumps({"cleaned_count": cleaned_count}))
            elif not args.quiet:
                print(f"✅ Cleaned up {cleaned_count} old scrapes")
            return 0
        
        # Default action: start a new scrape
        else:
            if not args.quiet:
                print("🚀 Starting AWS architecture scrape...")
                if args.services:
                    print(f"   Services: {', '.join(args.services)}")
                else:
                    print("   Services: ALL")
                
                if args.regions:
                    print(f"   Regions: {', '.join(args.regions)}")
                else:
                    print("   Regions: ALL")
                
                if args.profile:
                    print(f"   Profile: {args.profile}")
                print()
            
            result = scraper.scrape_aws_architecture(
                services=args.services,
                regions=args.regions,
                profile=args.profile
            )
            
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print_scrape_result(result, args.quiet)
            
            return 0 if result['success'] else 1
    
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def print_scrapes_table(scrapes, title="All Scrapes"):
    """Print scrapes in a nice table format"""
    if not scrapes:
        print(f"No scrapes found.")
        return
    
    print(f"\n{title}")
    print("=" * len(title))
    print(f"Total: {len(scrapes)}")
    print()
    
    # Header
    print(f"{'Status':<8} {'Scrape ID':<32} {'Start Time':<20} {'Duration':<10} {'Files':<8}")
    print("-" * 85)
    
    for scrape in scrapes[:20]:  # Show first 20
        status = "✅ OK" if scrape.get('success') else "❌ FAIL"
        scrape_id = scrape['scrape_id']
        
        try:
            from datetime import datetime
            start_time = datetime.fromisoformat(scrape['start_time'].replace('Z', '+00:00'))
            start_str = start_time.strftime('%Y-%m-%d %H:%M')
        except:
            start_str = scrape['start_time'][:16]
        
        duration = f"{scrape.get('duration_seconds', 0):.0f}s"
        files = str(scrape.get('scraped_files_count', 0))
        
        print(f"{status:<8} {scrape_id:<32} {start_str:<20} {duration:<10} {files:<8}")
    
    if len(scrapes) > 20:
        print(f"... and {len(scrapes) - 20} more")
    print()


def print_scrape_details(details):
    """Print detailed information about a scrape"""
    print(f"\n📋 Scrape Details: {details['scrape_id']}")
    print("=" * 50)
    
    status = "✅ SUCCESS" if details['success'] else "❌ FAILED"
    print(f"Status: {status}")
    print(f"Start Time: {details['start_time']}")
    print(f"End Time: {details.get('end_time', 'N/A')}")
    print(f"Duration: {details.get('duration_seconds', 0):.2f} seconds")
    
    services = details.get('services', 'all')
    if isinstance(services, list):
        services = ', '.join(services)
    print(f"Services: {services}")
    
    regions = details.get('regions', 'all')
    if isinstance(regions, list):
        regions = ', '.join(regions)
    print(f"Regions: {regions}")
    
    if details.get('profile'):
        print(f"Profile: {details['profile']}")
    
    print(f"Files Scraped: {details.get('scraped_files_count', 0)}")
    
    if 'scraped_files' in details and details['scraped_files']:
        print(f"\n📁 Scraped Files ({len(details['scraped_files'])}):")
        for file_info in details['scraped_files'][:10]:  # Show first 10
            size_kb = file_info['size_bytes'] / 1024
            print(f"   📄 {file_info['filename']} ({size_kb:.1f} KB)")
        
        if len(details['scraped_files']) > 10:
            print(f"   ... and {len(details['scraped_files']) - 10} more files")
    
    # Show command that was run
    if 'command' in details:
        cmd_str = ' '.join(details['command'])
        print(f"\n🔧 Command: {cmd_str}")
    
    # Show error if failed
    if not details['success'] and 'error' in details:
        print(f"\n❌ Error: {details['error']}")
    
    # Show logs if available
    if 'stderr' in details and details['stderr'].strip():
        print(f"\n📝 Error Log:")
        print(details['stderr'][:500])  # Show first 500 chars
        if len(details['stderr']) > 500:
            print("... (truncated)")
    
    print()


def print_scrape_result(result, quiet=False):
    """Print the result of a scrape operation"""
    if result['success']:
        status = "✅ SUCCESS"
        if not quiet:
            print(f"{status}")
            print(f"Scrape ID: {result['scrape_id']}")
            print(f"Duration: {result.get('duration_seconds', 0):.2f} seconds")
            print(f"Files scraped: {result.get('scraped_files_count', 0)}")
            
            if result.get('scrape_directory'):
                print(f"Output directory: {result['scrape_directory']}")
    else:
        status = "❌ FAILED"
        print(f"{status}")
        print(f"Scrape ID: {result['scrape_id']}")
        
        if 'error' in result:
            print(f"Error: {result['error']}")
        
        if result.get('return_code'):
            print(f"Return code: {result['return_code']}")


if __name__ == "__main__":
    sys.exit(main())
