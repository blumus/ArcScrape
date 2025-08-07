#!/usr/bin/env python3
"""
AWS Architecture Scraper API

FastAPI server that provides REST API endpoints for managing
AWS architecture scraping operations.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
from datetime import datetime
import json
import os
from pathlib import Path

from aws_scraper import AWSArchitectureScraper

# Initialize FastAPI app
app = FastAPI(
    title="AWS Architecture Scraper API",
    description="API for managing AWS architecture scraping operations",
    version="1.0.0"
)

# Initialize scraper
scraper = AWSArchitectureScraper()

# Pydantic models for request/response
class ScrapeRequest(BaseModel):
    services: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    profile: Optional[str] = None

class ScrapeResponse(BaseModel):
    scrape_id: str
    start_time: str
    success: bool
    message: str

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard showing scrapes overview"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AWS Architecture Scraper</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; }
            .header h1 { margin: 0; font-size: 2.5em; }
            .header p { margin: 10px 0 0 0; opacity: 0.9; }
            .stats { display: flex; gap: 20px; margin: 30px 0; }
            .stat-card { flex: 1; background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #667eea; }
            .stat-number { font-size: 2em; font-weight: bold; color: #667eea; margin-bottom: 5px; }
            .stat-label { color: #666; font-size: 0.9em; }
            .actions { margin: 30px 0; }
            .btn { background: #667eea; color: white; padding: 12px 24px; border: none; border-radius: 6px; text-decoration: none; display: inline-block; margin-right: 10px; cursor: pointer; }
            .btn:hover { background: #5a6fd8; }
            .btn-success { background: #28a745; }
            .btn-danger { background: #dc3545; }
            .scrapes-list { margin-top: 30px; }
            .scrape-item { background: #f8f9fa; margin: 10px 0; padding: 20px; border-radius: 6px; border-left: 4px solid #ddd; }
            .scrape-success { border-left-color: #28a745; }
            .scrape-failed { border-left-color: #dc3545; }
            .scrape-header { display: flex; justify-content: between; align-items: center; margin-bottom: 10px; }
            .scrape-id { font-weight: bold; font-family: monospace; }
            .scrape-status { padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: bold; }
            .status-success { background: #d4edda; color: #155724; }
            .status-failed { background: #f8d7da; color: #721c24; }
            .scrape-details { font-size: 0.9em; color: #666; }
            .nav-links { margin: 20px 0; }
            .nav-links a { margin-right: 20px; color: #667eea; text-decoration: none; }
            .nav-links a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏗️ AWS Architecture Scraper</h1>
                <p>Cloud infrastructure discovery and analysis platform</p>
            </div>
            
            <div class="nav-links">
                <a href="/api/scrapes">Scrapes API</a>
                <a href="/api/scrapes/successful">Successful Scrapes</a>
                <a href="/api/scrapes/failed">Failed Scrapes</a>
                <a href="/docs">API Documentation</a>
            </div>
            
            <div class="stats" id="stats">
                <div class="stat-card">
                    <div class="stat-number" id="total-scrapes">-</div>
                    <div class="stat-label">Total Scrapes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="successful-scrapes">-</div>
                    <div class="stat-label">Successful</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="failed-scrapes">-</div>
                    <div class="stat-label">Failed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-files">-</div>
                    <div class="stat-label">Files Scraped</div>
                </div>
            </div>
            
            <div class="actions">
                <button class="btn" onclick="startScrape()">🚀 Start New Scrape</button>
                <button class="btn btn-success" onclick="refreshData()">🔄 Refresh</button>
                <a href="/api/scrapes" class="btn">📊 View All Scrapes</a>
            </div>
            
            <div class="scrapes-list">
                <h3>Recent Scrapes</h3>
                <div id="scrapes-container">Loading...</div>
            </div>
        </div>
        
        <script>
            function refreshData() {
                loadStats();
                loadRecentScrapes();
            }
            
            function loadStats() {
                fetch('/api/scrapes')
                    .then(response => response.json())
                    .then(data => {
                        const successful = data.filter(s => s.success).length;
                        const failed = data.filter(s => !s.success).length;
                        const totalFiles = data.reduce((sum, s) => sum + (s.scraped_files_count || 0), 0);
                        
                        document.getElementById('total-scrapes').textContent = data.length;
                        document.getElementById('successful-scrapes').textContent = successful;
                        document.getElementById('failed-scrapes').textContent = failed;
                        document.getElementById('total-files').textContent = totalFiles.toLocaleString();
                    })
                    .catch(error => console.error('Error loading stats:', error));
            }
            
            function loadRecentScrapes() {
                fetch('/api/scrapes')
                    .then(response => response.json())
                    .then(data => {
                        const container = document.getElementById('scrapes-container');
                        if (data.length === 0) {
                            container.innerHTML = '<p>No scrapes found. Start your first scrape!</p>';
                            return;
                        }
                        
                        const scrapesHtml = data.slice(0, 10).map(scrape => {
                            const statusClass = scrape.success ? 'scrape-success' : 'scrape-failed';
                            const statusBadge = scrape.success ? 
                                '<span class="scrape-status status-success">✅ Success</span>' :
                                '<span class="scrape-status status-failed">❌ Failed</span>';
                            
                            const startTime = new Date(scrape.start_time).toLocaleString();
                            const duration = scrape.duration_seconds ? 
                                `${Math.round(scrape.duration_seconds)}s` : 'N/A';
                            
                            return `
                                <div class="scrape-item ${statusClass}">
                                    <div class="scrape-header">
                                        <span class="scrape-id">${scrape.scrape_id}</span>
                                        ${statusBadge}
                                    </div>
                                    <div class="scrape-details">
                                        <strong>Started:</strong> ${startTime} | 
                                        <strong>Duration:</strong> ${duration} | 
                                        <strong>Files:</strong> ${scrape.scraped_files_count || 0} |
                                        <strong>Services:</strong> ${Array.isArray(scrape.services) ? scrape.services.join(', ') : scrape.services} |
                                        <strong>Regions:</strong> ${Array.isArray(scrape.regions) ? scrape.regions.join(', ') : scrape.regions}
                                        <br>
                                        <a href="/api/scrapes/${scrape.scrape_id}" style="color: #667eea;">View Details</a>
                                    </div>
                                </div>
                            `;
                        }).join('');
                        
                        container.innerHTML = scrapesHtml;
                    })
                    .catch(error => {
                        console.error('Error loading scrapes:', error);
                        document.getElementById('scrapes-container').innerHTML = 
                            '<p style="color: red;">Error loading scrapes. Please refresh the page.</p>';
                    });
            }
            
            function startScrape() {
                const services = prompt('Enter AWS services (comma-separated, or leave empty for all):');
                const regions = prompt('Enter AWS regions (comma-separated, or leave empty for all):');
                
                const requestBody = {};
                if (services && services.trim()) {
                    requestBody.services = services.split(',').map(s => s.trim());
                }
                if (regions && regions.trim()) {
                    requestBody.regions = regions.split(',').map(r => r.trim());
                }
                
                fetch('/api/scrapes/start', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestBody)
                })
                .then(response => response.json())
                .then(data => {
                    alert(`Scrape started: ${data.scrape_id}`);
                    refreshData();
                })
                .catch(error => {
                    console.error('Error starting scrape:', error);
                    alert('Error starting scrape. Please try again.');
                });
            }
            
            // Load data on page load
            document.addEventListener('DOMContentLoaded', refreshData);
            
            // Auto-refresh every 30 seconds
            setInterval(refreshData, 30000);
        </script>
    </body>
    </html>
    """
    return html_content

