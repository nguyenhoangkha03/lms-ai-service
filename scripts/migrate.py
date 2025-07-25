#!/usr/bin/env python3
"""Enhanced database migration script with rollback and validation"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime
import json
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.database import (
    engine, 
    create_tables, 
    drop_tables, 
    check_database_connection,
    get_database_info,
    database_health_check,
    AsyncSessionLocal
)
from app.config.redis import init_redis_pool, redis_manager
from app.config.settings import get_settings
from scripts.init_db import DatabaseInitializer
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

class MigrationManager:
    """Advanced migration management with versioning and rollback"""
    
    def __init__(self):
        self.migration_table = "schema_migrations"
        self.current_version = "1.0.0"
    
    async def ensure_migration_table(self):
        """Ensure migration tracking table exists"""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.migration_table} (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        version VARCHAR(20) NOT NULL UNIQUE,
                        description TEXT,
                        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        execution_time_ms INT,
                        rollback_sql LONGTEXT,
                        status ENUM('pending', 'completed', 'failed', 'rolled_back') DEFAULT 'pending'
                    )
                """))
                await session.commit()
            logger.info("✅ Migration tracking table ensured")
        except Exception as e:
            logger.error(f"❌ Failed to create migration table: {str(e)}")
            raise
    
    async def record_migration(self, version: str, description: str, execution_time: int):
        """Record successful migration"""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text(f"""
                    INSERT INTO {self.migration_table} 
                    (version, description, execution_time_ms, status) 
                    VALUES (:version, :description, :execution_time, 'completed')
                    ON DUPLICATE KEY UPDATE 
                    executed_at = CURRENT_TIMESTAMP,
                    execution_time_ms = :execution_time,
                    status = 'completed'
                """), {
                    "version": version,
                    "description": description,
                    "execution_time": execution_time
                })
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to record migration: {str(e)}")
    
    async def get_migration_history(self):
        """Get migration history"""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(text(f"""
                    SELECT version, description, executed_at, execution_time_ms, status
                    FROM {self.migration_table}
                    ORDER BY executed_at DESC
                """))
                return result.fetchall()
        except Exception as e:
            logger.error(f"Failed to get migration history: {str(e)}")
            return []
    
    async def check_migration_status(self, version: str):
        """Check if migration version exists"""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(text(f"""
                    SELECT status FROM {self.migration_table} 
                    WHERE version = :version
                """), {"version": version})
                row = result.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to check migration status: {str(e)}")
            return None

