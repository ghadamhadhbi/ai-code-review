"""
Data aggregator for metrics service - FIXED VERSION
Handles periodic data aggregations with proper error handling
"""

import asyncio
from datetime import datetime
import structlog

from core.database import get_db_pool, is_db_available
from core.config import settings

logger = structlog.get_logger(__name__)


class DataAggregator:
    def __init__(self):
        self.is_running = False
        self.aggregations_run = 0
        self.last_aggregation_time = None
        self.failed_aggregations = 0
        
    async def start_background_processing(self):
        """Start background aggregation processing"""
        self.is_running = True
        logger.info("✅ Data aggregator started")
        
        # Wait a bit for database to initialize
        await asyncio.sleep(2)
        
        while self.is_running:
            try:
                # Check if database is available before running aggregations
                if not is_db_available():
                    logger.warning(
                        "Database not available - skipping aggregation",
                        skip_count=self.failed_aggregations + 1
                    )
                    self.failed_aggregations += 1
                    await asyncio.sleep(60)  # Wait longer when DB unavailable
                    continue
                
                # Run aggregations
                await self.run_aggregations()
                self.aggregations_run += 1
                self.last_aggregation_time = datetime.utcnow().isoformat()
                self.failed_aggregations = 0  # Reset failure count on success
                
                logger.info(
                    "Aggregation completed successfully",
                    total_runs=self.aggregations_run,
                    last_run=self.last_aggregation_time
                )
                
                await asyncio.sleep(settings.AGGREGATION_INTERVAL_SECONDS)
                
            except Exception as e:
                self.failed_aggregations += 1
                logger.error(
                    "Aggregation error",
                    error=str(e),
                    error_type=type(e).__name__,
                    failed_count=self.failed_aggregations
                )
                await asyncio.sleep(60)  # Wait before retry
                
    async def stop(self):
        """Stop background processing"""
        self.is_running = False
        logger.info(
            "Data aggregator stopped",
            total_runs=self.aggregations_run,
            failed_runs=self.failed_aggregations
        )
        
    async def run_aggregations(self):
        """Run periodic data aggregations"""
        if not is_db_available():
            logger.warning("Database not available - skipping aggregations")
            return
        
        db_pool = await get_db_pool()
        if not db_pool:
            logger.warning("Database pool is None - skipping aggregations")
            return
        
        try:
            async with db_pool.acquire() as conn:
                # Aggregate daily review counts
                await conn.execute("""
                    INSERT INTO system_metrics (metric_name, metric_value, metric_unit, recorded_at)
                    SELECT 
                        'reviews_completed_today' as metric_name,
                        COUNT(*)::decimal as metric_value,
                        'count' as metric_unit,
                        CURRENT_TIMESTAMP as recorded_at
                    FROM review_results
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND status = 'completed'
                    ON CONFLICT DO NOTHING
                """)
                
                # Aggregate average processing time
                await conn.execute("""
                    INSERT INTO system_metrics (metric_name, metric_value, metric_unit, recorded_at)
                    SELECT 
                        'avg_processing_time_today' as metric_name,
                        AVG(processing_time_ms)::decimal as metric_value,
                        'ms' as metric_unit,
                        CURRENT_TIMESTAMP as recorded_at
                    FROM review_results
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND status = 'completed'
                    AND processing_time_ms > 0
                    ON CONFLICT DO NOTHING
                """)
                
                # Aggregate token usage
                await conn.execute("""
                    INSERT INTO system_metrics (metric_name, metric_value, metric_unit, recorded_at)
                    SELECT 
                        'total_tokens_today' as metric_name,
                        SUM(tokens_used)::decimal as metric_value,
                        'tokens' as metric_unit,
                        CURRENT_TIMESTAMP as recorded_at
                    FROM review_results
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND status = 'completed'
                    ON CONFLICT DO NOTHING
                """)
                
            logger.debug(
                "Aggregations completed successfully",
                run_count=self.aggregations_run + 1
            )
            
        except Exception as e:
            logger.error(
                "Error running aggregations",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
        
    async def record_review_completion(self, data: dict):
        """Record a review completion event"""
        if not is_db_available():
            logger.warning("Database not available - cannot record review completion")
            return
        
        try:
            logger.debug(
                "Recording review completion",
                review_id=data.get("review_id"),
                upload_id=data.get("upload_id")
            )
            
            db_pool = await get_db_pool()
            if not db_pool:
                return
            
            import json
            tags_json = json.dumps({
               'review_id': str(data.get('review_id')),
               'upload_id': str(data.get('upload_id'))
              })
        
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO system_metrics (metric_name, metric_value, metric_unit, tags)
                    VALUES ($1, $2, $3, $4)
                """, 
                'review_completed', 
                1.0, 
                'count',
                tags_json  
                )
                
        except Exception as e:
            logger.error("Error recording review completion", error=str(e))
        
    async def record_review_failure(self, data: dict):
        """Record a review failure event"""
        if not is_db_available():
            logger.warning("Database not available - cannot record review failure")
            return
        
        try:
            logger.debug(
                "Recording review failure",
                review_id=data.get("review_id"),
                error=data.get("error")
            )
            
            db_pool = await get_db_pool()
            if not db_pool:
                return
            
            import json
            tags_json = json.dumps({
               'review_id': str(data.get('review_id')),
               'error': str(data.get('error', 'Unknown error'))
            })

            

            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO system_metrics (metric_name, metric_value, metric_unit, tags)
                    VALUES ($1, $2, $3, $4)
                """,
                'review_failed',
                1.0,
                'count',
                tags_json 
                )
                
        except Exception as e:
            logger.error("Error recording review failure", error=str(e))
        
    async def record_status_update(self, data: dict):
        """Record a status update event"""
        if not is_db_available():
            logger.debug("Database not available - skipping status update recording")
            return
        
        logger.debug(
            "Recording status update",
            review_id=data.get("review_id"),
            status=data.get("status")
        )
        
    def get_stats(self) -> dict:
        """Get aggregator statistics"""
        return {
            "is_running": self.is_running,
            "total_runs": self.aggregations_run,
            "failed_runs": self.failed_aggregations,
            "last_run_time": self.last_aggregation_time,
            "database_available": is_db_available(),
        }


# Global aggregator instance
aggregator = DataAggregator()


async def start_aggregator():
    """Start the data aggregator"""
    await aggregator.start_background_processing()


async def stop_aggregator():
    """Stop the data aggregator"""
    await aggregator.stop()


def get_aggregator() -> DataAggregator:
    """Get the global aggregator instance"""
    return aggregator