# AWS Architecture Scraper - Complete MongoDB System Design

## System Overview

A comprehensive MongoDB-based AWS architecture scraping system that discovers, processes, and analyzes AWS infrastructure using `aws-list-all` with real-time data processing and temporary file management.

## Architecture

```
AWS Architecture Scraper (MongoDB-Based)
├── Core Scraper Engine
│   ├── MongoDB Integration Layer
│   ├── File Watcher Service  
│   ├── Temporary File Manager
│   └── Real-time Data Processor
├── API Layer
│   ├── Scrape Management Endpoints
│   ├── Resource Query Endpoints
│   └── Analytics Endpoints
├── CLI Interface
│   ├── Scrape Operations
│   ├── Query Commands
│   └── Management Tools
└── Data Storage
    ├── MongoDB Collections
    └── Temporary File Processing (/tmp)
```

## Data Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   aws-list-all  │───▶│  /tmp/scrape_id/ │───▶│  File Watcher   │
│                 │    │   (temporary)    │    │    Service      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   File Cleanup  │◀───│    MongoDB       │◀───│  Data Processor │
│   (delete /tmp) │    │   Collections    │    │  (JSON Parser)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## MongoDB Schema Design

### Database: `aws_scraper_db`

#### Collection 1: `scrapes` (Scrape Metadata)
```javascript
{
  _id: ObjectId("..."),
  scrape_id: "scrape_20250809_173531_f4a5f77d",
  
  // Timing
  start_time: ISODate("2025-08-09T17:35:31.277Z"),
  end_time: ISODate("2025-08-09T17:37:37.533Z"),
  duration_seconds: 126.256754,
  
  // Execution
  success: false,
  return_code: -9,
  command: [
    "aws-list-all", "query", 
    "--directory", "/tmp/scrape_20250809_173531_f4a5f77d",
    "--region", "eu-west-1", "--region", "us-east-1"
  ],
  
  // Parameters
  services: "all", // or ["ec2", "s3", ...]
  regions: ["eu-west-1", "us-east-1"],
  profile: null,
  
  // Results
  scraped_files_count: 4,
  total_resources_saved: 150,
  
  // Processing
  temp_directory: "/tmp/scrape_20250809_173531_f4a5f77d",
  files_processed_to_mongo: 4,
  temp_files_cleaned: true,
  
  // Metadata
  created_at: ISODate("2025-08-09T17:35:31.277Z"),
  updated_at: ISODate("2025-08-09T17:37:37.533Z")
}
```

#### Collection 2: `aws_resources` (AWS Service Data)
```javascript
{
  _id: ObjectId("..."),
  
  // Scrape Context
  scrape_id: "scrape_20250809_173531_f4a5f77d",
  scrape_timestamp: ISODate("2025-08-09T17:35:31.277Z"),
  
  // AWS Context
  service: "apprunner",
  region: "us-east-1", 
  profile: null,
  operation: "ListObservabilityConfigurations",
  
  // File Reference
  source_filename: "apprunner_ListObservabilityConfigurations_us-east-1_None.json",
  
  // Complete AWS Response (preserving structure)
  response: {
    "ObservabilityConfigurationSummaryList": [
      {
        "ObservabilityConfigurationArn": "arn:aws:apprunner:us-east-1:571600832589:observabilityconfiguration/DefaultConfiguration/1/00000000000000000000000000000001",
        "ObservabilityConfigurationName": "DefaultConfiguration",
        "ObservabilityConfigurationRevision": 1
      }
    ],
    "ResponseMetadata": {
      "RequestId": "4a9e7039-b913-4ff1-bf35-f5d00fae4499",
      "HTTPStatusCode": 200,
      "HTTPHeaders": {
        "date": "Sat, 09 Aug 2025 17:37:17 GMT",
        "content-type": "application/x-amz-json-1.0",
        "content-length": "298",
        "connection": "keep-alive",
        "x-amzn-requestid": "4a9e7039-b913-4ff1-bf35-f5d00fae4499"
      },
      "RetryAttempts": 0
    }
  },
  
  // Processing
  temp_file_path: "/tmp/scrape_20250809_173531_f4a5f77d/apprunner_ListObservabilityConfigurations_us-east-1_None.json",
  processed_at: ISODate("2025-08-09T17:36:22.123Z"),
  
  // Metadata
  created_at: ISODate("2025-08-09T17:36:22.123Z"),
  updated_at: ISODate("2025-08-09T17:36:22.123Z")
}
```

