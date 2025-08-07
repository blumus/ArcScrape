# AWS Architecture Scraper

A comprehensive cloud architecture parsing and scraping application that discovers and analyzes AWS infrastructure using `aws-list-all`.

## 🎯 Overview

Organizations spend millions on cloud infrastructure but struggle to find the best cloud architecture solutions for their use case. This application:

- **Scrapes cloud architectures** using `aws-list-all`
- **Parses scraped content** and extracts relevant resources and data
- **Tracks scraping operations** with success/failure monitoring
- **Provides REST API** for managing scrapes
- **Organizes data** with timestamps and proper directory structure

## 🏗️ Architecture

```
AWS Architecture Scraper
├── CLI Interface (scrape_cli.py)
├── Core Scraper (aws_scraper.py)
├── REST API (scraper_api.py)
└── Data Organization
    ├── /aws-inventory/scrapes/     # Scraped data
    ├── /aws-inventory/logs/        # stdout/stderr logs
    └── /aws-inventory/status/      # success/fail markers
```

## ✨ Features

### 🔍 Smart Scraping
- **Service filtering**: Specify individual AWS services or scrape all
- **Region filtering**: Target specific regions or scrape globally  
- **Profile support**: Use different AWS profiles
- **Automatic timestamping**: Each scrape gets unique timestamp-based ID

### 📁 Organized Storage
- **Timestamped directories**: `scrape_20250806_143022_abc12345`
- **Success/fail tracking**: Empty files indicate status
- **Comprehensive logging**: Separate stdout/stderr capture
- **Metadata tracking**: Full scrape details in JSON format

### 🌐 Web Dashboard
- **Real-time status**: View all scrapes and their status
- **Interactive interface**: Start new scrapes from browser
- **File browsing**: Download individual scraped files
- **Log viewing**: Access stdout/stderr logs via web

### 📊 REST API
- **Start scrapes**: POST to `/api/scrapes/start`
- **List scrapes**: GET `/api/scrapes`
- **View details**: GET `/api/scrapes/{scrape_id}`
- **Download files**: GET `/api/scrapes/{scrape_id}/download/{filename}`

## 🚀 Quick Start

### 1. Prerequisites

All required tools and dependencies are pre-installed and configured in the provided Dockerfile. You only need to ensure you have valid AWS credentials and network access to AWS endpoints. For containerized deployment, Docker is recommended.

### 2. Basic Usage

```bash
# Scrape specific services and regions (as requested)
python scrape_cli.py --service ec2 --service s3 --region eu-west-1 --region us-east-1

# Scrape all services in specific regions
python scrape_cli.py --region eu-west-1 --region us-east-1

# Scrape everything (all services, all regions)
python scrape_cli.py

# List all scrapes
python scrape_cli.py --list

# Get scrape details
python scrape_cli.py --details scrape_20250806_143022_abc12345
```

### 3. Web Dashboard

```bash
# Start the web server
python scraper_api.py

# Access dashboard at:
# http://localhost:8000
```

## 📂 Directory Structure

After running scrapes, your directory will look like:

```
aws-inventory/
├── scrapes/
│   ├── scrape_20250806_143022_abc12345/
│   │   ├── scrape_metadata.json
│   │   ├── ec2_DescribeInstances_eu-west-1_None.json
│   │   ├── s3_ListBuckets_None_None.json
│   │   └── ... (all scraped AWS data)
│   └── scrape_20250806_144530_def67890/
├── logs/
│   ├── scrape_20250806_143022_abc12345/
│   │   ├── stdout.log
│   │   └── stderr.log
│   └── scrape_20250806_144530_def67890/
└── status/
    ├── scrape_20250806_143022_abc12345/
    │   ├── success          # (empty file = success)
    │   └── metadata.json
    └── scrape_20250806_144530_def67890/
        ├── fail            # (empty file = failure)
        └── metadata.json
```

## 🔧 Command Examples

### CLI Usage

```bash
# Basic scraping (mimics your requested command)
python scrape_cli.py --service ec2 --service s3 --region eu-west-1 --region us-east-1

# Advanced usage
python scrape_cli.py --service lambda --service dynamodb --region us-west-2 --profile production

# Management commands
python scrape_cli.py --list                    # List all scrapes
python scrape_cli.py --list-successful         # List only successful
python scrape_cli.py --list-failed             # List only failed
python scrape_cli.py --cleanup 7               # Clean scrapes older than 7 days

# Output options
python scrape_cli.py --list --json             # JSON output
python scrape_cli.py --service ec2 --quiet     # Minimal output
```

### API Usage

```bash
# Start a scrape
curl -X POST "http://localhost:8000/api/scrapes/start" \
  -H "Content-Type: application/json" \
  -d '{
    "services": ["ec2", "s3"],
    "regions": ["eu-west-1", "us-east-1"]
  }'

# List all scrapes
curl "http://localhost:8000/api/scrapes"

# Get scrape details
curl "http://localhost:8000/api/scrapes/scrape_20250806_143022_abc12345"

# Download a specific file
curl "http://localhost:8000/api/scrapes/scrape_20250806_143022_abc12345/download/ec2_DescribeInstances_eu-west-1_None.json"

# Get scrape logs
curl "http://localhost:8000/api/scrapes/scrape_20250806_143022_abc12345/logs"
```

## 📊 Web Dashboard Features

