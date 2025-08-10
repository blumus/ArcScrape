# AWS Architecture Scraper - MongoDB Edition

A comprehensive cloud architecture parsing and scraping application that discovers and analyzes AWS infrastructure using `aws-list-all` with MongoDB storage and real-time processing.

## 🎯 Overview

Organizations spend millions on cloud infrastructure but struggle to find the best cloud architecture solutions for their use case. This application:

- **Scrapes cloud architectures** using `aws-list-all` with real-time file processing
- **Stores data in MongoDB** for flexible querying and analysis
- **Parses scraped content** and extracts relevant resources and data
- **Tracks scraping operations** with comprehensive metadata and success/failure monitoring
- **Provides REST API** for managing scrapes and querying resources
- **Offers CLI interface** for command-line operations
- **Enables cross-scrape analysis** to track infrastructure changes over time

## 🏗️ Architecture

The system uses a MongoDB-based architecture with real-time file processing:

```
aws-list-all → /tmp/scrape_id/ → File Watcher → MongoDB Collections
                     ↓              ↓              ↓
                Temp Files    Real-time      Structured Storage
                             Processing      & Indexing
```

### Key Components:
- **MongoDB Manager**: Handles all database operations and indexing
- **File Watcher Service**: Monitors temp directories and processes files in real-time
- **AWS Scraper Engine**: Orchestrates the entire scraping workflow
- **REST API**: FastAPI-based web interface
- **CLI Interface**: Command-line tools for direct operations

## 📋 Prerequisites

### System Requirements
- **Docker & Docker Compose** (already configured in this dev container)
- **aws-list-all** tool (pre-installed in the container)
- **AWS CLI** configured with appropriate permissions

### AWS Configuration
Your AWS credentials are already mounted from the host system into the dev container. Verify they're working:

```bash
# Check AWS configuration
aws sts get-caller-identity

# If not configured, set up AWS credentials on your host machine
# The container will automatically use: ~/.aws/credentials_read_only and ~/.aws/config
```

## 🚀 Quick Start
### 1. go to backend dir
```bash
cd backend
```

### 2. Test the System
```bash
# Run smoke tests
python3 tests/smoke_test.py 

# Test MongoDB connection and basic functionality
python3 aws_scraper.py

# Or test with CLI
python3 scrape_cli_mongo.py stats
```

### 3. Start the API Server
```bash
# Start the REST API
python3 scraper_api_mongo.py
# API available at: http://localhost:8000
# Docs available at: http://localhost:8000/docs
```

### 4. Open API Documentation
```bash
# Open API docs in your browser
"$BROWSER" "http://localhost:8000/docs"
```

## 🐳 Docker Compose Services

Your environment includes these services:

```yaml
services:
  dev_env:           # Your current dev container
    ports:
      - "8000:8000"  # FastAPI API server
    environment:
      - MONGO_URI=mongodb://mongodb:27017/cloudculate
    
  mongodb:           # MongoDB database
    ports: 
      - "27017:27017" # MongoDB connection
    volumes:
      - mongo_data:/data/db  # Persistent storage
```

### Managing Services

```bash
# View running services
docker-compose ps

# Start MongoDB if stopped
docker-compose up -d mongodb

# View MongoDB logs
docker-compose logs mongodb

# Stop all services (from host)
docker-compose down

# Reset MongoDB data (WARNING: destroys all data)
docker-compose down -v
docker volume rm $(docker volume ls -q | grep mongo_data)
```

## 💻 Command Line Usage

### Basic Scraping Commands

```bash
# Scrape all services in specific regions
python3 scrape_cli_mongo.py scrape --regions us-east-1,eu-west-1

# Scrape specific services
python3 scrape_cli_mongo.py scrape --services ec2,s3,rds --regions us-east-1

# Scrape with specific AWS profile (if you have multiple profiles)
python3 scrape_cli_mongo.py scrape --profile production --regions us-east-1
```

### Querying and Management