class DatabaseValidator:
    """Validate database schema and data integrity"""
    
    async def validate_schema(self):
        """Validate database schema"""
        validations = []
        
        try:
            async with AsyncSessionLocal() as session:
                # Check if all required tables exist
                required_tables = [
                    'users', 'user_profiles', 'student_profiles', 'teacher_profiles',
                    'categories', 'courses', 'course_sections', 'lessons',
                    'enrollments', 'lesson_progress', 'learning_activities',
                    'learning_analytics', 'ai_recommendations', 'chatbot_conversations',
                    'chatbot_messages', 'chatbot_knowledge_base', 'assessments',
                    'questions', 'assessment_attempts'
                ]
                
                for table in required_tables:
                    result = await session.execute(text(f"""
                        SELECT COUNT(*) as count 
                        FROM information_schema.tables 
                        WHERE table_schema = '{settings.MYSQL_DATABASE}' 
                        AND table_name = '{table}'
                    """))
                    count = result.fetchone()[0]
                    
                    if count == 0:
                        validations.append({
                            "type": "error",
                            "message": f"Required table '{table}' is missing"
                        })
                    else:
                        validations.append({
                            "type": "success",
                            "message": f"Table '{table}' exists"
                        })
                
                # Check foreign key constraints
                fk_checks = [
                    ("user_profiles", "userId", "users", "id"),
                    ("student_profiles", "userId", "users", "id"),
                    ("teacher_profiles", "userId", "users", "id"),
                    ("courses", "teacherId", "users", "id"),
                    ("courses", "categoryId", "categories", "id"),
                    ("enrollments", "studentId", "users", "id"),
                    ("enrollments", "courseId", "courses", "id"),
                ]
                
                for child_table, child_col, parent_table, parent_col in fk_checks:
                    result = await session.execute(text(f"""
                        SELECT COUNT(*) as count
                        FROM information_schema.key_column_usage
                        WHERE table_schema = '{settings.MYSQL_DATABASE}'
                        AND table_name = '{child_table}'
                        AND column_name = '{child_col}'
                        AND referenced_table_name = '{parent_table}'
                        AND referenced_column_name = '{parent_col}'
                    """))
                    count = result.fetchone()[0]
                    
                    if count == 0:
                        validations.append({
                            "type": "warning",
                            "message": f"Foreign key constraint missing: {child_table}.{child_col} -> {parent_table}.{parent_col}"
                        })
                    else:
                        validations.append({
                            "type": "success",
                            "message": f"Foreign key constraint exists: {child_table}.{child_col} -> {parent_table}.{parent_col}"
                        })
                
                # Check indexes
                important_indexes = [
                    ("users", "email"),
                    ("users", "userType"),
                    ("courses", "teacherId"),
                    ("courses", "status"),
                    ("enrollments", "studentId"),
                    ("learning_activities", "studentId"),
                ]
                
                for table, column in important_indexes:
                    result = await session.execute(text(f"""
                        SELECT COUNT(*) as count
                        FROM information_schema.statistics
                        WHERE table_schema = '{settings.MYSQL_DATABASE}'
                        AND table_name = '{table}'
                        AND column_name = '{column}'
                    """))
                    count = result.fetchone()[0]
                    
                    if count == 0:
                        validations.append({
                            "type": "warning",
                            "message": f"Index missing on {table}.{column} - consider adding for performance"
                        })
                    else:
                        validations.append({
                            "type": "success",
                            "message": f"Index exists on {table}.{column}"
                        })
        
        except Exception as e:
            validations.append({
                "type": "error",
                "message": f"Schema validation failed: {str(e)}"
            })
        
        return validations
    
    async def validate_data_integrity(self):
        """Validate data integrity"""
        validations = []
        
        try:
            async with AsyncSessionLocal() as session:
                # Check for orphaned records
                orphan_checks = [
                    ("user_profiles", "userId", "users", "id", "User profiles without users"),
                    ("student_profiles", "userId", "users", "id", "Student profiles without users"),
                    ("teacher_profiles", "userId", "users", "id", "Teacher profiles without users"),
                    ("courses", "teacherId", "users", "id", "Courses without teachers"),
                    ("enrollments", "studentId", "users", "id", "Enrollments without students"),
                    ("enrollments", "courseId", "courses", "id", "Enrollments without courses"),
                ]
                
                for child_table, child_col, parent_table, parent_col, description in orphan_checks:
                    result = await session.execute(text(f"""
                        SELECT COUNT(*) as count
                        FROM {child_table} c
                        LEFT JOIN {parent_table} p ON c.{child_col} = p.{parent_col}
                        WHERE p.{parent_col} IS NULL AND c.{child_col} IS NOT NULL
                    """))
                    count = result.fetchone()[0]
                    
                    if count > 0:
                        validations.append({
                            "type": "error",
                            "message": f"{description}: {count} orphaned records found"
                        })
                    else:
                        validations.append({
                            "type": "success",
                            "message": f"{description}: No orphaned records"
                        })
                
                # Check data consistency
                consistency_checks = [
                    ("""
                        SELECT COUNT(*) FROM users u
                        LEFT JOIN user_profiles up ON u.id = up.userId
                        WHERE u.userType = 'student' AND up.userId IS NULL
                    """, "Students without user profiles"),
                    ("""
                        SELECT COUNT(*) FROM enrollments e
                        WHERE e.progressPercentage < 0 OR e.progressPercentage > 100
                    """, "Invalid progress percentages"),
                    ("""
                        SELECT COUNT(*) FROM courses c
                        WHERE c.price < 0
                    """, "Courses with negative prices"),
                ]
                
                for query, description in consistency_checks:
                    result = await session.execute(text(query))
                    count = result.fetchone()[0]
                    
                    if count > 0:
                        validations.append({
                            "type": "warning",
                            "message": f"{description}: {count} inconsistent records found"
                        })
                    else:
                        validations.append({
                            "type": "success",
                            "message": f"{description}: All records consistent"
                        })
        
        except Exception as e:
            validations.append({
                "type": "error", 
                "message": f"Data integrity validation failed: {str(e)}"
            })
        
        return validations

