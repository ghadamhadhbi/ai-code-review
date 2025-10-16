// services/reviewService.js - COMPLETE FIXED VERSION
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8003';

/**
 * Service for handling review-related API calls
 * FIXED: All routes match backend exactly with proper error handling
 */
class ReviewService {
  /**
   * Get all reviews with optional filtering and pagination
   */
async getReviews(filters = {}) {
  try {
    const queryParams = new URLSearchParams();
    
    Object.keys(filters).forEach(key => {
      if (filters[key] !== undefined && filters[key] !== null && filters[key] !== '') {
        queryParams.append(key, filters[key]);
      }
    });

    const url = `${API_BASE_URL}/api/reviews${queryParams.toString() ? '?' + queryParams : ''}`;
    console.log('Fetching reviews from:', url);
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('Raw API response data:', data); // Add this for debugging
    
    // Backend returns { reviews: [], page: 1, page_size: 20, total: 100, total_pages: 5 }
    return {
      data: Array.isArray(data.reviews) ? data.reviews : [],
      pagination: {
        page: data.page || 1,
        page_size: data.page_size || 20, // Add this line
        total: data.total || 0,
        pages: data.total_pages || 1
      }
    };
  } catch (error) {
    console.error('Error fetching reviews:', error);
    throw error;
  }
  }

  /**
   * Get a specific review by ID
   */
  async getReviewById(reviewId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/reviews/${reviewId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      // Backend returns { review: {...} }
      return { data: data.review || data };
    } catch (error) {
      console.error('Error fetching review:', error);
      throw error;
    }
  }

  /**
   * Get upload status by UPLOAD ID
   */
  async getUploadStatus(uploadId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/upload/status/${uploadId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching upload status:', error);
      throw error;
    }
  }

  /**
   * Get upload review status (from reviews router)
   */
  async getUploadReviewStatus(uploadId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/reviews/upload/${uploadId}/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching upload review status:', error);
      throw error;
    }
  }

  /**
   * Cancel an upload/review
   */
  async cancelUpload(uploadId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/reviews/upload/${uploadId}/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error canceling upload:', error);
      throw error;
    }
  }

  /**
   * ✅ FIXED: Get review statistics
   * Backend returns stats object directly (no wrapper)
   */
  async getReviewStats(days = 7) {
    try {
      console.log(`Fetching stats for ${days} days`);
      
      const response = await fetch(`${API_BASE_URL}/api/reviews/stats?days=${days}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 404 || response.status === 422) {
          console.warn('Stats endpoint not available or invalid params');
          return {
            data: this.getDefaultStats(days)
          };
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Backend returns stats object directly, wrap it for consistency
      return { 
        data: {
          period_days: data.period_days || days,
          total_reviews: data.total_reviews || 0,
          pending_reviews: data.pending_reviews || 0,
          processing_reviews: data.processing_reviews || 0,
          completed_reviews: data.completed_reviews || 0,
          failed_reviews: data.failed_reviews || 0,
          average_score: data.average_score,
          average_processing_time_ms: data.average_processing_time_ms,
          total_suggestions: data.total_suggestions || 0,
          total_tokens_used: data.total_tokens_used || 0
        }
      };
    } catch (error) {
      if (!error.message.includes('404') && !error.message.includes('422')) {
        console.error('Error fetching review stats:', error);
      }
      // Return default stats instead of throwing
      return {
        data: this.getDefaultStats(days)
      };
    }
  }

  /**
   * Get default stats object
   */
  getDefaultStats(days = 7) {
    return {
      period_days: days,
      total_reviews: 0,
      pending_reviews: 0,
      processing_reviews: 0,
      completed_reviews: 0,
      failed_reviews: 0,
      average_score: null,
      average_processing_time_ms: null,
      total_suggestions: 0,
      total_tokens_used: 0
    };
  }

  /**
   * Get suggestions for a specific review (if endpoint exists)
   */
  async getReviewSuggestions(reviewId, filters = {}) {
    try {
      const queryParams = new URLSearchParams();
      
      if (filters.severity) {
        queryParams.append('severity', filters.severity);
      }
      if (filters.suggestion_type) {
        queryParams.append('suggestion_type', filters.suggestion_type);
      }

      const url = `${API_BASE_URL}/api/reviews/${reviewId}/suggestions${queryParams.toString() ? '?' + queryParams : ''}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching review suggestions:', error);
      throw error;
    }
  }

  /**
   * Submit review feedback (if endpoint exists)
   */
  async submitFeedback(reviewId, feedback) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/reviews/${reviewId}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedback)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error submitting feedback:', error);
      throw error;
    }
  }

  /**
   * Delete a review (if endpoint exists)
   */
  async deleteReview(reviewId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/reviews/${reviewId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error deleting review:', error);
      throw error;
    }
  }

  /**
   * Upload files for review
   */
  async uploadFiles(formData) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header - let browser set it with boundary
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading files:', error);
      throw error;
    }
  }

  /**
   * Health check for the API
   */
  async healthCheck() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }
}

const reviewService = new ReviewService();
export default reviewService;

