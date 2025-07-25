from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event, text
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.engine.events import PoolEvents
import logging
from typing import AsyncGenerator
import asyncio
from contextlib import asynccontextmanager

from app.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Database configuration based on environment
def get_database_config():
    """Get database configuration based on environment"""
    base_config = {
        "echo": settings.DEBUG,
        "pool_pre_ping": True,
        "pool_recycle": 3600,  # 1 hour
        "connect_args": {
            "charset": "utf8mb4",
            "connect_timeout": 30,
            "read_timeout": 30,
            "write_timeout": 30,
        }
    }
    
    if settings.ENVIRONMENT == "production":
        return {
            **base_config,
            "pool_size": 20,
            "max_overflow": 30,
            "pool_timeout": 30,
            "poolclass": QueuePool,
            "echo": False
        }
    elif settings.ENVIRONMENT == "testing":
        return {
            **base_config,
            "poolclass": NullPool,
            "echo": False
        }
    else:  # development
        return {
            **base_config,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "poolclass": QueuePool
        }

# Create async engine with optimized configuration
engine = create_async_engine(
    settings.DATABASE_URL,
    **get_database_config()
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# Base class for models
Base = declarative_base()

# Connection pool monitoring
class DatabaseMonitor:
    """Monitor database connection pool and performance"""
    
    def __init__(self):
        self.connection_count = 0
        self.active_connections = 0
        self.failed_connections = 0
    
    def log_connection_status(self):
        """Log current connection pool status"""
        if hasattr(engine.pool, 'size'):
            pool_size = engine.pool.size()
            checked_in = engine.pool.checkedin()
            checked_out = engine.pool.checkedout()
            
            logger.info(
                f"DB Pool Status - Size: {pool_size}, "
                f"Checked In: {checked_in}, Checked Out: {checked_out}, "
                f"Total Connections: {self.connection_count}, "
                f"Failed: {self.failed_connections}"
            )

db_monitor = DatabaseMonitor()

# Connection event handlers
@event.listens_for(engine.sync_engine, "connect")
def set_mysql_pragma(dbapi_connection, connection_record):
    """Set MySQL connection parameters"""
    try:
        with dbapi_connection.cursor() as cursor:
            # Set SQL mode for strict behavior
            cursor.execute("SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'")
            
            # Set timezone
            cursor.execute("SET time_zone = '+00:00'")
            
            # Optimize for InnoDB
            cursor.execute("SET innodb_strict_mode = 1")
            
            # Character set
            cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
        
        db_monitor.connection_count += 1
        logger.debug("Database connection established and configured")
        
    except Exception as e:
        db_monitor.failed_connections += 1
        logger.error(f"Failed to configure database connection: {str(e)}")
        raise

@event.listens_for(engine.sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Handle connection checkout from pool"""
    db_monitor.active_connections += 1
    logger.debug("Connection checked out from pool")

@event.listens_for(engine.sync_engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Handle connection checkin to pool"""
    db_monitor.active_connections -= 1
    logger.debug("Connection checked in to pool")

@event.listens_for(engine.sync_engine, "close")
def receive_close(dbapi_connection, connection_record):
    """Handle connection close"""
    logger.debug("Connection closed")

@event.listens_for(engine.sync_engine, "close_detached")
def receive_close_detached(dbapi_connection):
    """Handle detached connection close"""
    logger.debug("Detached connection closed")

# Database management functions
async def create_tables():
    """Create database tables"""
    try:
        logger.info("🔄 Creating database tables...")
        
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            import app.models.database  # noqa: F401
            
            # Create tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("✅ Database tables created successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {str(e)}")
        raise

async def drop_tables():
    """Drop all database tables (use with caution!)"""
    try:
        logger.warning("⚠️  Dropping all database tables...")
        
        async with engine.begin() as conn:
            import app.models.database  # noqa: F401
            await conn.run_sync(Base.metadata.drop_all)
            
        logger.info("✅ Database tables dropped successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to drop database tables: {str(e)}")
        raise

async def check_database_connection():
    """Check database connectivity"""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False

async def get_database_info():
    """Get database information and statistics"""
    try:
        async with AsyncSessionLocal() as session:
            # Get MySQL version
            version_result = await session.execute(text("SELECT VERSION()"))
            version = version_result.scalar()
            
            # Get database size
            size_result = await session.execute(text(
                f"SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) AS 'DB Size in MB' "
                f"FROM information_schema.tables WHERE table_schema='{settings.MYSQL_DATABASE}'"
            ))
            size = size_result.scalar()
            
            # Get table count
            table_result = await session.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='{settings.MYSQL_DATABASE}'"
            ))
            table_count = table_result.scalar()
            
            return {
                "version": version,
                "size_mb": size or 0,
                "table_count": table_count or 0,
                "pool_status": {
                    "size": engine.pool.size() if hasattr(engine.pool, 'size') else 0,
                    "checked_in": engine.pool.checkedin() if hasattr(engine.pool, 'checkedin') else 0,
                    "checked_out": engine.pool.checkedout() if hasattr(engine.pool, 'checkedout') else 0,
                }
            }
    except Exception as e:
        logger.error(f"Failed to get database info: {str(e)}")
        return None