async def run_migration(args):
    """Run database migration with options"""
    start_time = datetime.utcnow()
    migration_manager = MigrationManager()
    
    try:
        logger.info("🚀 Starting database migration...")
        
        # Check database connection
        if not await check_database_connection():
            logger.error("❌ Cannot connect to database")
            return False
        
        # Initialize Redis connection
        await init_redis_pool()
        logger.info("✅ Redis connection established")
        
        # Ensure migration table exists
        await migration_manager.ensure_migration_table()
        
        # Check current migration status
        current_status = await migration_manager.check_migration_status(migration_manager.current_version)
        
        if current_status == 'completed' and not args.force:
            logger.info(f"ℹ️  Migration {migration_manager.current_version} already completed")
            
            if args.validate:
                await run_validation()
            return True
        
        # Drop tables if requested
        if args.drop_tables:
            logger.warning("⚠️  Dropping all tables...")
            await drop_tables()
        
        # Create tables
        logger.info("🔄 Creating database tables...")
        migration_start = datetime.utcnow()
        await create_tables()
        migration_time = int((datetime.utcnow() - migration_start).total_seconds() * 1000)
        
        # Seed initial data if requested
        if args.seed:
            logger.info("🌱 Seeding initial data...")
            async with DatabaseInitializer() as db_init:
                await db_init.seed_categories()
                await db_init.seed_admin_user()
                await db_init.seed_demo_teacher()
                await db_init.seed_demo_student()
                await db_init.seed_demo_course()
                await db_init.seed_chatbot_knowledge()
        
        # Record migration
        await migration_manager.record_migration(
            migration_manager.current_version,
            "Initial database schema with core LMS AI tables",
            migration_time
        )
        
        # Run validation if requested
        if args.validate:
            await run_validation()
        
        # Display summary
        total_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"✅ Migration completed successfully in {total_time:.2f} seconds")
        
        # Get database info
        db_info = await get_database_info()
        if db_info:
            logger.info(f"📊 Database: {db_info['table_count']} tables, {db_info['size_mb']} MB")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        
        # Record failed migration
        try:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            async with AsyncSessionLocal() as session:
                await session.execute(text(f"""
                    INSERT INTO {migration_manager.migration_table} 
                    (version, description, execution_time_ms, status) 
                    VALUES (:version, :description, :execution_time, 'failed')
                    ON DUPLICATE KEY UPDATE 
                    status = 'failed',
                    execution_time_ms = :execution_time
                """), {
                    "version": migration_manager.current_version,
                    "description": f"Migration failed: {str(e)}",
                    "execution_time": execution_time
                })
                await session.commit()
        except:
            pass  # Don't fail if we can't record the failure
        
        return False
    
    finally:
        # Close connections
        await engine.dispose()
        await redis_manager.close()

