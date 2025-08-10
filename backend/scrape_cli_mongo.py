#!/usr/bin/env python3
"""
MongoDB-based CLI wrapper for AWS Architecture Scraping

This script provides command-line interface for the new MongoDB-based
AWS Architecture Scraper system.
"""
import sys
import argparse
from aws_scraper import AWSArchitectureScraper
import json
from datetime import datetime

def main():
    """Main CLI function for MongoDB-based scraper"""
    parser = argparse.ArgumentParser(
        description='AWS Architecture Scraper - MongoDB Version',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start new scrape
  %(prog)s scrape --services ec2,s3 --regions us-east-1,eu-west-1
  
  # List all scrapes
  %(prog)s list
  
  # Show scrape details  
  %(prog)s show scrape_20250809_173531_f4a5f77d
  
  # Query resources
  %(prog)s query --scrape-id scrape_20250809_173531_f4a5f77d --region us-east-1
  
  # Delete scrape
  %(prog)s delete scrape_20250809_173531_f4a5f77d
  
  # Get statistics
  %(prog)s stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Start new scrape')
    scrape_parser.add_argument('--services', help='Comma-separated list of services (or "all")')
    scrape_parser.add_argument('--regions', help='Comma-separated list of regions')  
    scrape_parser.add_argument('--profile', help='AWS profile to use')
    scrape_parser.add_argument('--mongo-uri', default='mongodb://mongodb:27017/cloudculate', 
                              help='MongoDB connection string')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List scrapes')
    list_parser.add_argument('--limit', type=int, default=20, help='Number of scrapes to show')
    list_parser.add_argument('--success-only', action='store_true', help='Show only successful scrapes')
    list_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Show command  
    show_parser = subparsers.add_parser('show', help='Show scrape details')
    show_parser.add_argument('scrape_id', help='Scrape ID to show')
    show_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Query resources')
    query_parser.add_argument('--scrape-id', required=True, help='Scrape ID to query')
    query_parser.add_argument('--service', help='Filter by service')
    query_parser.add_argument('--region', help='Filter by region') 
    query_parser.add_argument('--operation', help='Filter by operation')
    query_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete scrape')
    delete_parser.add_argument('scrape_id', help='Scrape ID to delete')
    delete_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    stats_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize scraper
    mongo_uri = getattr(args, 'mongo_uri', 'mongodb://mongodb:27017/cloudculate')
    scraper = AWSArchitectureScraper(mongo_uri)
    
    try:
        if args.command == 'scrape':
            return handle_scrape(scraper, args)
        elif args.command == 'list':
            return handle_list(scraper, args)
        elif args.command == 'show':
            return handle_show(scraper, args)
        elif args.command == 'query':
            return handle_query(scraper, args)
        elif args.command == 'delete':
            return handle_delete(scraper, args)
        elif args.command == 'stats':
            return handle_stats(scraper, args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1
    
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    finally:
        scraper.close()

def handle_scrape(scraper, args):
    """Handle scrape command"""
    print("🚀 Starting AWS architecture scrape...")
    
    services = None
    if args.services:
        if args.services.lower() == 'all':
            services = None
        else:
            services = [s.strip() for s in args.services.split(',')]
    
    regions = None
    if args.regions:
        regions = [r.strip() for r in args.regions.split(',')]
    
    if services:
        print(f"   Services: {', '.join(services)}")
    else:
        print("   Services: ALL")
        
    if regions:
        print(f"   Regions: {', '.join(regions)}")
    else:
        print("   Regions: ALL")
        
    if args.profile:
        print(f"   Profile: {args.profile}")
    
    print()
    
    result = scraper.scrape_aws_architecture(
        services=services,
        regions=regions,
        profile=args.profile
    )
    
    if result['success']:
        print("✅ Scrape completed successfully!")
        print(f"   Scrape ID: {result['scrape_id']}")
        print(f"   Duration: {result.get('duration_seconds', 0):.2f} seconds")
        print(f"   Files processed: {result.get('files_processed', 0)}")
        return 0
    else:
        print("❌ Scrape failed!")
        print(f"   Scrape ID: {result['scrape_id']}")
        if result.get('return_code'):
            print(f"   Return code: {result['return_code']}")
        return 1

def handle_list(scraper, args):
    """Handle list command"""
    scrapes = scraper.list_scrapes(limit=args.limit, success_only=args.success_only)
    
    if args.json:
        print(json.dumps(scrapes, indent=2, default=str))
        return 0
    
    if not scrapes:
        print("No scrapes found.")
        return 0
    
    title = "Successful Scrapes" if args.success_only else "All Scrapes"
    print(f"\n{title}")
    print("=" * len(title))
    print(f"Total: {len(scrapes)}")
    print()
    
    # Table header
    print(f"{'Status':<8} {'Scrape ID':<32} {'Start Time':<20} {'Duration':<10} {'Files':<8}")
    print("-" * 85)
    
    for scrape in scrapes:
        status = "✅ OK" if scrape.get('success') else "❌ FAIL"
        scrape_id = scrape['scrape_id']
        
        # Format start time
        try:
            if isinstance(scrape['start_time'], str):
                start_time = datetime.fromisoformat(scrape['start_time'].replace('Z', '+00:00'))
            else:
                start_time = scrape['start_time']
            start_str = start_time.strftime('%Y-%m-%d %H:%M')
        except:
            start_str = str(scrape['start_time'])[:16]
        
        duration = f"{scrape.get('duration_seconds', 0):.0f}s"
        files = str(scrape.get('files_processed_to_mongo', 0))
        
        print(f"{status:<8} {scrape_id:<32} {start_str:<20} {duration:<10} {files:<8}")
    
    print()
    return 0

def handle_show(scraper, args):
    """Handle show command"""
    details = scraper.get_scrape_details(args.scrape_id)
    
    if not details:
        print(f"❌ Scrape not found: {args.scrape_id}", file=sys.stderr)
        return 1
    
    if args.json:
        print(json.dumps(details, indent=2, default=str))
        return 0
    
    print(f"\n📋 Scrape Details: {details['scrape_id']}")
    print("=" * 50)
    
    status = "✅ SUCCESS" if details.get('success') else "❌ FAILED"
    print(f"Status: {status}")
    print(f"Start Time: {details.get('start_time')}")
    print(f"End Time: {details.get('end_time', 'N/A')}")
    print(f"Duration: {details.get('duration_seconds', 0):.2f} seconds")
    
    services = details.get('services', 'all')
    if isinstance(services, list):
        services = ', '.join(services)
    print(f"Services: {services}")
    
    regions = details.get('regions', [])
    if isinstance(regions, list):
        regions = ', '.join(regions) if regions else 'all'
    print(f"Regions: {regions}")
    
    if details.get('profile'):
        print(f"Profile: {details['profile']}")
    
    print(f"Files Processed: {details.get('files_processed_to_mongo', 0)}")
    print(f"Resources Saved: {details.get('total_resources_saved', 0)}")
    print(f"Temp Files Cleaned: {details.get('temp_files_cleaned', False)}")
    
    if details.get('command'):
        print(f"\n🔧 Command: {' '.join(details['command'])}")
    
    print()
    return 0

def handle_query(scraper, args):
    """Handle query command"""
    resources = scraper.query_resources(
        scrape_id=args.scrape_id,
        service=args.service,
        region=args.region,
        operation=args.operation
    )
    
    if args.json:
        print(json.dumps(resources, indent=2, default=str))
        return 0
    
    print(f"\n📊 Resources Query Results")
    print("=" * 30)
    print(f"Scrape ID: {args.scrape_id}")
    if args.service:
        print(f"Service: {args.service}")
    if args.region:
        print(f"Region: {args.region}")
    if args.operation:
        print(f"Operation: {args.operation}")
    print(f"Total Results: {len(resources)}")
    print()
    
    if not resources:
        print("No resources found matching criteria.")
        return 0
    
    # Show summary
    print(f"{'Service':<15} {'Region':<15} {'Operation':<30} {'Filename':<50}")
    print("-" * 110)
    
    for resource in resources[:20]:  # Show first 20
        service = resource.get('service', 'N/A')
        region = resource.get('region', 'N/A')
        operation = resource.get('operation', 'N/A')
        filename = resource.get('source_filename', 'N/A')
        
        print(f"{service:<15} {region:<15} {operation:<30} {filename:<50}")
    
    if len(resources) > 20:
        print(f"... and {len(resources) - 20} more resources")
    
    print()
    return 0

def handle_delete(scraper, args):
    """Handle delete command"""
    if not args.force:
        response = input(f"Are you sure you want to delete scrape {args.scrape_id}? (y/N): ")
        if response.lower() != 'y':
            print("Delete cancelled.")
            return 0
    
    success = scraper.delete_scrape(args.scrape_id)
    
    if success:
        print(f"✅ Scrape {args.scrape_id} deleted successfully")
        return 0
    else:
        print(f"❌ Failed to delete scrape {args.scrape_id}", file=sys.stderr)
        return 1

def handle_stats(scraper, args):
    """Handle stats command"""
    stats = scraper.get_stats()
    
    if args.json:
        print(json.dumps(stats, indent=2, default=str))
        return 0
    
    print(f"\n📈 AWS Scraper Statistics")
    print("=" * 30)
    print(f"Total Scrapes: {stats.get('total_scrapes', 0)}")
    print(f"Successful Scrapes: {stats.get('successful_scrapes', 0)}")
    print(f"Total Resources: {stats.get('total_resources', 0)}")
    
    services = stats.get('services_discovered', [])
    if services:
        print(f"Services Discovered: {len(services)}")
        print(f"  {', '.join(services[:10])}")
        if len(services) > 10:
            print(f"  ... and {len(services) - 10} more")
    
    regions = stats.get('regions_scanned', [])
    if regions:
        print(f"Regions Scanned: {len(regions)}")
        print(f"  {', '.join(regions)}")
    
    if stats.get('last_scrape'):
        print(f"Last Scrape: {stats['last_scrape']}")
    
    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())