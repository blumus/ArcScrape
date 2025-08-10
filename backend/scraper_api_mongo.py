#!/usr/bin/env python3
"""
AWS Architecture Scraper API - MongoDB Version

FastAPI server that provides REST API endpoints for managing
AWS architecture scraping operations with MongoDB storage.
"""
import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from bson import ObjectId
from aws_scraper import AWSArchitectureScraper
import uvicorn
import asyncio

# Custom JSON encoder for MongoDB ObjectId
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Custom jsonable_encoder that handles ObjectId
def custom_jsonable_encoder(obj: Any) -> Any:
    """Recursively convert MongoDB ObjectIds to strings"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: custom_jsonable_encoder(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [custom_jsonable_encoder(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scraper instance
scraper: Optional[AWSArchitectureScraper] = None

# Lifespan event handler (replaces startup/shutdown events)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources during app lifespan"""
    global scraper
    
    # Startup
    try:
        mongo_uri = "mongodb://mongodb:27017/cloudculate"  # Could be from env var
        scraper = AWSArchitectureScraper(mongo_uri)
        logger.info("AWS Scraper API started with MongoDB connection")
    except Exception as e:
        logger.error(f"Failed to initialize scraper: {e}")
        raise
    
    yield  # App runs here
    
    # Shutdown
    if scraper:
        scraper.close()
        logger.info("AWS Scraper API shutdown complete")

# Initialize FastAPI app with lifespan handler
app = FastAPI(
    title="AWS Architecture Scraper API",
    description="MongoDB-based AWS architecture scraping and analysis API",
    version="2.0.0",
    lifespan=lifespan
)

# Pydantic models for request/response schemas
class ScrapeRequest(BaseModel):
    """Request model for starting a new scrape"""
    services: Optional[List[str]] = Field(None, description="List of AWS services to scrape, or null for all")
    regions: Optional[List[str]] = Field(None, description="List of AWS regions to scrape, or null for all")
    profile: Optional[str] = Field(None, description="AWS profile to use")
    
    class Config:
        json_schema_extra = {
            "example": {
                "services": ["ec2", "s3", "rds"],
                "regions": ["us-east-1", "eu-west-1"],
                "profile": "default"
            }
        }

class ScrapeResponse(BaseModel):
    """Response model for scrape operations"""
    scrape_id: str
    success: bool
    duration_seconds: Optional[float]
    files_processed: Optional[int]
    return_code: Optional[int]
    message: Optional[str]

class ResourceQuery(BaseModel):
    """Query parameters for resource filtering"""
    service: Optional[str] = None
    region: Optional[str] = None
    operation: Optional[str] = None
    limit: int = Field(1000, ge=1, le=10000)
    offset: int = Field(0, ge=0)

# Helper function for background scraping - make it truly async
async def run_scrape_background(services: Optional[List[str]], regions: Optional[List[str]], profile: Optional[str]) -> Dict[str, Any]:
    """Run scrape in background using a thread pool to avoid blocking"""
    try:
        # Run the synchronous scrape method in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,  # Use default thread pool
            scraper.scrape_aws_architecture,
            services,
            regions,
            profile
        )
        logger.info(f"Background scrape completed: {result['scrape_id']}")
        return result
    except Exception as e:
        logger.error(f"Background scrape failed: {e}")
        raise