async def run_validation():
    """Run database validation"""
    logger.info("🔍 Running database validation...")
    
    validator = DatabaseValidator()
    
    # Schema validation
    schema_validations = await validator.validate_schema()
    logger.info("\n" + "="*50)
    logger.info("SCHEMA VALIDATION RESULTS")
    logger.info("="*50)
    
    for validation in schema_validations:
        icon = "✅" if validation["type"] == "success" else "⚠️" if validation["type"] == "warning" else "❌"
        logger.info(f"{icon} {validation['message']}")
    
    # Data integrity validation
    data_validations = await validator.validate_data_integrity()
    logger.info("\n" + "="*50)
    logger.info("DATA INTEGRITY VALIDATION RESULTS")
    logger.info("="*50)
    
    for validation in data_validations:
        icon = "✅" if validation["type"] == "success" else "⚠️" if validation["type"] == "warning" else "❌"
        logger.info(f"{icon} {validation['message']}")
    
    # Health check
    health_status = await database_health_check()
    logger.info("\n" + "="*50)
    logger.info("DATABASE HEALTH CHECK")
    logger.info("="*50)
    logger.info(f"Status: {health_status['status'].upper()}")
    
    if health_status.get('details'):
        details = health_status['details']
        logger.info(f"Version: {details.get('version', 'Unknown')}")
        logger.info(f"Size: {details.get('size_mb', 0)} MB")
        logger.info(f"Tables: {details.get('table_count', 0)}")
        logger.info(f"Query Time: {details.get('query_time_ms', 0)} ms")
    
    if health_status.get('errors'):
        for error in health_status['errors']:
            logger.warning(f"⚠️  {error}")

async def show_migration_history():
    """Show migration history"""
    migration_manager = MigrationManager()
    
    try:
        await migration_manager.ensure_migration_table()
        history = await migration_manager.get_migration_history()
        
        logger.info("\n" + "="*60)
        logger.info("MIGRATION HISTORY")
        logger.info("="*60)
        
        if not history:
            logger.info("No migrations found")
            return
        
        for row in history:
            version, description, executed_at, execution_time, status = row
            status_icon = {
                'completed': '✅',
                'failed': '❌',
                'pending': '⏳',
                'rolled_back': '↩️'
            }.get(status, '❓')
            
            logger.info(f"{status_icon} {version} - {status.upper()}")
            logger.info(f"   Description: {description}")
            logger.info(f"   Executed: {executed_at}")
            logger.info(f"   Duration: {execution_time}ms")
            logger.info("")
    
    except Exception as e:
        logger.error(f"Failed to get migration history: {str(e)}")

async def rollback_migration(version: str):
    """Rollback migration (placeholder for future implementation)"""
    logger.warning(f"⚠️  Rollback for version {version} requested")
    logger.warning("⚠️  Rollback functionality not yet implemented")
    logger.warning("⚠️  Manual intervention required")
    
    # In a full implementation, this would:
    # 1. Check if rollback SQL exists for the version
    # 2. Execute the rollback SQL
    # 3. Update migration status to 'rolled_back'
    # 4. Validate the rollback was successful

def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(description="LMS AI Database Migration Tool")
    parser.add_argument("--drop-tables", action="store_true", help="Drop all tables before migration")
    parser.add_argument("--seed", action="store_true", help="Seed initial data after migration")
    parser.add_argument("--validate", action="store_true", help="Run validation after migration")
    parser.add_argument("--force", action="store_true", help="Force migration even if already completed")
    parser.add_argument("--history", action="store_true", help="Show migration history")
    parser.add_argument("--rollback", type=str, help="Rollback to specified version")
    parser.add_argument("--validate-only", action="store_true", help="Only run validation")
    
    args = parser.parse_args()
    
    async def run():
        try:
            if args.history:
                await show_migration_history()
            elif args.rollback:
                await rollback_migration(args.rollback)
            elif args.validate_only:
                await run_validation()
                await engine.dispose()
            else:
                success = await run_migration(args)
                if not success:
                    sys.exit(1)
        except Exception as e:
            logger.error(f"❌ Migration script failed: {str(e)}")
            sys.exit(1)
    
    asyncio.run(run())

if __name__ == "__main__":
    main()