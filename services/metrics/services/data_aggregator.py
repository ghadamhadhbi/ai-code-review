# =====================================================
# services/metrics/services/data_aggregator.py
# =====================================================

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import structlog

from core.database import get_db_session
from core.config import settings

logger = structlog.get_logger(__name__)


class DataAggregator:
    """Aggregates and processes metrics data"""
    
    def __init__(self):
        self.is_running = False
        self.aggregations_run = 0
        self.last_aggregation_time: Optional[datetime] = None
        self.cache = {}
        self.cache_timestamps = {}
    
    async def start_background_processing(self):
        """Start background aggregation tasks"""
        self.is_running = True
        logger.info("Starting data aggregation background processing")
        
        # Schedule periodic aggregations
        while self.is_running:
            try:
                await self._run_periodic_aggregations()
                await asyncio.sleep(settings.AGGREGATION_INTERVAL_MINUTES * 60)
                
            except Exception as e:
                logger.error("Background aggregation failed", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def stop(self):
        """Stop background processing"""
        logger.info("Stopping data aggregator")
        self.is_running = False
    
    async def process_review_metrics(self, metrics: Dict[str, Any]):
        """Process metrics from a completed review"""
        try:
            # Store individual review metrics
            async with get_db_session() as db:
                await self._store_review_metrics(db, metrics)
            
            # Update real-time aggregations
            await self._update_realtime_metrics(metrics)
            
            logger.debug("Processed review metrics", review_id=metrics.get("review_id"))
        
        except Exception as e:
            logger.error("Failed to process review metrics", error=str(e))
    
    async def process_metric_event(self, event_data: Dict[str, Any]):
        """Process general metric events"""
        try:
            # Store system metric
            async with get_db_session() as db:
                await self._store_system_metric(db, event_data)
            
            logger.debug("Processed metric event", type=event_data.get("type"))
        
        except Exception as e:
            logger.error("Failed to process metric event", error=str(e))
    
    async def _run_periodic_aggregations(self):
        """Run periodic data aggregations"""
        try:
            logger.info("Running periodic data aggregations")
            
            async with get_db_session() as db:
                # Daily aggregations
                await self._aggregate_daily_metrics(db)
                
                # Hourly aggregations
                await self._aggregate_hourly_metrics(db)
                
                # Clean up old data
                await self._cleanup_old_data(db)
                
                # Clear expired cache
                self._clear_expired_cache()
            
            self.aggregations_run += 1
            self.last_aggregation_time = datetime.utcnow()
            
            logger.info("Completed periodic data aggregations")
        
        except Exception as e:
            logger.error("Periodic aggregation failed", error=str(e))
    
    async def _store_review_metrics(self, db, metrics: Dict[str, Any]):
        """Store individual review metrics"""
        query = """
            INSERT INTO system_metrics (
                metric_name, metric_value, metric_unit, tags, recorded_at
            ) VALUES ($1, $2, $3, $4, NOW())
        """
        
        # Store processing time
        if metrics.get("processing_time_ms"):
            await db.execute(
                query,
                "review.processing_time",
                metrics["processing_time_ms"],
                "milliseconds",
                {"review_id": metrics.get("review_id")}
            )
        
        # Store token usage
        if metrics.get("tokens_used"):
            await db.execute(
                query,
                "review.tokens_used",
                metrics["tokens_used"],
                "tokens",
                {"review_id": metrics.get("review_id")}
            )
        
        # Store quality score
        if metrics.get("overall_score"):
            await db.execute(
                query,
                "review.quality_score",
                metrics["overall_score"],
                "score",
                {"review_id": metrics.get("review_id")}
            )
        
        # Store suggestions count
        await db.execute(
            query,
            "review.suggestions_count",
            metrics.get("suggestions_count", 0),
            "count",
            {"review_id": metrics.get("review_id")}
        )
    
    async def _store_system_metric(self, db, event_data: Dict[str, Any]):
        """Store system metrics"""
        query = """
            INSERT INTO system_metrics (
                metric_name, metric_value, metric_unit, tags, recorded_at
            ) VALUES ($1, $2, $3, $4, NOW())
        """
        
        await db.execute(
            query,
            event_data.get("name", "unknown"),
            event_data.get("value", 0),
            event_data.get("unit", "count"),
            event_data.get("tags", {})
        )
    
    async def _aggregate_daily_metrics(self, db):
        """Create daily metric aggregations"""
        today = datetime.utcnow().date()
        
        # Daily review counts
        query = """
            INSERT INTO system_metrics (metric_name, metric_value, metric_unit, tags, recorded_at)
            SELECT 
                'daily.reviews.total',
                COUNT(*),
                'count',
                '{"date": "' || $1 || '"}',
                NOW()
            FROM review_results
            WHERE DATE(created_at) = $1::date
            ON CONFLICT DO NOTHING
        """
        await db.execute(query, today)
        
        # Daily completion rate
        query = """
            INSERT INTO system_metrics (metric_name, metric_value, metric_unit, tags, recorded_at)
            SELECT 
                'daily.reviews.completion_rate',
                ROUND(
                    COUNT(*) FILTER (WHERE status = 'completed')::float / 
                    NULLIF(COUNT(*), 0) * 100, 2
                ),
                'percentage',
                '{"date": "' || $1 || '"}',
                NOW()
            FROM review_results
            WHERE DATE(created_at) = $1::date
            ON CONFLICT DO NOTHING
        """
        await db.execute(query, today)
        
        # Daily average quality score
        query = """
            INSERT INTO system_metrics (metric_name, metric_value, metric_unit, tags, recorded_at)
            SELECT 
                'daily.reviews.avg_quality_score',
                ROUND(AVG(overall_score), 1),
                'score',
                '{"date": "' || $1 || '"}',
                NOW()
            FROM review_results
            WHERE DATE(created_at) = $1::date AND overall_score IS NOT NULL
            ON CONFLICT DO NOTHING
        """
        await db.execute(query, today)
    
    async def _aggregate_hourly_metrics(self, db):
        """Create hourly metric aggregations"""
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        # Hourly processing times
        query = """
            INSERT INTO system_metrics (metric_name, metric_value, metric_unit, tags, recorded_at)
            SELECT 
                'hourly.processing.avg_time',
                ROUND(AVG(processing_time_ms), 1),
                'milliseconds',
                '{"hour": "' || $1 || '"}',
                NOW()
            FROM review_results
            WHERE DATE_TRUNC('hour', created_at) = $1::date 
            AND processing_time_ms > 0
            ON CONFLICT DO NOTHING
        """
        await db.execute(query, current_hour)
        
        # Hourly token usage
        query = """
            INSERT INTO system_metrics (metric_name, metric_value, metric_unit, tags, recorded_at)
            SELECT 
                'hourly.tokens.total',
                SUM(tokens_used),
                'tokens',
                '{"hour": "' || $1 || '"}',
                NOW()
            FROM review_results
            WHERE DATE_TRUNC('hour', created_at) = $1::date
            ON CONFLICT DO NOTHING
        """
        await db.execute(query, current_hour)
    
    async def _cleanup_old_data(self, db):
        """Clean up old metric data"""
        cutoff_date = datetime.utcnow() - timedelta(days=settings.RETENTION_DAYS)
        
        # Clean up old system metrics
        query = """
            DELETE FROM system_metrics 
            WHERE recorded_at < $1
        """
        
        result = await db.execute(query, cutoff_date)
        logger.info(f"Cleaned up old metrics", deleted_rows=result.split()[1] if result else 0)
    
    async def _update_realtime_metrics(self, metrics: Dict[str, Any]):
        """Update real-time metrics cache"""
        # Update processing time rolling average
        self._update_rolling_average("processing_time", metrics.get("processing_time_ms", 0))
        
        # Update token usage rolling average
        self._update_rolling_average("tokens_used", metrics.get("tokens_used", 0))
        
        # Update quality score rolling average
        if metrics.get("overall_score"):
            self._update_rolling_average("quality_score", metrics["overall_score"])
    
    def _update_rolling_average(self, metric_name: str, value: float):
        """Update rolling average for a metric"""
        if metric_name not in self.cache:
            self.cache[metric_name] = {"values": [], "average": 0}
        
        # Add new value
        self.cache[metric_name]["values"].append(value)
        
        # Keep only last 100 values
        if len(self.cache[metric_name]["values"]) > 100:
            self.cache[metric_name]["values"] = self.cache[metric_name]["values"][-100:]
        
        # Recalculate average
        values = self.cache[metric_name]["values"]
        self.cache[metric_name]["average"] = sum(values) / len(values) if values else 0
        
        # Update timestamp
        self.cache_timestamps[metric_name] = datetime.utcnow()
    
    def _clear_expired_cache(self):
        """Clear expired cache entries"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=settings.CACHE_TTL_MINUTES)
        
        expired_keys = [
            key for key, timestamp in self.cache_timestamps.items()
            if timestamp < cutoff_time
        ]
        
        for key in expired_keys:
            del self.cache[key]
            del self.cache_timestamps[key]
        
        if expired_keys:
            logger.debug("Cleared expired cache entries", keys=expired_keys)
    
    def get_cached_metrics(self) -> Dict[str, Any]:
        """Get current cached metrics"""
        return {
            metric_name: data["average"]
            for metric_name, data in self.cache.items()
        }