# Health check endpoint
@app.get("/")
async def root():
    """Landing page with API information"""
    try:
        stats = scraper.get_stats()
        total_scrapes = stats.get("total_scrapes", 0)
        total_resources = stats.get("total_resources", 0)
        services_count = len(stats.get("services_discovered", []))
    except:
        total_scrapes = 0
        total_resources = 0
        services_count = 0
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AWS Architecture Scraper API</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .container {{
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                max-width: 800px;
                margin: 20px;
                overflow: hidden;
            }}
            .header {{
                background: #2c3e50;
                color: white;
                padding: 2rem;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5em;
                font-weight: 300;
            }}
            .header p {{
                margin: 0.5rem 0 0 0;
                opacity: 0.9;
                font-size: 1.1em;
            }}
            .content {{
                padding: 2rem;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin: 2rem 0;
            }}
            .stat-card {{
                background: #f8f9fa;
                padding: 1.5rem;
                border-radius: 10px;
                text-align: center;
                border: 2px solid transparent;
                transition: all 0.3s ease;
            }}
            .stat-card:hover {{
                border-color: #667eea;
                transform: translateY(-5px);
            }}
            .stat-number {{
                font-size: 2.5em;
                font-weight: bold;
                color: #2c3e50;
                margin: 0;
            }}
            .stat-label {{
                color: #666;
                font-size: 0.9em;
                margin: 0.5rem 0 0 0;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .buttons {{
                display: flex;
                gap: 1rem;
                margin: 2rem 0;
                justify-content: center;
                flex-wrap: wrap;
            }}
            .btn {{
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                transition: all 0.3s ease;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }}
            .btn-primary {{
                background: #667eea;
                color: white;
            }}
            .btn-primary:hover {{
                background: #5a67d8;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            }}
            .btn-secondary {{
                background: #e2e8f0;
                color: #2c3e50;
            }}
            .btn-secondary:hover {{
                background: #cbd5e0;
                transform: translateY(-2px);
            }}
            .endpoints {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 1.5rem;
                margin: 2rem 0;
            }}
            .endpoint {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem 0;
                border-bottom: 1px solid #e2e8f0;
            }}
            .endpoint:last-child {{
                border-bottom: none;
            }}
            .endpoint-method {{
                background: #38a169;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8em;
                font-weight: bold;
                min-width: 60px;
                text-align: center;
            }}
            .endpoint-method.post {{ background: #3182ce; }}
            .endpoint-method.delete {{ background: #e53e3e; }}
            .endpoint-path {{
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 0.9em;
                color: #2c3e50;
                flex-grow: 1;
                margin: 0 1rem;
            }}
            .endpoint-desc {{
                color: #666;
                font-size: 0.85em;
                max-width: 200px;
                text-align: right;
            }}
            .status-indicator {{
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: #38a169;
                margin-right: 8px;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
                100% {{ opacity: 1; }}
            }}
            .footer {{
                text-align: center;
                padding: 1rem 2rem;
                background: #f8f9fa;
                color: #666;
                font-size: 0.9em;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏗️ AWS Architecture Scraper</h1>
                <p><span class="status-indicator"></span>MongoDB-based AWS Infrastructure Analysis API</p>
            </div>
            
            <div class="content">
                <div class="stats-grid">
                    <div class="stat-card">
                        <h2 class="stat-number">{total_scrapes}</h2>
                        <p class="stat-label">Total Scrapes</p>
                    </div>
                    <div class="stat-card">
                        <h2 class="stat-number">{total_resources}</h2>
                        <p class="stat-label">AWS Resources</p>
                    </div>
                    <div class="stat-card">
                        <h2 class="stat-number">{services_count}</h2>
                        <p class="stat-label">AWS Services</p>
                    </div>
                </div>

                <div class="buttons">
                    <a href="/docs" class="btn btn-primary">📚 Interactive API Docs</a>
                    <a href="/api/stats" class="btn btn-secondary">📊 View Statistics</a>
                    <a href="/health" class="btn btn-secondary">💚 Health Check</a>
                </div>

                <div class="endpoints">
                    <h3 style="margin-top: 0; color: #2c3e50;">🔗 Key API Endpoints</h3>
                    <div class="endpoint">
                        <span class="endpoint-method">GET</span>
                        <code class="endpoint-path">/api/scrapes</code>
                        <span class="endpoint-desc">List all scrapes</span>
                    </div>
                    <div class="endpoint">
                        <span class="endpoint-method post">POST</span>
                        <code class="endpoint-path">/api/scrapes</code>
                        <span class="endpoint-desc">Start new scrape</span>
                    </div>
                    <div class="endpoint">
                        <span class="endpoint-method">GET</span>
                        <code class="endpoint-path">/api/stats/services</code>
                        <span class="endpoint-desc">Service statistics</span>
                    </div>
                    <div class="endpoint">
                        <span class="endpoint-method">GET</span>
                        <code class="endpoint-path">/api/stats/regions</code>
                        <span class="endpoint-desc">Regional statistics</span>
                    </div>
                    <div class="endpoint">
                        <span class="endpoint-method">GET</span>
                        <code class="endpoint-path">/api/scrapes/{{id}}/resources</code>
                        <span class="endpoint-desc">Query resources</span>
                    </div>
                </div>
            </div>

            <div class="footer">
                <p>Version 2.0.0 • MongoDB Backend • Real-time AWS Infrastructure Discovery</p>
            </div>
        </div>

        <script>
            // Add some interactivity
            document.addEventListener('DOMContentLoaded', function() {{
                // Animate numbers on page load
                const numbers = document.querySelectorAll('.stat-number');
                numbers.forEach(num => {{
                    const finalValue = parseInt(num.textContent);
                    let currentValue = 0;
                    const increment = finalValue / 50;
                    const timer = setInterval(() => {{
                        currentValue += increment;
                        if (currentValue >= finalValue) {{
                            currentValue = finalValue;
                            clearInterval(timer);
                        }}
                        num.textContent = Math.floor(currentValue);
                    }}, 30);
                }});

                // Add click tracking for buttons
                document.querySelectorAll('.btn').forEach(btn => {{
                    btn.addEventListener('click', function(e) {{
                        console.log('Navigating to:', this.href);
                    }});
                }});
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test MongoDB connection
        stats = scraper.get_stats()
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc),
            "mongodb_connected": True,
            "total_scrapes": stats.get("total_scrapes", 0)
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

# Scrape Management Endpoints

@app.post("/api/scrapes", response_model=ScrapeResponse)
async def scrape_async(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Start a new AWS architecture scrape (asynchronous - returns immediately)"""
    try:
        logger.info(f"Starting asynchronous scrape with services: {request.services}, regions: {request.regions}")
        
        # Generate scrape ID immediately
        scrape_id = f"scrape_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        # Start scrape in background - this should now be truly non-blocking
        background_tasks.add_task(
            run_scrape_background, 
            request.services, 
            request.regions, 
            request.profile
        )
        
        logger.info(f"Background task started for scrape {scrape_id}, returning immediately")
        
        return ScrapeResponse(
            scrape_id=scrape_id,
            success=True,
            duration_seconds=None,
            files_processed=None,
            return_code=None,
            message=f"Scrape {scrape_id} started successfully - check status with GET /api/scrapes/{scrape_id}"
        )
        
    except Exception as e:
        logger.error(f"Failed to start asynchronous scrape: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scrape: {str(e)}"
        )

@app.get("/api/scrapes")
async def list_scrapes(
    limit: int = Query(50, ge=1, le=1000, description="Number of scrapes to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    success: Optional[bool] = Query(None, description="Filter by success status")
):
    """List all scrapes with optional filtering"""
    try:
        scrapes = scraper.list_scrapes(limit=limit, offset=offset, success_only=success or False)
        
        # Convert ObjectIds to strings
        cleaned_scrapes = custom_jsonable_encoder(scrapes)
        
        return {
            "scrapes": cleaned_scrapes,
            "count": len(cleaned_scrapes),
            "limit": limit,
            "offset": offset,
            "filters": {
                "success_only": success
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to list scrapes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list scrapes: {str(e)}"
        )

@app.get("/api/scrapes/{scrape_id}")
async def get_scrape(scrape_id: str):
    """Get detailed information about a specific scrape"""
    try:
        scrape_details = scraper.get_scrape_details(scrape_id)
        
        if not scrape_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scrape not found: {scrape_id}"
            )
        
        # Convert ObjectIds to strings
        cleaned_details = custom_jsonable_encoder(scrape_details)
        return cleaned_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scrape {scrape_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scrape: {str(e)}"
        )

@app.delete("/api/scrapes/{scrape_id}")
async def delete_scrape(scrape_id: str):
    """Delete a scrape and all associated resources"""
    try:
        # Check if scrape exists first
        scrape_details = scraper.get_scrape_details(scrape_id)
        if not scrape_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scrape not found: {scrape_id}"
            )
        
        success = scraper.delete_scrape(scrape_id)
        
        if success:
            return {
                "message": f"Scrape {scrape_id} deleted successfully",
                "scrape_id": scrape_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete scrape {scrape_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete scrape {scrape_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete scrape: {str(e)}"
        )

# Resource Query Endpoints

@app.get("/api/scrapes/{scrape_id}/resources")
async def get_scrape_resources(
    scrape_id: str,
    service: Optional[str] = Query(None, description="Filter by AWS service"),
    region: Optional[str] = Query(None, description="Filter by AWS region"),
    operation: Optional[str] = Query(None, description="Filter by AWS operation"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of resources to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get resources for a specific scrape"""
    try:
        resources = scraper.query_resources(
            scrape_id=scrape_id,
            service=service,
            region=region,
            operation=operation
        )
        
        # Apply pagination
        total = len(resources)
        paginated_resources = resources[offset:offset + limit]
        
        # Use custom encoder to handle ObjectIds
        response_data = {
            "scrape_id": scrape_id,
            "resources": custom_jsonable_encoder(paginated_resources),
            "total": total,
            "returned": len(paginated_resources),
            "offset": offset,
            "limit": limit,
            "filters": {
                "service": service,
                "region": region,
                "operation": operation
            }
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Failed to get resources for scrape {scrape_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scrape resources: {str(e)}"
        )

@app.delete("/api/scrapes/{scrape_id}/resources")
async def delete_scrape_resources(
    scrape_id: str,
    service: Optional[str] = Query(None, description="Filter by AWS service"),
    region: Optional[str] = Query(None, description="Filter by AWS region"),
    operation: Optional[str] = Query(None, description="Filter by AWS operation")
):
    """Delete resources from a specific scrape with optional filtering"""
    try:
        # Verify scrape exists
        scrape_details = scraper.get_scrape_details(scrape_id)
        if not scrape_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scrape not found: {scrape_id}"
            )
        
        # Build filters
        filters = {"scrape_id": scrape_id}
        if service:
            filters["service"] = service
        if region:
            filters["region"] = region
        if operation:
            filters["operation"] = operation
        
        # Count resources before deletion
        resources_before = scraper.query_resources(
            scrape_id=scrape_id,
            service=service,
            region=region,
            operation=operation
        )
        count_before = len(resources_before)
        
        # Delete resources
        deleted_count = scraper.mongo_manager.delete_resources(filters)
        
        return {
            "scrape_id": scrape_id,
            "filters": {
                "service": service,
                "region": region,
                "operation": operation
            },
            "resources_found": count_before,
            "resources_deleted": deleted_count,
            "success": deleted_count == count_before
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete resources for scrape {scrape_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete resources: {str(e)}"
        )

@app.get("/api/resources/compare")
async def compare_resources(
    service: str = Query(..., description="AWS service to compare"),
    region: str = Query(..., description="AWS region to compare"),
    operation: str = Query(..., description="AWS operation to compare"),
    limit: int = Query(10, ge=1, le=100, description="Number of scrapes to compare")
):
    """Compare the same resource across different scrapes"""
    try:
        # Build query for this specific service/region/operation
        filters = {
            "service": service,
            "region": region,
            "operation": operation
        }
        
        # Get resources sorted by scrape timestamp (most recent first)
        all_matching_resources = scraper.mongo_manager.query_resources(filters, limit=limit)
        
        # Sort by scrape timestamp descending
        all_matching_resources.sort(
            key=lambda x: x.get('scrape_timestamp', datetime.min.replace(tzinfo=timezone.utc)), 
            reverse=True
        )
        
        return {
            "comparison_criteria": {
                "service": service,
                "region": region,
                "operation": operation
            },
            "total_matches": len(all_matching_resources),
            "limit": limit,
            "resources": all_matching_resources[:limit]
        }
        
    except Exception as e:
        logger.error(f"Failed to compare resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare resources: {str(e)}"
        )

# Analytics Endpoints

@app.get("/api/stats")
async def get_stats():
    """Get database and scraping statistics"""
    try:
        stats = scraper.get_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )

@app.get("/api/stats/services")
async def get_service_stats():
    """Get statistics by AWS service"""
    try:
        # Use the scraper's direct query method instead of accessing MongoDB directly
        # Get all resources and aggregate by service in Python
        all_resources = []
        scrapes = scraper.list_scrapes(limit=100)  # Get recent scrapes
        
        service_stats = {}
        
        for scrape in scrapes[:10]:  # Check last 10 scrapes
            try:
                resources = scraper.query_resources(scrape_id=scrape['scrape_id'])
                for resource in resources:
                    service = resource.get('service', 'unknown')
                    if service not in service_stats:
                        service_stats[service] = {
                            'service': service,
                            'resource_count': 0,
                            'regions': set(),
                            'operations': set()
                        }
                    
                    service_stats[service]['resource_count'] += 1
                    service_stats[service]['regions'].add(resource.get('region', 'unknown'))
                    service_stats[service]['operations'].add(resource.get('operation', 'unknown'))
            except:
                continue  # Skip failed scrapes
        
        # Convert sets to counts and lists
        result = []
        for service, stats in service_stats.items():
            result.append({
                'service': service,
                'resource_count': stats['resource_count'],
                'region_count': len(stats['regions']),
                'operation_count': len(stats['operations']),
                'regions': list(stats['regions']),
                'operations': list(stats['operations'])
            })
        
        result.sort(key=lambda x: x['resource_count'], reverse=True)
        
        return {
            "service_statistics": result,
            "total_services": len(result)
        }
        
    except Exception as e:
        logger.error(f"Failed to get service stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service statistics: {str(e)}"
        )

@app.get("/api/stats/regions")
async def get_region_stats():
    """Get statistics by AWS region"""
    try:
        # Similar approach for regions
        scrapes = scraper.list_scrapes(limit=100)
        
        region_stats = {}
        
        for scrape in scrapes[:10]:  # Check last 10 scrapes
            try:
                resources = scraper.query_resources(scrape_id=scrape['scrape_id'])
                for resource in resources:
                    region = resource.get('region', 'unknown')
                    if region not in region_stats:
                        region_stats[region] = {
                            'region': region,
                            'resource_count': 0,
                            'services': set(),
                            'operations': set()
                        }
                    
                    region_stats[region]['resource_count'] += 1
                    region_stats[region]['services'].add(resource.get('service', 'unknown'))
                    region_stats[region]['operations'].add(resource.get('operation', 'unknown'))
            except:
                continue
        
        # Convert sets to counts and lists
        result = []
        for region, stats in region_stats.items():
            result.append({
                'region': region,
                'resource_count': stats['resource_count'],
                'service_count': len(stats['services']),
                'operation_count': len(stats['operations']),
                'services': list(stats['services']),
                'operations': list(stats['operations'])
            })
        
        result.sort(key=lambda x: x['resource_count'], reverse=True)
        
        return {
            "region_statistics": result,
            "total_regions": len(result)
        }
        
    except Exception as e:
        logger.error(f"Failed to get region stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get region statistics: {str(e)}"
        )

@app.get("/api/stats/timeline")
async def get_timeline_stats(days: int = Query(30, ge=1, le=365, description="Number of days to analyze")):
    """Get scraping statistics over time"""
    try:
        from datetime import timedelta
        
        # Get scrapes and group by date
        scrapes = scraper.list_scrapes(limit=1000)
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Group scrapes by date
        daily_stats = {}
        
        for scrape in scrapes:
            try:
                # Parse start time - handle different formats
                start_time = scrape.get('start_time')
                if isinstance(start_time, str):
                    # Remove 'Z' and parse
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                elif isinstance(start_time, datetime):
                    # Already a datetime object
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=timezone.utc)
                else:
                    continue  # Skip if we can't parse the time
                
                # Check if within date range
                if start_time < start_date or start_time > end_date:
                    continue
                
                date_key = start_time.date().isoformat()
                
                if date_key not in daily_stats:
                    daily_stats[date_key] = {
                        'date': date_key,
                        'total_scrapes': 0,
                        'successful_scrapes': 0,
                        'total_resources': 0
                    }
                
                daily_stats[date_key]['total_scrapes'] += 1
                if scrape.get('success'):
                    daily_stats[date_key]['successful_scrapes'] += 1
                
                daily_stats[date_key]['total_resources'] += scrape.get('total_resources_saved', 0)
                
            except Exception as e:
                logger.warning(f"Failed to parse scrape timestamp: {e}")
                continue
        
        # Convert to sorted list
        timeline = sorted(daily_stats.values(), key=lambda x: x['date'])
        
        return {
            "timeline": timeline,
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_days": len(timeline),
            "scrapes_analyzed": len(scrapes)
        }
        
    except Exception as e:
        logger.error(f"Failed to get timeline stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get timeline statistics: {str(e)}"
        )

# Development/testing endpoint
@app.get("/api/debug/mongo-test")
async def test_mongo_connection():
    """Test MongoDB connection (development only)"""
    try:
        # Use the same methods that work in the CLI
        stats = scraper.get_stats()
        
        # Get some sample scrapes to test the connection
        scrapes = scraper.list_scrapes(limit=5)
        
        return {
            "mongodb_status": "connected",
            "stats": stats,
            "sample_scrapes_count": len(scrapes),
            "mongo_manager_type": type(scraper.mongo_manager).__name__,
            "available_methods": [method for method in dir(scraper) if not method.startswith('_') and callable(getattr(scraper, method))]
        }
        
    except Exception as e:
        logger.error(f"MongoDB test failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": str(e), 
                "mongodb_status": "disconnected"
            }
        )

# Fix the reload warning by using the module import string
if __name__ == "__main__":
    import uvicorn
    # Use import string instead of app object to enable reload
    uvicorn.run("scraper_api_mongo:app", host="0.0.0.0", port=8000, reload=True)