## Database Indexing Strategy

### `scrapes` Collection Indexes
```javascript
// Primary identifier - unique lookup
db.scrapes.createIndex({ "scrape_id": 1 }, { unique: true })

// Query by time (most recent first)
db.scrapes.createIndex({ "start_time": -1 })

// Query by success/failure
db.scrapes.createIndex({ "success": 1 })

// Query by services and regions
db.scrapes.createIndex({ "services": 1, "regions": 1 })

// Compound index for filtered time queries
db.scrapes.createIndex({ "success": 1, "start_time": -1 })
```

### `aws_resources` Collection Indexes
```javascript
// Primary differentiator - unique document identification
db.aws_resources.createIndex({ 
  "scrape_id": 1, 
  "service": 1, 
  "region": 1, 
  "operation": 1 
}, { unique: true })

// Cross-scrape comparison queries
db.aws_resources.createIndex({ 
  "service": 1, 
  "region": 1, 
  "operation": 1, 
  "scrape_timestamp": -1 
})

// Scrape-based queries
db.aws_resources.createIndex({ "scrape_id": 1 })

// Service-based queries
db.aws_resources.createIndex({ "service": 1, "region": 1 })

// Time-based queries
db.aws_resources.createIndex({ "scrape_timestamp": -1 })

// Source filename lookup (for debugging)
db.aws_resources.createIndex({ "source_filename": 1 })
```

## Core Components

### 1. MongoDB Manager
```python
class MongoDBManager:
    """Handles all MongoDB operations"""
    
    def __init__(self, connection_string: str, database_name: str):
        self.client = MongoClient(connection_string)
        self.db = self.client[database_name]
        self.scrapes = self.db.scrapes
        self.aws_resources = self.db.aws_resources
    
    def create_indexes(self):
        """Create all required indexes"""
        
    def save_scrape_metadata(self, scrape_data: dict) -> str:
        """Save scrape metadata to scrapes collection"""
        
    def save_aws_resource(self, resource_data: dict) -> str:
        """Save AWS resource to aws_resources collection"""
        
    def query_resources(self, filters: dict) -> List[dict]:
        """Query resources with flexible filtering"""
        
    def delete_resources(self, filters: dict) -> int:
        """Delete resources matching criteria"""
```

### 2. File Watcher Service
```python
class FileWatcherService:
    """Monitors temporary directories and processes files in real-time"""
    
    def __init__(self, mongo_manager: MongoDBManager):
        self.mongo_manager = mongo_manager
        self.observer = Observer()
    
    def start_watching(self, temp_directory: str, scrape_id: str):
        """Start monitoring directory for new files"""
        
    def process_new_file(self, file_path: str, scrape_id: str):
        """Process new JSON file and save to MongoDB"""
        
    def stop_watching(self):
        """Stop file monitoring"""
```