```bash
# List all scrapes
python3 scrape_cli_mongo.py list

# List only successful scrapes
python3 scrape_cli_mongo.py list --success-only

# Show detailed scrape information
python3 scrape_cli_mongo.py show scrape_20250809_173531_f4a5f77d

# Query resources from a scrape
python3 scrape_cli_mongo.py query --scrape-id scrape_20250809_173531_f4a5f77d --region us-east-1

# Filter by specific service and region
python3 scrape_cli_mongo.py query --scrape-id scrape_20250809_173531_f4a5f77d --service ec2 --region us-east-1

# Get system statistics
python3 scrape_cli_mongo.py stats

# Delete a scrape and all its resources
python3 scrape_cli_mongo.py delete scrape_20250809_173531_f4a5f77d --force
```

### Output Formats

```bash
# Get JSON output for programmatic use
python3 scrape_cli_mongo.py list --json
python3 scrape_cli_mongo.py stats --json
python3 scrape_cli_mongo.py query --scrape-id <id> --json
```

## 🌐 REST API Usage

### Starting a Scrape

```bash
# Start a comprehensive scrape
curl -X POST "http://localhost:8000/api/scrapes" \
  -H "Content-Type: application/json" \
  -d '{
    "services": ["ec2", "s3", "rds"],
    "regions": ["us-east-1", "eu-west-1"],
    "profile": "default"
  }'

# Response:
# {
#   "scrape_id": "scrape_20250809_173531_f4a5f77d",
#   "success": true,
#   "duration_seconds": 125.5,
#   "files_processed": 15,
#   "message": "Scrape completed successfully"
# }
```

### Querying Data

```bash
# List all scrapes
curl "http://localhost:8000/api/scrapes?limit=10"

# Get scrape details
curl "http://localhost:8000/api/scrapes/scrape_20250809_173531_f4a5f77d"

# Query resources with filtering
curl "http://localhost:8000/api/scrapes/scrape_20250809_173531_f4a5f77d/resources?service=ec2&region=us-east-1"

# Compare resources across scrapes
curl "http://localhost:8000/api/resources/compare?service=ec2&region=us-east-1&operation=DescribeInstances&limit=5"

# Get system statistics
curl "http://localhost:8000/api/stats"

# Get service-specific statistics
curl "http://localhost:8000/api/stats/services"
```

### Interactive API Documentation

The FastAPI server provides interactive documentation:

```bash
# Open API documentation in your browser
"$BROWSER" "http://localhost:8000/docs"

# Alternative documentation format
"$BROWSER" "http://localhost:8000/redoc"
```

## 📊 Data Structure

### MongoDB Collections

The system uses two main collections in the `cloudculate` database:

#### `scrapes` Collection
Stores metadata about each scraping operation:
```json
{
  "scrape_id": "scrape_20250809_173531_f4a5f77d",
  "start_time": "2025-08-09T17:35:31.277Z",
  "end_time": "2025-08-09T17:37:37.533Z",
  "success": true,
  "services": ["ec2", "s3"],
  "regions": ["us-east-1", "eu-west-1"],
  "files_processed_to_mongo": 15,
  "total_resources_saved": 15
}
```

#### `aws_resources` Collection
Stores individual AWS service responses:
```json
{
  "scrape_id": "scrape_20250809_173531_f4a5f77d",
  "service": "ec2",
  "region": "us-east-1",
  "operation": "DescribeInstances",
  "source_filename": "ec2_DescribeInstances_us-east-1_None.json",
  "response": {
    "Instances": [...],
    "ResponseMetadata": {...}
  }
}
```

## 🔍 Advanced Querying

### MongoDB Direct Access

Connect directly to the MongoDB container for advanced analysis:

```bash
# Connect to MongoDB from the dev container
mongosh mongodb://mongodb:27017/cloudculate

# Or using docker-compose
docker-compose exec mongodb mongosh cloudculate
```

### MongoDB Queries

