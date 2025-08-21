#!/usr/bin/env python3
"""
Database optimization script for Smart Factory
Creates indexes, analyzes tables, and optimizes queries
"""

import os
import sys
import django
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Set Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings_production')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line
from django.conf import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_database_indexes():
    """Create database indexes for better performance"""
    try:
        with connection.cursor() as cursor:
            logger.info("Creating database indexes...")
            
            # Indexes for orders
            indexes = [
                # Orders table
                "CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders (status, created_at);",
                "CREATE INDEX IF NOT EXISTS idx_orders_client_status ON orders (client_id, status);",
                "CREATE INDEX IF NOT EXISTS idx_orders_workshop_status ON orders (workshop_id, status);",
                "CREATE INDEX IF NOT EXISTS idx_orders_priority_completion ON orders (priority, estimated_completion);",
                "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_orders_updated_at ON orders (updated_at);",
                
                # Order items
                "CREATE INDEX IF NOT EXISTS idx_orderitems_order ON orderitem (order_id);",
                "CREATE INDEX IF NOT EXISTS idx_orderitems_product ON orderitem (product_id);",
                
                # Order stages
                "CREATE INDEX IF NOT EXISTS idx_orderstages_order ON orderstage (order_id);",
                "CREATE INDEX IF NOT EXISTS idx_orderstages_workshop ON orderstage (workshop_id);",
                "CREATE INDEX IF NOT EXISTS idx_orderstages_employee ON orderstage (employee_id);",
                "CREATE INDEX IF NOT EXISTS idx_orderstages_deadline ON orderstage (deadline);",
                
                # Clients
                "CREATE INDEX IF NOT EXISTS idx_clients_status ON client (status);",
                "CREATE INDEX IF NOT EXISTS idx_clients_name ON client (name);",
                
                # Products
                "CREATE INDEX IF NOT EXISTS idx_products_is_glass ON product (is_glass);",
                "CREATE INDEX IF NOT EXISTS idx_products_glass_type ON product (glass_type);",
                
                # Employees
                "CREATE INDEX IF NOT EXISTS idx_employees_workshop ON employee (workshop_id);",
                "CREATE INDEX IF NOT EXISTS idx_employees_status ON employee (status);",
                
                # Employee tasks
                "CREATE INDEX IF NOT EXISTS idx_employeetasks_employee ON employeetask (employee_id);",
                "CREATE INDEX IF NOT EXISTS idx_employeetasks_completed ON employeetask (completed_at);",
                "CREATE INDEX IF NOT EXISTS idx_employeetasks_earnings ON employeetask (earnings);",
                
                # Defects
                "CREATE INDEX IF NOT EXISTS idx_defects_order ON defect (order_id);",
                "CREATE INDEX IF NOT EXISTS idx_defects_employee ON defect (employee_id);",
                "CREATE INDEX IF NOT EXISTS idx_defects_created ON defect (created_at);",
                
                # Finance
                "CREATE INDEX IF NOT EXISTS idx_expenses_date ON expense (date);",
                "CREATE INDEX IF NOT EXISTS idx_expenses_category ON expense (category_id);",
                "CREATE INDEX IF NOT EXISTS idx_incomes_date ON income (date);",
                "CREATE INDEX IF NOT EXISTS idx_debts_due_date ON debt (due_date);",
                
                # Inventory
                "CREATE INDEX IF NOT EXISTS idx_rawmaterials_code ON rawmaterial (code);",
                "CREATE INDEX IF NOT EXISTS idx_materialincoming_date ON materialincoming (date);",
                "CREATE INDEX IF NOT EXISTS idx_materialconsumption_date ON materialconsumption (date);",
                
                # Attendance
                "CREATE INDEX IF NOT EXISTS idx_attendancerecords_employee ON attendancerecord (employee_id);",
                "CREATE INDEX IF NOT EXISTS idx_attendancerecords_date ON attendancerecord (date);",
                "CREATE INDEX IF NOT EXISTS idx_attendancerecords_check_in ON attendancerecord (check_in);",
            ]
            
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    logger.info(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Error creating index: {e}")
            
            logger.info("Database indexes created successfully")
            
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        raise

def analyze_tables():
    """Analyze tables for better query planning"""
    try:
        with connection.cursor() as cursor:
            logger.info("Analyzing tables...")
            
            # Get all tables
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename NOT LIKE 'django_%'
                AND tablename NOT LIKE 'auth_%'
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                try:
                    cursor.execute(f"ANALYZE {table};")
                    logger.info(f"Analyzed table: {table}")
                except Exception as e:
                    logger.warning(f"Error analyzing table {table}: {e}")
            
            logger.info("Table analysis completed")
            
    except Exception as e:
        logger.error(f"Error analyzing tables: {e}")
        raise

def vacuum_tables():
    """Vacuum tables to reclaim storage and update statistics"""
    try:
        with connection.cursor() as cursor:
            logger.info("Vacuuming tables...")
            
            # Get all tables
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename NOT LIKE 'django_%'
                AND tablename NOT LIKE 'auth_%'
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                try:
                    cursor.execute(f"VACUUM ANALYZE {table};")
                    logger.info(f"Vacuumed table: {table}")
                except Exception as e:
                    logger.warning(f"Error vacuuming table {table}: {e}")
            
            logger.info("Table vacuuming completed")
            
    except Exception as e:
        logger.error(f"Error vacuuming tables: {e}")
        raise

def optimize_database_settings():
    """Optimize database settings for better performance"""
    try:
        with connection.cursor() as cursor:
            logger.info("Optimizing database settings...")
            
            # Enable pg_stat_statements extension if available
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
                logger.info("pg_stat_statements extension enabled")
            except Exception as e:
                logger.warning(f"Could not enable pg_stat_statements: {e}")
            
            # Set work_mem for current session
            cursor.execute("SET work_mem = '16MB';")
            
            # Set maintenance_work_mem for current session
            cursor.execute("SET maintenance_work_mem = '128MB';")
            
            # Set random_page_cost for SSD
            cursor.execute("SET random_page_cost = 1.1;")
            
            # Set effective_io_concurrency for SSD
            cursor.execute("SET effective_io_concurrency = 200;")
            
            logger.info("Database settings optimized")
            
    except Exception as e:
        logger.error(f"Error optimizing database settings: {e}")
        raise

def get_database_stats():
    """Get database statistics and performance metrics"""
    try:
        with connection.cursor() as cursor:
            logger.info("Collecting database statistics...")
            
            # Table sizes
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10;
            """)
            
            table_sizes = cursor.fetchall()
            logger.info("Top 10 largest tables:")
            for table in table_sizes:
                logger.info(f"  {table[1]}: {table[2]}")
            
            # Index usage statistics
            try:
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    ORDER BY idx_scan DESC 
                    LIMIT 10;
                """)
                
                index_stats = cursor.fetchall()
                logger.info("Top 10 most used indexes:")
                for index in index_stats:
                    logger.info(f"  {index[2]} on {index[1]}: {index[3]} scans")
                    
            except Exception as e:
                logger.warning(f"Could not get index statistics: {e}")
            
            # Slow queries (if pg_stat_statements is available)
            try:
                cursor.execute("""
                    SELECT 
                        query,
                        calls,
                        total_time,
                        mean_time
                    FROM pg_stat_statements 
                    WHERE mean_time > 1000
                    ORDER BY mean_time DESC 
                    LIMIT 5;
                """)
                
                slow_queries = cursor.fetchall()
                if slow_queries:
                    logger.info("Top 5 slowest queries:")
                    for query in slow_queries:
                        logger.info(f"  Query: {query[0][:100]}... (avg: {query[3]:.2f}ms, calls: {query[1]})")
                else:
                    logger.info("No slow queries found")
                    
            except Exception as e:
                logger.warning(f"Could not get slow query statistics: {e}")
            
            logger.info("Database statistics collected")
            
    except Exception as e:
        logger.error(f"Error collecting database statistics: {e}")
        raise

def main():
    """Main optimization function"""
    try:
        logger.info("Starting database optimization...")
        
        # Check if we're in production
        if settings.DEBUG:
            logger.warning("Running in DEBUG mode. This script is designed for production.")
        
        # Optimize database settings
        optimize_database_settings()
        
        # Create indexes
        create_database_indexes()
        
        # Analyze tables
        analyze_tables()
        
        # Vacuum tables
        vacuum_tables()
        
        # Get statistics
        get_database_stats()
        
        logger.info("Database optimization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 