# Session management
@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()

async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with get_db_session() as session:
        yield session

# Health check functions
async def database_health_check():
    """Comprehensive database health check"""
    health_status = {
        "status": "healthy",
        "details": {},
        "errors": []
    }
    
    try:
        # Test basic connectivity
        if not await check_database_connection():
            health_status["status"] = "unhealthy"
            health_status["errors"].append("Cannot connect to database")
            return health_status
        
        # Get database info
        db_info = await get_database_info()
        if db_info:
            health_status["details"] = db_info
        
        # Check connection pool
        try:
            pool_size = engine.pool.size() if hasattr(engine.pool, 'size') else 0
            checked_out = engine.pool.checkedout() if hasattr(engine.pool, 'checkedout') else 0
            
            # Warning if pool utilization is high
            if pool_size > 0 and (checked_out / pool_size) > 0.8:
                health_status["status"] = "warning"
                health_status["errors"].append("High connection pool utilization")
                
        except Exception as e:
            health_status["errors"].append(f"Pool check failed: {str(e)}")
        
        # Test query performance
        start_time = asyncio.get_event_loop().time()
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        query_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        health_status["details"]["query_time_ms"] = round(query_time, 2)
        
        if query_time > 1000:  # > 1 second
            health_status["status"] = "warning"
            health_status["errors"].append("Slow database response")
        
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["errors"].append(f"Health check failed: {str(e)}")
    
    return health_status

# Cleanup function
async def close_database():
    """Close database connections and cleanup"""
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")

# Transaction helper
@asynccontextmanager
async def database_transaction():
    """Context manager for database transactions"""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            try:
                yield session
            except Exception as e:
                logger.error(f"Transaction failed, rolling back: {str(e)}")
                raise

# Batch operation helper
async def batch_insert(model_class, data_list: list, batch_size: int = 1000):
    """Efficiently insert large amounts of data"""
    try:
        async with AsyncSessionLocal() as session:
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i:i + batch_size]
                session.add_all([model_class(**item) for item in batch])
                
                if i + batch_size < len(data_list):
                    await session.flush()  # Flush but don't commit
            
            await session.commit()
            logger.info(f"Successfully inserted {len(data_list)} records")
            
    except Exception as e:
        logger.error(f"Batch insert failed: {str(e)}")
        raise

# Database metrics for monitoring
async def get_database_metrics():
    """Get database performance metrics"""
    try:
        async with AsyncSessionLocal() as session:
            # Get connection stats
            connection_stats = await session.execute(text(
                "SHOW STATUS LIKE 'Connections'"
            ))
            
            # Get query stats
            query_stats = await session.execute(text(
                "SHOW STATUS LIKE 'Questions'"
            ))
            
            # Get slow query count
            slow_queries = await session.execute(text(
                "SHOW STATUS LIKE 'Slow_queries'"
            ))
            
            return {
                "connections": connection_stats.fetchone(),
                "queries": query_stats.fetchone(),
                "slow_queries": slow_queries.fetchone(),
                "pool_metrics": {
                    "active_connections": db_monitor.active_connections,
                    "total_connections": db_monitor.connection_count,
                    "failed_connections": db_monitor.failed_connections
                }
            }
    except Exception as e:
        logger.error(f"Failed to get database metrics: {str(e)}")
        return None