```javascript
// Find all resources for a specific service
db.aws_resources.find({"service": "ec2"}).limit(5)

// Count resources by service
db.aws_resources.aggregate([
  {"$group": {"_id": "$service", "count": {"$sum": 1}}},
  {"$sort": {"count": -1}}
])

// Find latest scrapes
db.scrapes.find().sort({"start_time": -1}).limit(10)

// Compare resource counts across scrapes
db.aws_resources.aggregate([
  {"$group": {
    "_id": {"scrape_id": "$scrape_id", "service": "$service"},
    "count": {"$sum": 1}
  }},
  {"$sort": {"_id.scrape_id": -1}}
])
```

### Python Integration

```python
from aws_scraper import AWSArchitectureScraper

# Initialize scraper (uses docker-compose MongoDB connection)
scraper = AWSArchitectureScraper("mongodb://mongodb:27017/cloudculate")

# Start a scrape
result = scraper.scrape_aws_architecture(
    services=["ec2", "s3"],
    regions=["us-east-1"]
)

# Query resources
resources = scraper.query_resources(
    scrape_id=result["scrape_id"],
    service="ec2",
    region="us-east-1"
)

# Get statistics
stats = scraper.get_stats()
print(f"Total scrapes: {stats['total_scrapes']}")
```

## 🛠️ Configuration

### Environment Variables

The dev container is configured with these environment variables:

```bash
# MongoDB connection (pre-configured)
MONGO_URI=mongodb://mongodb:27017/cloudculate

# You can override with:
export MONGODB_CONNECTION_STRING="mongodb://mongodb:27017/cloudculate"
export MONGODB_DATABASE_NAME="cloudculate"

# AWS Configuration (already mounted from host)
# AWS_PROFILE is read from your host ~/.aws/config
```

### Custom MongoDB Connection

```python
# Use the docker-compose MongoDB service
scraper = AWSArchitectureScraper("mongodb://mongodb:27017/cloudculate")

# For external MongoDB
scraper = AWSArchitectureScraper("mongodb://external-host:27017/aws_scraper")
```

## 🔧 Troubleshooting

### Common Issues

**1. MongoDB Connection Failed**
```bash
# Check MongoDB container status
docker-compose ps mongodb

# Start MongoDB if stopped
docker-compose up -d mongodb

# Check MongoDB logs
docker-compose logs mongodb

# Test connection from dev container
mongosh mongodb://mongodb:27017/cloudculate --eval "db.runCommand('ping').ok"
```

**2. AWS Credentials Not Working**
```bash
# Check mounted AWS credentials
ls -la /root/.aws/
cat /root/.aws/credentials
cat /root/.aws/config

# Test AWS access
aws sts get-caller-identity

# If credentials missing, they need to be on your host at:
# ~/.aws/credentials_read_only
# ~/.aws/config
```

**3. aws-list-all Issues**
```bash
# Verify aws-list-all is installed (should be pre-installed)
aws-list-all --help

# Test with a simple command
aws-list-all query --service sts --region us-east-1
```

**4. API Server Issues**
```bash
# Check if port 8000 is available
netstat -tlnp | grep :8000

# Kill existing processes
pkill -f "scraper_api_mongo"

# Start with different port
python3 scraper_api_mongo.py --port 8001

# Or use uvicorn directly
uvicorn scraper_api_mongo:app --host 0.0.0.0 --port 8000
```

**5. File Permissions Issues**
```bash
# Check temp directory permissions
ls -la /tmp/

# Clear old temp directories
rm -rf /tmp/scrape_*

# Create temp directory if needed
mkdir -p /tmp && chmod 755 /tmp
```

### Logging and Debugging

```bash
# Enable debug logging
export PYTHONPATH="/app/backend:$PYTHONPATH"
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from aws_scraper import AWSArchitectureScraper
scraper = AWSArchitectureScraper('mongodb://mongodb:27017/cloudculate')
print(scraper.get_stats())
"

# Test API endpoints
python3 test_mongo_api.py

# Check MongoDB collections directly
docker-compose exec mongodb mongosh cloudculate --eval "
  print('Scrapes:', db.scrapes.countDocuments({}));
  print('Resources:', db.aws_resources.countDocuments({}));
"
```

