#!/usr/bin/env python3
"""
MongoDB Manager for AWS Architecture Scraper

Handles all MongoDB operations including connections, indexing,
and CRUD operations for scrapes and AWS resources.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

logger = logging.getLogger(__name__)

class MongoDBManager:
    """MongoDB manager for AWS scraper data"""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017/cloudculate"):
        """Initialize MongoDB connection"""
        self.connection_string = connection_string
        self.client = None
        self.database = None
        self.scrapes_collection = None
        self.resources_collection = None  # Add this line
        self._connect()
        self._create_indexes()
    
    def _connect(self):
        """Establish MongoDB connection"""
        try:
            self.client = MongoClient(self.connection_string)
            # Extract database name from connection string
            if "/" in self.connection_string:
                db_name = self.connection_string.split("/")[-1]
            else:
                db_name = "cloudculate"
            
            self.database = self.client[db_name]
            self.scrapes_collection = self.database['scrapes']
            self.resources_collection = self.database['resources']  # Add this line
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {db_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def _create_indexes(self):
        """Create necessary indexes for optimal performance"""
        try:
            # Scrapes collection indexes
            self.scrapes_collection.create_index("scrape_id", unique=True)
            self.scrapes_collection.create_index([("start_time", DESCENDING)])
            self.scrapes_collection.create_index("success")
            
            # Resources collection indexes - Add these
            self.resources_collection.create_index("scrape_id")
            self.resources_collection.create_index([("scrape_id", ASCENDING), ("service", ASCENDING)])
            self.resources_collection.create_index([("scrape_id", ASCENDING), ("region", ASCENDING)])
            self.resources_collection.create_index([("service", ASCENDING), ("region", ASCENDING)])
            self.resources_collection.create_index("scraped_at")
            
            logger.info("MongoDB indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise
    
    def save_scrape_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Save scrape metadata to MongoDB"""
        try:
            result = self.scrapes_collection.insert_one(metadata)
            return result.inserted_id is not None
        except Exception as e:
            logger.error(f"Failed to save scrape metadata: {e}")
            return False
    
    def update_scrape_metadata(self, scrape_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing scrape metadata"""
        try:
            result = self.scrapes_collection.update_one(
                {"scrape_id": scrape_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update scrape metadata: {e}")
            return False
    
    def save_resource(self, resource_doc: Dict[str, Any]) -> bool:
        """Save a resource document to the resources collection"""
        try:
            # Ensure required fields
            if not resource_doc.get('scrape_id'):
                raise ValueError("Resource document must have a scrape_id")
            
            # Add timestamp if not present
            if 'scraped_at' not in resource_doc:
                resource_doc['scraped_at'] = datetime.now(timezone.utc)
            
            # Insert the resource document
            result = self.resources_collection.insert_one(resource_doc)
            
            if result.inserted_id:
                logger.debug(f"Saved resource: {resource_doc.get('filename', 'unknown')}")
                return True
            else:
                logger.error("Failed to insert resource document")
                return False
                
        except Exception as e:
            logger.error(f"Error saving resource: {e}")
            return False
    
    def get_scrape_by_id(self, scrape_id: str) -> Optional[Dict[str, Any]]:
        """Get scrape metadata by scrape_id"""
        try:
            return self.scrapes_collection.find_one({"scrape_id": scrape_id})
        except Exception as e:
            logger.error(f"Failed to get scrape by ID: {e}")
            return None
    
    def query_scrapes(self, filters: Dict[str, Any] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Query scrapes with optional filters"""
        try:
            query = filters or {}
            cursor = self.scrapes_collection.find(query).sort("start_time", DESCENDING).skip(offset).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to query scrapes: {e}")
            return []
    
    def query_resources(self, filters: Dict[str, Any] = None, limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """Query resources with optional filters"""
        try:
            query = filters or {}
            cursor = self.resources_collection.find(query).sort("scraped_at", DESCENDING).skip(offset).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to query resources: {e}")
            return []
    
    def delete_scrape(self, scrape_id: str) -> bool:
        """Delete a scrape and all associated resources"""
        try:
            # Delete resources first
            self.resources_collection.delete_many({"scrape_id": scrape_id})
            
            # Delete scrape metadata
            result = self.scrapes_collection.delete_one({"scrape_id": scrape_id})
            
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete scrape: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            total_scrapes = self.scrapes_collection.count_documents({})
            total_resources = self.resources_collection.count_documents({})
            
            # Get unique services
            services_pipeline = [
                {"$group": {"_id": "$service"}},
                {"$match": {"_id": {"$ne": None}}}
            ]
            services_result = list(self.resources_collection.aggregate(services_pipeline))
            services_discovered = [doc['_id'] for doc in services_result]
            
            # Get recent scrapes count
            recent_successful = self.scrapes_collection.count_documents({
                "success": True,
                "start_time": {"$gte": datetime.now(timezone.utc).replace(day=1)}  # This month
            })
            
            return {
                "total_scrapes": total_scrapes,
                "total_resources": total_resources,
                "services_discovered": services_discovered,
                "recent_successful_scrapes": recent_successful
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")