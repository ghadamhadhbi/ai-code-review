# =====================================================
# services/shared/utils/metrics.py
# =====================================================

"""
Common metrics utilities for all services
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Collect and track service metrics"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, list] = {}
        self.start_time = time.time()
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict] = None):
        """Increment a counter metric"""
        key = f"{self.service_name}.{name}"
        self.counters[key] = self.counters.get(key, 0) + value
        
        logger.debug("Counter incremented", metric=key, value=value, tags=tags)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict] = None):
        """Set a gauge metric"""
        key = f"{self.service_name}.{name}"
        self.gauges[key] = value
        
        logger.debug("Gauge set", metric=key, value=value, tags=tags)
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict] = None):
        """Record a histogram value"""
        key = f"{self.service_name}.{name}"
        if key not in self.histograms:
            self.histograms[key] = []
        
        self.histograms[key].append(value)
        
        # Keep only last 1000 values
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]
        
        logger.debug("Histogram recorded", metric=key, value=value, tags=tags)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        metrics = {
            "service": self.service_name,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
            "counters": self.counters.copy(),
            "gauges": self.gauges.copy(),
        }
        
        # Calculate histogram statistics
        histogram_stats = {}
        for key, values in self.histograms.items():
            if values:
                sorted_values = sorted(values)
                count = len(sorted_values)
                
                histogram_stats[key] = {
                    "count": count,
                    "min": sorted_values[0],
                    "max": sorted_values[-1],
                    "avg": sum(sorted_values) / count,
                    "p50": sorted_values[int(count * 0.5)],
                    "p95": sorted_values[int(count * 0.95)],
                    "p99": sorted_values[int(count * 0.99)],
                }
        
        metrics["histograms"] = histogram_stats
        return metrics
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        logger.info("Metrics reset", service=self.service_name)


class Timer:
    """Context manager for timing operations"""
    
    def __init__(self, metrics_collector: MetricsCollector, metric_name: str, tags: Optional[Dict] = None):
        self.metrics_collector = metrics_collector
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.metrics_collector.record_histogram(
                f"{self.metric_name}.duration_seconds",
                duration,
                self.tags
            )