### Performance Optimization

**For Large Environments:**
```bash
# Increase timeout for large scrapes
export FILE_WATCHER_TIMEOUT="300"  # 5 minutes

# Use specific services instead of "all"
python3 scrape_cli_mongo.py scrape --services ec2,s3,rds --regions us-east-1

# Monitor MongoDB performance
docker-compose exec mongodb mongosh cloudculate --eval "db.stats()"
```

## 📈 Monitoring and Analytics

### Built-in Statistics

```bash
# Get comprehensive statistics
python3 scrape_cli_mongo.py stats

# API endpoint for statistics
curl "http://localhost:8000/api/stats"

# Service-specific analytics
curl "http://localhost:8000/api/stats/services"

# Regional analytics
curl "http://localhost:8000/api/stats/regions"

# Timeline analysis
curl "http://localhost:8000/api/stats/timeline?days=30"
```

### MongoDB Monitoring

```bash
# Monitor MongoDB from another terminal
docker-compose exec mongodb mongotop

# Check MongoDB logs
docker-compose logs -f mongodb

# MongoDB performance stats
docker-compose exec mongodb mongosh cloudculate --eval "
  db.runCommand({serverStatus: 1}).metrics
"
```

### Custom Analytics

Use MongoDB aggregation for custom analysis:

```javascript
// Resource growth over time
db.aws_resources.aggregate([
  {"$group": {
    "_id": {
      "year": {"$year": "$scrape_timestamp"},
      "month": {"$month": "$scrape_timestamp"}
    },
    "total_resources": {"$sum": 1}
  }},
  {"$sort": {"_id": 1}}
])

// Most active regions
db.aws_resources.aggregate([
  {"$group": {"_id": "$region", "count": {"$sum": 1}}},
  {"$sort": {"count": -1}},
  {"$limit": 10}
])
```

## 🧪 Development and Testing

### Running Tests
```bash
# Run comprehensive API tests
python3 test_mongo_api.py

# Test individual components
cd /app/backend
python3 -m pytest tests/ -v

# Test with different configurations
MONGODB_CONNECTION_STRING="mongodb://mongodb:27017/test_db" python3 test_mongo_api.py
```

### Development Workflow
```bash
# Make code changes in VS Code
# The /app volume is mounted, so changes are immediately available

# Restart API server to pick up changes
pkill -f "scraper_api_mongo" && python3 scraper_api_mongo.py &

# Or use uvicorn with auto-reload
uvicorn scraper_api_mongo:app --host 0.0.0.0 --port 8000 --reload
```

### Database Management
```bash
# Reset database for testing
docker-compose exec mongodb mongosh cloudculate --eval "db.dropDatabase()"

# Create fresh indexes
python3 -c "
from aws_scraper import AWSArchitectureScraper
scraper = AWSArchitectureScraper('mongodb://mongodb:27017/cloudculate')
scraper.mongo_manager.create_indexes()
scraper.close()
"

# Backup database
docker-compose exec mongodb mongodump --db cloudculate --out /tmp/backup
docker-compose cp mongodb:/tmp/backup ./mongodb_backup
```

## 📝 Architecture Documentation

For detailed technical information about the system architecture, database schema, and internal components, see:
- [`design.md`](design.md) - Complete technical design document

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

For issues, questions, or contributions:
1. Check the troubleshooting section above
2. Review the technical design document ([`design.md`](design.md))
3. Test your setup with: `python3 test_mongo_api.py`
4. Check service status with: `docker-compose ps`
5. View logs with: `docker-compose logs mongodb` or `docker-compose logs dev_env`

---

**Happy Cloud Architecture Scraping from your Dev Container! 🚀☁️🐳**