// ============================================================================
// Error handling utilities
// ============================================================================
export const handleApiError = (error) => {
  if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
    return {
      message: 'Impossible de se connecter au serveur. Vérifiez votre connexion.',
      type: 'network_error'
    };
  }

  if (error.message.includes('401')) {
    return {
      message: 'Authentification requise. Veuillez vous reconnecter.',
      type: 'auth_error'
    };
  }

  if (error.message.includes('403')) {
    return {
      message: 'Vous n\'avez pas la permission d\'effectuer cette action.',
      type: 'permission_error'
    };
  }

  if (error.message.includes('404')) {
    return {
      message: 'La ressource demandée n\'a pas été trouvée.',
      type: 'not_found'
    };
  }

  if (error.message.includes('422')) {
    return {
      message: 'Données invalides envoyées au serveur.',
      type: 'validation_error'
    };
  }

  if (error.message.includes('500')) {
    return {
      message: 'Erreur serveur. Veuillez réessayer plus tard.',
      type: 'server_error'
    };
  }

  if (error.message.includes('503')) {
    return {
      message: 'Le service est temporairement indisponible.',
      type: 'service_unavailable'
    };
  }

  return {
    message: error.message || 'Une erreur inattendue s\'est produite.',
    type: 'unknown_error'
  };
};

// ============================================================================
// Format review data for display
// ============================================================================
export const formatReviewForDisplay = (review) => {
  if (!review) return null;

  const createdAt = review.created_at ? new Date(review.created_at) : null;
  const completedAt = review.completed_at ? new Date(review.completed_at) : null;
  const now = new Date();
  
  let duration = 'N/A';
  if (createdAt) {
    const endTime = completedAt || now;
    const diffMs = endTime - createdAt;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    
    if (diffHours > 0) {
      duration = `${diffHours}h ${diffMins % 60}m`;
    } else if (diffMins > 0) {
      duration = `${diffMins}m`;
    } else {
      duration = 'À l\'instant';
    }
  }
  
  const filename = review.filename || 
                   (review.files && review.files[0] && review.files[0].filename) ||
                   'Fichier inconnu';
  
  const issues = Array.isArray(review.suggestions) 
    ? review.suggestions.filter(s => s.severity === 'high' || s.severity === 'critical').length
    : 0;

  return {
    id: review.id || review.review_id,
    title: filename,
    filename: filename,
    status: review.status || 'unknown',
    priority: review.priority || 'medium',
    language: review.language || 'unknown',
    createdAt: review.created_at,
    completedAt: review.completed_at,
    duration: duration,
    issues: issues,
    suggestions: Array.isArray(review.suggestions) ? review.suggestions.length : 0,
    linesOfCode: review.lines_of_code || 0,
    score: review.overall_score,
    reviewer: 'Assistant IA',
    progress: calculateProgress(review.status),
    summary: review.summary,
    model_used: review.model_used,
    tokens_used: review.tokens_used || 0,
    processing_time_ms: review.processing_time_ms || 0,
    upload_id: review.upload_id,
    error_message: review.error_message,
    suggestionsData: review.suggestions || [],
    files: review.files || []
  };
};

const calculateProgress = (status) => {
  switch (status) {
    case 'pending':
    case 'uploaded':
      return 0;
    case 'processing':
    case 'in_progress':
      return 50;
    case 'completed':
      return 100;
    case 'failed':
    case 'cancelled':
      return 0;
    default:
      return 0;
  }
};

// ============================================================================
// Format stats for display
// ============================================================================
export const formatStatsForDisplay = (stats) => {
  if (!stats) return null;

  return {
    period_days: stats.period_days || 7,
    total_reviews: stats.total_reviews || 0,
    pending_reviews: stats.pending_reviews || 0,
    processing_reviews: stats.processing_reviews || 0,
    completed_reviews: stats.completed_reviews || 0,
    failed_reviews: stats.failed_reviews || 0,
    average_score: stats.average_score !== null && stats.average_score !== undefined 
      ? Math.round(stats.average_score * 10) / 10 
      : null,
    average_processing_time_ms: stats.average_processing_time_ms !== null && stats.average_processing_time_ms !== undefined
      ? Math.round(stats.average_processing_time_ms)
      : null,
    total_suggestions: stats.total_suggestions || 0,
    total_tokens_used: stats.total_tokens_used || 0,
    // Derived metrics
    success_rate: stats.total_reviews > 0 
      ? Math.round((stats.completed_reviews / stats.total_reviews) * 100)
      : 0,
    failure_rate: stats.total_reviews > 0
      ? Math.round((stats.failed_reviews / stats.total_reviews) * 100)
      : 0
  };
};

// ============================================================================
// WebSocket utilities (if needed)
// ============================================================================
export const createWebSocketConnection = (onMessage, onError, onClose) => {
  const wsUrl = API_BASE_URL.replace('http', 'ws');
  const ws = new WebSocket(`${wsUrl}/api/reviews/ws/reviews`);

  ws.onopen = () => {
    console.log('WebSocket connected');
    // Send ping every 30 seconds to keep connection alive
    setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    if (onError) onError(error);
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
    if (onClose) onClose();
  };

  return ws;
};

export const subscribeToReview = (ws, reviewId) => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'subscribe',
      review_id: reviewId
    }));
  }
};