@app.post("/api/scrapes/start", response_model=ScrapeResponse)
async def start_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Start a new AWS architecture scrape"""
    try:
        # Start scrape in background
        result = scraper.scrape_aws_architecture(
            services=request.services,
            regions=request.regions,
            profile=request.profile
        )
        
        return ScrapeResponse(
            scrape_id=result["scrape_id"],
            start_time=result["start_time"],
            success=result["success"],
            message=f"Scrape {'completed' if result['success'] else 'failed'}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scrape: {str(e)}")

@app.get("/api/scrapes")
async def list_scrapes() -> List[Dict[str, Any]]:
    """List all scrapes"""
    return scraper.list_scrapes()

@app.get("/api/scrapes/successful")
async def list_successful_scrapes() -> List[Dict[str, Any]]:
    """List successful scrapes"""
    return scraper.get_successful_scrapes()

@app.get("/api/scrapes/failed")
async def list_failed_scrapes() -> List[Dict[str, Any]]:
    """List failed scrapes"""
    return scraper.get_failed_scrapes()

@app.get("/api/scrapes/{scrape_id}")
async def get_scrape_details(scrape_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific scrape"""
    details = scraper.get_scrape_details(scrape_id)
    if not details:
        raise HTTPException(status_code=404, detail=f"Scrape not found: {scrape_id}")
    return details

