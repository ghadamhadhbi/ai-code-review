/**
 * Metrics Service - Frontend
 * Handles all metrics and analytics API calls to the backend
 * Location: frontend/src/services/metricsService.js
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const metricsApi = axios.create({
  baseURL: `${API_BASE_URL}/api/analytics`,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
metricsApi.interceptors.request.use(
  (config) => {
    console.log(`[Metrics API] ${config.method.toUpperCase()} ${config.url}`, config.params);
    return config;
  },
  (error) => {
    console.error('[Metrics API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
metricsApi.interceptors.response.use(
  (response) => {
    console.log(`[Metrics API] Response:`, response.data);
    return response;
  },
  (error) => {
    console.error('[Metrics API] Response error:', error.response?.data || error.message);
    
    // Handle specific error cases
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 503:
          throw new Error('Metrics service is currently unavailable. Please try again later.');
        case 504:
          throw new Error('Request timeout. The metrics service took too long to respond.');
        case 500:
          throw new Error(data.detail || 'Internal server error occurred.');
        default:
          throw new Error(data.detail || data.message || 'Failed to fetch metrics data.');
      }
    } else if (error.request) {
      throw new Error('No response from server. Please check your connection.');
    } else {
      throw new Error(error.message || 'An unexpected error occurred.');
    }
  }
);

/**
 * Metrics Service Class
 */
