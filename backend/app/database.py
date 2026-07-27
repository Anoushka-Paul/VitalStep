"""
Database connection management for multiple Supabase databases
Production-ready connection pooling and error handling
"""
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from functools import lru_cache
import logging
from contextlib import contextmanager

from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages multiple Supabase database connections
    Supports primary and secondary databases for failover or multi-tenant setups
    """
    
    def __init__(self):
        self._primary_client: Optional[Client] = None
        self._secondary_client: Optional[Client] = None
        self._connection_pool: Dict[str, Client] = {}
    
    def initialize(self):
        """Initialize database connections"""
        try:
            # Primary database
            self._primary_client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_ANON_KEY,
                options={"proxy": None}  # Disable proxy to fix compatibility issue
            )
            logger.info("Primary Supabase database connected")
            
            # Secondary database (if configured)
            if settings.SUPABASE_URL_2 and settings.SUPABASE_ANON_KEY_2:
                self._secondary_client = create_client(
                    settings.SUPABASE_URL_2,
                    settings.SUPABASE_ANON_KEY_2,
                    options={"proxy": None}  # Disable proxy to fix compatibility issue
                )
                logger.info("Secondary Supabase database connected")
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            return False
    
    def get_primary_client(self) -> Client:
        """Get primary database client"""
        if not self._primary_client:
            raise RuntimeError("Primary database not initialized")
        return self._primary_client
    
    def get_secondary_client(self) -> Optional[Client]:
        """Get secondary database client (if available)"""
        if not self._secondary_client:
            raise RuntimeError("Secondary database not configured")
        return self._secondary_client
    
    def get_client(self, database: str = "primary") -> Client:
        """
        Get database client by name
        
        Args:
            database: Database name ("primary" or "secondary")
        
        Returns:
            Supabase client instance
        """
        if database == "secondary":
            return self.get_secondary_client()
        return self.get_primary_client()
    
    @contextmanager
    def get_connection(self, database: str = "primary"):
        """
        Context manager for database connections
        
        Usage:
            with db_manager.get_connection() as client:
                result = client.table("users").select("*").execute()
        """
        client = self.get_client(database)
        try:
            yield client
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of all database connections
        
        Returns:
            Dict with connection status
        """
        status = {
            "primary": {"connected": False, "error": None},
            "secondary": {"connected": False, "error": None}
        }
        
        # Check primary
        try:
            client = self.get_primary_client()
            # Simple query to test connection
            client.table("research_patients").select("count", count="exact").limit(1).execute()
            status["primary"]["connected"] = True
        except Exception as e:
            status["primary"]["error"] = str(e)
        
        # Check secondary
        if self._secondary_client:
            try:
                client = self.get_secondary_client()
                client.table("research_patients").select("count", count="exact").limit(1).execute()
                status["secondary"]["connected"] = True
            except Exception as e:
                status["secondary"]["error"] = str(e)
        
        return status
    
    def close(self):
        """Close all database connections"""
        self._primary_client = None
        self._secondary_client = None
        self._connection_pool.clear()
        logger.info("All database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> DatabaseManager:
    """Get database manager instance"""
    return db_manager


# ============================================================================
# Repository Pattern for Data Access
# ============================================================================

class BaseRepository:
    """Base repository for database operations"""
    
    def __init__(self, table_name: str, database: str = "primary"):
        self.table_name = table_name
        self.database = database
        self.db = db_manager
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all records with pagination"""
        with self.db.get_connection(self.database) as client:
            response = (
                client.table(self.table_name)
                .select("*")
                .range(offset, offset + limit - 1)
                .execute()
            )
            return response.data
    
    def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Get record by ID"""
        with self.db.get_connection(self.database) as client:
            response = (
                client.table(self.table_name)
                .select("*")
                .eq("id", id)
                .execute()
            )
            return response.data[0] if response.data else None
    
    def get_by_field(self, field: str, value: Any) -> List[Dict[str, Any]]:
        """Get records by field value"""
        with self.db.get_connection(self.database) as client:
            response = (
                client.table(self.table_name)
                .select("*")
                .eq(field, value)
                .execute()
            )
            return response.data
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new record"""
        with self.db.get_connection(self.database) as client:
            response = (
                client.table(self.table_name)
                .insert(data)
                .execute()
            )
            return response.data[0] if response.data else data
    
    def update(self, id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update record by ID"""
        with self.db.get_connection(self.database) as client:
            response = (
                client.table(self.table_name)
                .update(data)
                .eq("id", id)
                .execute()
            )
            return response.data[0] if response.data else data
    
    def delete(self, id: int) -> bool:
        """Delete record by ID"""
        with self.db.get_connection(self.database) as client:
            response = (
                client.table(self.table_name)
                .delete()
                .eq("id", id)
                .execute()
            )
            return len(response.data) > 0


class PatientRepository(BaseRepository):
    """Repository for patient operations"""
    
    def __init__(self, database: str = "primary"):
        super().__init__("research_patients", database)
    
    def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get patient by phone number"""
        with self.db.get_connection(self.database) as client:
            response = (
                client.table(self.table_name)
                .select("*")
                .eq("contact", phone)
                .execute()
            )
            return response.data[0] if response.data else None
    
    def search_by_name(self, name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search patients by name"""
        with self.db.get_connection(self.database) as client:
            response = (
                client.table(self.table_name)
                .select("*")
                .ilike("name", f"%{name}%")
                .limit(limit)
                .execute()
            )
            return response.data


class TrialReadingRepository(BaseRepository):
    """Repository for trial reading operations"""
    
    def __init__(self, database: str = "primary"):
        super().__init__("patient_readings", database)
    
    def get_latest_by_patient(self, patient_id: int) -> Optional[Dict[str, Any]]:
        """Get latest reading for a patient"""
        with self.db.get_connection(self.database) as client:
            response = (
                client.table(self.table_name)
                .select("*")
                .eq("patient_id", patient_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
    
    def get_by_patient(self, patient_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all readings for a patient"""
        with self.db.get_connection(self.database) as client:
            response = (
                client.table(self.table_name)
                .select("*")
                .eq("patient_id", patient_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data