### 3. AWS Architecture Scraper
```python
class AWSArchitectureScraper:
    """Main scraper orchestrating the entire process"""
    
    def __init__(self, mongo_connection_string: str):
        self.mongo_manager = MongoDBManager(mongo_connection_string, "aws_scraper_db")
        self.file_watcher = FileWatcherService(self.mongo_manager)
    
    def scrape_aws_architecture(self, 
                               services: Optional[List[str]] = None,
                               regions: Optional[List[str]] = None,
                               profile: Optional[str] = None) -> Dict[str, Any]:
        """Execute complete scraping workflow"""
        
        # 1. Generate scrape ID and temp directory
        scrape_id = self.generate_scrape_id()
        temp_dir = f"/tmp/{scrape_id}"
        
        # 2. Start file watcher
        self.file_watcher.start_watching(temp_dir, scrape_id)
        
        # 3. Save initial scrape metadata
        scrape_metadata = self.create_scrape_metadata(scrape_id, services, regions, profile)
        self.mongo_manager.save_scrape_metadata(scrape_metadata)
        
        # 4. Execute aws-list-all
        result = self.execute_aws_list_all(temp_dir, services, regions, profile)
        
        # 5. Wait for file processing completion
        self.wait_for_processing_completion(temp_dir, scrape_id)
        
        # 6. Update final scrape metadata
        self.update_scrape_completion(scrape_id, result)
        
        # 7. Cleanup temporary files
        self.cleanup_temp_directory(temp_dir)
        
        # 8. Stop file watcher
        self.file_watcher.stop_watching()
        
        return result
```

## API Endpoints

### Scrape Management
```python
# Start new scrape
POST /api/scrapes
{
  "services": ["ec2", "s3"] | "all",
  "regions": ["us-east-1", "eu-west-1"], 
  "profile": "default"
}

# Get scrape status
GET /api/scrapes/{scrape_id}

# List all scrapes
GET /api/scrapes?limit=50&offset=0&success=true

# Delete scrape and all resources
DELETE /api/scrapes/{scrape_id}
```

### Resource Querying
```python
# Get resources with flexible filtering
GET /api/scrapes/{scrape_id}/resources?service={service}&region={region}&operation={operation}

# Get all resources from scrape
GET /api/scrapes/{scrape_id}/resources

# Delete resources with filtering
DELETE /api/scrapes/{scrape_id}/resources?service={service}&region={region}&operation={operation}

# Compare resources across scrapes
GET /api/resources/compare?service={service}&region={region}&operation={operation}&limit=10
```

### Analytics
```python
# Dashboard statistics
GET /api/stats
{
  "total_scrapes": 45,
  "successful_scrapes": 42,
  "total_resources": 15230,
  "services_discovered": ["ec2", "s3", "rds", ...],
  "regions_scanned": ["us-east-1", "eu-west-1", ...],
  "last_scrape": "2025-08-09T17:35:31.277Z"
}

# Service statistics
GET /api/stats/services

# Region statistics  
GET /api/stats/regions

# Time-based statistics
GET /api/stats/timeline?days=30
```

## CLI Interface

### Scrape Commands
```bash
# Start new scrape
python scrape_cli.py scrape --services all --regions us-east-1,eu-west-1

# Start scrape with specific services
python scrape_cli.py scrape --services ec2,s3,rds --regions us-east-1

# List scrapes
python scrape_cli.py list --limit 20 --success-only

# Show scrape details
python scrape_cli.py show scrape_20250809_173531_f4a5f77d
```

### Query Commands
```bash
# Query resources
python scrape_cli.py query --scrape-id scrape_20250809_173531_f4a5f77d --region us-east-1

# Query specific service
python scrape_cli.py query --scrape-id scrape_20250809_173531_f4a5f77d --service ec2 --region us-east-1

# Compare across scrapes
python scrape_cli.py compare --service ec2 --region us-east-1 --operation DescribeInstances --limit 5
```

### Management Commands
```bash
# Delete resources
python scrape_cli.py delete --scrape-id scrape_20250809_173531_f4a5f77d --region us-east-1

# Delete entire scrape
python scrape_cli.py delete --scrape-id scrape_20250809_173531_f4a5f77d

# System statistics
python scrape_cli.py stats

# Database maintenance
python scrape_cli.py maintenance --cleanup-old-scrapes --days 30
```

## Query Patterns