class MetricsService {
  /**
   * Get dashboard statistics
   * @param {number} days - Number of days to analyze (1-90)
   * @returns {Promise<Object>} Dashboard statistics
   */
  async getDashboardStats(days = 7) {
    try {
      const response = await metricsApi.get('/stats', {
        params: { days },
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      throw error;
    }
  }

  /**
   * Get issue analytics
   * @param {number} days - Number of days to analyze (1-90)
   * @returns {Promise<Object>} Issue analytics data
   */
  async getIssueAnalytics(days = 30) {
    try {
      const response = await metricsApi.get('/analytics/issues', {
        params: { days },
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching issue analytics:', error);
      throw error;
    }
  }

  /**
   * Get performance analytics
   * @param {number} hours - Number of hours to analyze (1-168)
   * @returns {Promise<Object>} Performance analytics data
   */
  async getPerformanceAnalytics(hours = 24) {
    try {
      const response = await metricsApi.get('/analytics/performance', {
        params: { hours },
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching performance analytics:', error);
      throw error;
    }
  }

  /**
   * Get quality analytics
   * @param {number} days - Number of days to analyze (1-90)
   * @returns {Promise<Object>} Quality analytics data
   */
  async getQualityAnalytics(days = 30) {
    try {
      const response = await metricsApi.get('/analytics/quality', {
        params: { days },
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching quality analytics:', error);
      throw error;
    }
  }

  /**
   * Get all analytics data in one call
   * @param {Object} params - Parameters for different analytics
   * @param {number} params.statsDays - Days for dashboard stats
   * @param {number} params.issuesDays - Days for issue analytics
   * @param {number} params.performanceHours - Hours for performance analytics
   * @param {number} params.qualityDays - Days for quality analytics
   * @returns {Promise<Object>} All analytics data
   */
  async getAllAnalytics(params = {}) {
    const {
      statsDays = 7,
      issuesDays = 30,
      performanceHours = 24,
      qualityDays = 30,
    } = params;

    try {
      const [stats, issues, performance, quality] = await Promise.allSettled([
        this.getDashboardStats(statsDays),
        this.getIssueAnalytics(issuesDays),
        this.getPerformanceAnalytics(performanceHours),
        this.getQualityAnalytics(qualityDays),
      ]);

      return {
        stats: stats.status === 'fulfilled' ? stats.value : null,
        issues: issues.status === 'fulfilled' ? issues.value : null,
        performance: performance.status === 'fulfilled' ? performance.value : null,
        quality: quality.status === 'fulfilled' ? quality.value : null,
        errors: {
          stats: stats.status === 'rejected' ? stats.reason.message : null,
          issues: issues.status === 'rejected' ? issues.reason.message : null,
          performance: performance.status === 'rejected' ? performance.reason.message : null,
          quality: quality.status === 'rejected' ? quality.reason.message : null,
        },
      };
    } catch (error) {
      console.error('Error fetching all analytics:', error);
      throw error;
    }
  }

  /**
   * Check if metrics service is available
   * @returns {Promise<boolean>} Service availability status
   */
  async checkServiceHealth() {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`, {
        timeout: 5000,
      });
      
      const components = response.data.components || {};
      return components.database === 'healthy';
    } catch (error) {
      console.error('Metrics service health check failed:', error);
      return false;
    }
  }

  /**
   * Format statistics for display
   * @param {Object} stats - Raw statistics data
   * @returns {Object} Formatted statistics
   */
  formatStats(stats) {
    if (!stats) return null;

    return {
      totalReviews: stats.total_reviews || 0,
      pendingReviews: stats.pending_reviews || 0,
      processingReviews: stats.processing_reviews || 0,
      completedReviews: stats.completed_reviews || 0,
      failedReviews: stats.failed_reviews || 0,
      averageScore: stats.average_score ? stats.average_score.toFixed(1) : 'N/A',
      averageProcessingTime: stats.average_processing_time_ms 
        ? `${(stats.average_processing_time_ms / 1000).toFixed(2)}s`
        : 'N/A',
      totalSuggestions: stats.total_suggestions || 0,
      totalTokensUsed: stats.total_tokens_used ? stats.total_tokens_used.toLocaleString() : '0',
      periodDays: stats.period_days || 7,
    };
  }

  /**
   * Calculate completion rate
   * @param {Object} stats - Statistics data
   * @returns {string} Completion rate percentage
   */
  calculateCompletionRate(stats) {
    if (!stats || !stats.total_reviews || stats.total_reviews === 0) {
      return '0%';
    }
    
    const rate = (stats.completed_reviews / stats.total_reviews) * 100;
    return `${rate.toFixed(1)}%`;
  }

  /**
   * Calculate failure rate
   * @param {Object} stats - Statistics data
   * @returns {string} Failure rate percentage
   */
  calculateFailureRate(stats) {
    if (!stats || !stats.total_reviews || stats.total_reviews === 0) {
      return '0%';
    }
    
    const rate = (stats.failed_reviews / stats.total_reviews) * 100;
    return `${rate.toFixed(1)}%`;
  }

  /**
   * Get severity color for issues
   * @param {string} severity - Issue severity level
   * @returns {string} Color code
   */
  getSeverityColor(severity) {
    const colors = {
      critical: '#dc2626',
      high: '#ea580c',
      medium: '#ca8a04',
      low: '#16a34a',
      info: '#3b82f6',
    };
    return colors[severity?.toLowerCase()] || '#6b7280';
  }

  /**
   * Get quality tier color
   * @param {string} tier - Quality tier
   * @returns {string} Color code
   */
  getQualityTierColor(tier) {
    const colors = {
      excellent: '#10b981',
      good: '#3b82f6',
      fair: '#f59e0b',
      poor: '#ef4444',
      very_poor: '#991b1b',
    };
    return colors[tier?.toLowerCase()] || '#6b7280';
  }

  /**
   * Format timestamp to readable date
   * @param {string} timestamp - ISO timestamp
   * @returns {string} Formatted date
   */
  formatDate(timestamp) {
    if (!timestamp) return 'N/A';
    
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  /**
   * Format timestamp to readable datetime
   * @param {string} timestamp - ISO timestamp
   * @returns {string} Formatted datetime
   */
  formatDateTime(timestamp) {
    if (!timestamp) return 'N/A';
    
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}

// Export singleton instance
const metricsService = new MetricsService();
export default metricsService;

// Also export the class for testing
export { MetricsService };