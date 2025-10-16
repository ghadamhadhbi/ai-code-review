# =====================================================
# services/metrics/services/data_aggregator.py
# =====================================================

import asyncio
from datetime import datetime
import structlog

from core.database import db_pool

logger = structlog.get_logger(__name__)


class DataAggregator:
    def __init__(self):
        self.is_running = False
        self.aggregations_run = 0
        self.last_aggregation_time = None
        
    async def start_background_processing(self):
        """Start background aggregation tasks"""
        self.is_running = True
        logger.info("✅ Data aggregator started")
        
        while self.is_running:
            try:
                await self.run_aggregations()
                self.aggregations_run += 1
                self.last_aggregation_time = datetime.utcnow().isoformat()
                await asyncio.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error("Aggregation error", error=str(e))
                await asyncio.sleep(60)
                
    async def stop(self):
        """Stop background processing"""
        self.is_running = False
        logger.info("Data aggregator stopped")
        
    async def run_aggregations(self):
        """Run data aggregation tasks"""
        async with db_pool.acquire() as conn:
            # Record system metrics
            await conn.execute("""
                INSERT INTO system_metrics (metric_name, metric_value, metric_unit)
                SELECT 
                    'reviews_completed_today',
                    COUNT(*),
                    'count'
                FROM review_results
                WHERE DATE(created_at) = CURRENT_DATE
                AND status = 'completed'
            """)
            
        logger.debug("Aggregations completed")
        
    async def record_review_completion(self, data):
        """Record review completion metrics"""
        logger.debug("Recording review completion", review_id=data.get("review_id"))
        
    async def record_review_failure(self, data):
        """Record review failure metrics"""
        logger.debug("Recording review failure", review_id=data.get("review_id"))