### Resource Retrieval Patterns
```javascript
// Get all resources from specific scrape
db.aws_resources.find({"scrape_id": "scrape_20250809_173531_f4a5f77d"})

// Filter by region and service
db.aws_resources.find({
  "scrape_id": "scrape_20250809_173531_f4a5f77d",
  "region": "us-east-1", 
  "service": "ec2"
})

// Compare same operation across scrapes
db.aws_resources.find({
  "service": "ec2",
  "region": "us-east-1",
  "operation": "DescribeInstances"
}).sort({"scrape_timestamp": -1}).limit(5)

// Get latest resources for each service in region
db.aws_resources.aggregate([
  {"$match": {"region": "us-east-1"}},
  {"$sort": {"scrape_timestamp": -1}},
  {"$group": {
    "_id": {"service": "$service", "operation": "$operation"},
    "latest": {"$first": "$$ROOT"}
  }}
])
```

### Analytics Queries
```javascript
// Count resources by service
db.aws_resources.aggregate([
  {"$group": {
    "_id": "$service",
    "count": {"$sum": 1}
  }},
  {"$sort": {"count": -1}}
])

// Scrape success rate
db.scrapes.aggregate([
  {"$group": {
    "_id": "$success",
    "count": {"$sum": 1}
  }}
])

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
```

## Configuration

### Environment Variables
```bash
# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb://localhost:27017
MONGODB_DATABASE_NAME=aws_scraper_db

# AWS Configuration
AWS_PROFILE=default
AWS_DEFAULT_REGION=us-east-1

# Application Configuration
TEMP_DIRECTORY_BASE=/tmp
FILE_WATCHER_TIMEOUT=30
MAX_CONCURRENT_SCRAPES=3
```

### MongoDB Configuration
```javascript
// TTL Index for automatic cleanup (optional)
db.scrapes.createIndex(
  { "created_at": 1 }, 
  { expireAfterSeconds: 2592000 } // 30 days
)

db.aws_resources.createIndex(
  { "created_at": 1 }, 
  { expireAfterSeconds: 2592000 } // 30 days
)
```

## Error Handling & Monitoring

### Error Scenarios
- MongoDB connection failures
- File watcher service failures  
- Temporary file processing errors
- `aws-list-all` execution failures
- Cleanup operation failures

### Monitoring Points
- Scrape success/failure rates
- File processing delays
- MongoDB query performance
- Temporary disk space usage
- File cleanup completion

### Logging Strategy
```python
# Application logging to MongoDB collection
{
  "timestamp": ISODate("..."),
  "level": "ERROR",
  "component": "FileWatcher",
  "scrape_id": "scrape_20250809_173531_f4a5f77d", 
  "message": "Failed to process file: /tmp/scrape_20250809_173531_f4a5f77d/ec2_DescribeInstances_us-east-1_None.json",
  "error": "JSON decode error: ...",
  "file_path": "/tmp/scrape_20250809_173531_f4a5f77d/ec2_DescribeInstances_us-east-1_None.json"
}
```

## Benefits

### Performance Benefits
- **Indexed Queries**: Fast resource lookups via MongoDB indexes
- **Concurrent Access**: Multiple users can query simultaneously
- **Scalable Storage**: Handle large AWS environments efficiently
- **Real-time Processing**: Files processed as they're created

### Operational Benefits
- **No Manual Cleanup**: Automatic temporary file management
- **Data Consistency**: Transactional guarantees from MongoDB
- **Flexible Retention**: TTL indexes for automatic data cleanup
- **Cross-Scrape Analysis**: Compare resources over time

### Development Benefits  
- **Rich Query Language**: MongoDB aggregation for complex analysis
- **Schema Flexibility**: Easy to add new fields without migration
- **API Ready**: JSON-native storage perfect for REST APIs
- **Backup/Recovery**: Database-level backup and restore

This design provides a complete, scalable, MongoDB-based AWS architecture scraping system with real-time processing, flexible querying, and comprehensive management capabilities.