@app.get("/api/scrapes/{scrape_id}/files")
async def list_scrape_files(scrape_id: str) -> List[Dict[str, Any]]:
    """List files from a specific scrape"""
    details = scraper.get_scrape_details(scrape_id)
    if not details:
        raise HTTPException(status_code=404, detail=f"Scrape not found: {scrape_id}")
    
    return details.get("scraped_files", [])

@app.get("/api/scrapes/{scrape_id}/download/{filename}")
async def download_scrape_file(scrape_id: str, filename: str):
    """Download a specific file from a scrape"""
    scrape_dir = Path(scraper.base_directory) / "scrapes" / scrape_id
    file_path = None
    
    # Find the file (it might be in subdirectories)
    for json_file in scrape_dir.glob("**/*.json"):
        if json_file.name == filename:
            file_path = json_file
            break
    
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/json'
    )

@app.get("/api/scrapes/{scrape_id}/logs")
async def get_scrape_logs(scrape_id: str) -> Dict[str, str]:
    """Get logs for a specific scrape"""
    log_dir = Path(scraper.base_directory) / "logs" / scrape_id
    
    logs = {}
    
    stdout_file = log_dir / "stdout.log"
    if stdout_file.exists():
        with open(stdout_file, 'r') as f:
            logs["stdout"] = f.read()
    
    stderr_file = log_dir / "stderr.log"
    if stderr_file.exists():
        with open(stderr_file, 'r') as f:
            logs["stderr"] = f.read()
    
    if not logs:
        raise HTTPException(status_code=404, detail=f"Logs not found for scrape: {scrape_id}")
    
    return logs

@app.delete("/api/scrapes/{scrape_id}")
async def delete_scrape(scrape_id: str) -> Dict[str, str]:
    """Delete a specific scrape and all its data"""
    import shutil
    
    base_dir = Path(scraper.base_directory)
    
    # Check if scrape exists
    scrape_dir = base_dir / "scrapes" / scrape_id
    if not scrape_dir.exists():
        raise HTTPException(status_code=404, detail=f"Scrape not found: {scrape_id}")
    
    try:
        # Remove all directories for this scrape
        for subdir in ["scrapes", "logs", "status"]:
            target_dir = base_dir / subdir / scrape_id
            if target_dir.exists():
                shutil.rmtree(target_dir)
        
        return {"message": f"Scrape {scrape_id} deleted successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete scrape: {str(e)}")

@app.post("/api/scrapes/cleanup")
async def cleanup_old_scrapes(days: int = Query(30, description="Days to keep")):
    """Clean up old scrapes"""
    try:
        cleaned_count = scraper.cleanup_old_scrapes(days)
        return {
            "message": f"Cleaned up {cleaned_count} old scrapes",
            "cleaned_count": cleaned_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@app.get("/api/stats")
async def get_scrape_stats() -> Dict[str, Any]:
    """Get overall scraping statistics"""
    scrapes = scraper.list_scrapes()
    
    total_scrapes = len(scrapes)
    successful_scrapes = len([s for s in scrapes if s.get('success')])
    failed_scrapes = total_scrapes - successful_scrapes
    total_files = sum(s.get('scraped_files_count', 0) for s in scrapes)
    
    # Get recent activity (last 24 hours)
    from datetime import datetime, timedelta
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    
    recent_scrapes = []
    for scrape in scrapes:
        try:
            scrape_time = datetime.fromisoformat(scrape['start_time'].replace('Z', '+00:00'))
            if scrape_time.replace(tzinfo=None) > yesterday:
                recent_scrapes.append(scrape)
        except:
            pass
    
    return {
        "total_scrapes": total_scrapes,
        "successful_scrapes": successful_scrapes,
        "failed_scrapes": failed_scrapes,
        "total_files_scraped": total_files,
        "recent_scrapes_24h": len(recent_scrapes),
        "success_rate": round((successful_scrapes / total_scrapes * 100) if total_scrapes > 0 else 0, 1)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