### Main Dashboard
- **Statistics overview**: Total scrapes, success rate, files scraped
- **Recent scrapes**: Last 10 scrapes with status
- **Quick actions**: Start new scrape, refresh data
- **Auto-refresh**: Updates every 30 seconds

### Scrape Management
- **Interactive scrape creation**: Enter services and regions via prompts
- **Detailed scrape views**: Click any scrape for full details
- **File downloads**: Direct download links for scraped files
- **Log viewing**: stdout/stderr logs accessible via web

## 🔍 Data Format

### Scrape Metadata
Each scrape creates a `scrape_metadata.json` file:

```json
{
  "scrape_id": "scrape_20250806_143022_abc12345",
  "start_time": "2025-08-06T14:30:22.123Z",
  "end_time": "2025-08-06T14:32:45.456Z", 
  "duration_seconds": 143.33,
  "success": true,
  "return_code": 0,
  "command": ["aws-list-all", "query", "--directory", "...", "--service", "ec2"],
  "services": ["ec2", "s3"],
  "regions": ["eu-west-1", "us-east-1"],
  "profile": null,
  "scraped_files_count": 25,
  "scrape_directory": "/path/to/scrapes/scrape_20250806_143022_abc12345",
  "log_directory": "/path/to/logs/scrape_20250806_143022_abc12345",
  "status_directory": "/path/to/status/scrape_20250806_143022_abc12345"
}
```

### Status Tracking
- **Success indicator**: Empty `success` file in status directory
- **Failure indicator**: Empty `fail` file in status directory  
- **Logs**: Separate `stdout.log` and `stderr.log` files
- **Metadata**: Duplicate metadata in status directory for quick access

## 🛠️ Advanced Usage

### Custom Directory Structure
```bash
python scrape_cli.py --directory /custom/path --service ec2
```

### Profile Management
```bash
python scrape_cli.py --profile production --service ec2
python scrape_cli.py --profile staging --region us-west-2
```

### Automation Examples
```bash
# Daily production scrape
0 2 * * * /usr/bin/python /app/scrape_cli.py --profile production --quiet

# Weekly full inventory
0 0 * * 0 /usr/bin/python /app/scrape_cli.py --quiet

# Cleanup old scrapes monthly
0 0 1 * * /usr/bin/python /app/scrape_cli.py --cleanup 30 --quiet
```

### Integration with Other Tools
```python
from aws_scraper import AWSArchitectureScraper

# Programmatic usage
scraper = AWSArchitectureScraper("/custom/directory")

# Start scrape
result = scraper.scrape_aws_architecture(
    services=["ec2", "rds"],
    regions=["us-east-1"],
    profile="production"
)

# Check results
if result['success']:
    print(f"Scraped {result['scraped_files_count']} files")
else:
    print(f"Scrape failed: {result.get('error')}")

# List all scrapes
scrapes = scraper.list_scrapes()
successful = scraper.get_successful_scrapes()
failed = scraper.get_failed_scrapes()
```

## 📈 Monitoring & Analytics

### Success Rate Tracking
The system automatically tracks:
- Total scrapes attempted
- Success/failure rates
- Files scraped per operation
- Duration statistics
- Error patterns

### Log Analysis
Each scrape captures:
- **stdout**: Normal aws-list-all output
- **stderr**: Error messages and warnings
- **Return codes**: Process exit status
- **Command executed**: Full command with parameters

### Cleanup & Maintenance
```bash
# Clean old scrapes (keeps 30 days by default)
python scrape_cli.py --cleanup

# Custom cleanup period
python scrape_cli.py --cleanup 7    # Keep 7 days

# API endpoint for cleanup
curl -X POST "http://localhost:8000/api/scrapes/cleanup?days=14"
```

## 🔒 Security Considerations

### AWS Credentials
- Uses standard AWS credential chain
- Supports AWS profiles for multi-account access
- No credentials stored in application

### File Permissions
- Scraped data inherits directory permissions
- Log files readable by application user only
- Status files used for quick checks without parsing JSON

### API Security
- Currently no authentication (suitable for internal use)
- Consider adding authentication for production deployments
- CORS disabled by default

## 🐛 Troubleshooting

### Common Issues

1. **aws-list-all not found**
   ```bash
   pip install aws-list-all
   ```

2. **AWS credentials not configured**
   ```bash
   aws configure
   # or
   export AWS_ACCESS_KEY_ID=...
   export AWS_SECRET_ACCESS_KEY=...
   ```

3. **Permission errors**
   ```bash
   # Ensure directory is writable
   chmod 755 ./aws-inventory
   ```

4. **Scrape timeouts**
   - Default timeout is 1 hour
   - Large accounts may need longer
   - Check logs for specific service issues

### Debug Mode
```bash
# Verbose logging
python scrape_cli.py --service ec2 --region us-east-1 2>&1 | tee debug.log

# Check individual scrape logs
cat aws-inventory/logs/scrape_*/stderr.log
```

## 🚀 Deployment

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
pip install aws-list-all

# Start API server
python scraper_api.py

# Run scrapes
python scrape_cli.py --service ec2
```

### Production Deployment
```bash
# Use systemd service
sudo cp scraper.service /etc/systemd/system/
sudo systemctl enable scraper
sudo systemctl start scraper

# Or use Docker
docker build -t aws-scraper .
docker run -d -p 8000:8000 -v ./aws-inventory:/app/aws-inventory aws-scraper
```

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs in `aws-inventory/logs/`
3. Check AWS credentials and permissions
4. Verify aws-list-all installation
