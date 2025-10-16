// context/ReviewContext.jsx - COMPLETE WITH REAL API
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import reviewService, { formatReviewForDisplay, formatStatsForDisplay } from '../services/reviewService';

const ReviewContext = createContext();

export const useReviewContext = () => {
  const context = useContext(ReviewContext);
  if (!context) {
    throw new Error('useReviewContext must be used within ReviewProvider');
  }
  return context;
};

export const ReviewProvider = ({ children }) => {
  // State
  const [reviews, setReviews] = useState([]);
  const [stats, setStats] = useState({
    total_reviews: 0,
    pending_reviews: 0,
    processing_reviews: 0,
    completed_reviews: 0,
    failed_reviews: 0,
    average_score: null,
    total_suggestions: 0
  });
  const [loading, setLoading] = useState({
    reviews: false,
    stats: false,
    detail: false
  });
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    status: '',
    priority: '',
    searchQuery: ''
  });
  const [sort, setSort] = useState('created_desc');
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0
  });

  // WebSocket connection for real-time updates
  const [ws, setWs] = useState(null);

  // Initialize WebSocket connection
  useEffect(() => {
    const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8003';
    const wsUrl = API_BASE_URL.replace('http', 'ws');
    
    try {
      const websocket = new WebSocket(`${wsUrl}/api/reviews/ws/reviews`);
      
      websocket.onopen = () => {
        console.log('WebSocket connected to reviews');
      };
      
      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (err) {
          console.error('WebSocket message parse error:', err);
        }
      };
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      websocket.onclose = () => {
        console.log('WebSocket disconnected');
        // Attempt reconnection after 5 seconds
        setTimeout(() => {
          console.log('Attempting WebSocket reconnection...');
        }, 5000);
      };
      
      setWs(websocket);
      
      // Cleanup on unmount
      return () => {
        if (websocket.readyState === WebSocket.OPEN) {
          websocket.close();
        }
      };
    } catch (err) {
      console.error('WebSocket initialization error:', err);
    }
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((data) => {
    const { type, review_id, data: reviewData } = data;
    
    console.log('WebSocket message received:', { type, review_id });
    
    switch (type) {
      case 'review_completed':
      case 'review_updated':
      case 'review_processing':
      case 'review_failed':
        // Update the specific review in the list
        setReviews(prev => prev.map(review => 
          review.id === review_id 
            ? { ...review, ...formatReviewForDisplay(reviewData) }
            : review
        ));
        // Reload stats
        loadStats();
        break;
      
      case 'connection_established':
        console.log('WebSocket connection established');
        break;
      
      case 'pong':
        // Keep-alive response
        break;
      
      default:
        console.log('Unknown WebSocket message type:', type);
    }
  }, []);

  // Load reviews from API
  const loadReviews = useCallback(async (page = null) => {
    setLoading(prev => ({ ...prev, reviews: true }));
    setError(null);

    try {
      const params = {
        page: page || pagination.page,
        page_size: pagination.page_size,
        sort: sort
      };

      // Add filters if set
      if (filters.status) params.status = filters.status;
      if (filters.priority) params.priority = filters.priority;
      if (filters.searchQuery) params.search = filters.searchQuery;

      console.log('Loading reviews with params:', params);

      const response = await reviewService.getReviews(params);
      
      console.log('Reviews loaded:', response);

      // Format reviews for display
      const formattedReviews = response.data.map(formatReviewForDisplay);
      setReviews(formattedReviews);

      // Update pagination
      if (response.pagination) {
        setPagination(prev => ({
          ...prev,
          page: response.pagination.page || prev.page,
          page_size: response.pagination.page_size || prev.page_size,
          total: response.pagination.total || 0,
          total_pages: response.pagination.pages || 0
        }));
      }

    } catch (err) {
      console.error('Error loading reviews:', err);
      setError({
        message: err.message || 'Impossible de charger les révisions',
        details: err
      });
    } finally {
      setLoading(prev => ({ ...prev, reviews: false }));
    }
  }, [pagination.page, pagination.page_size, filters, sort]);

  // Load statistics
  const loadStats = useCallback(async (days = 7) => {
    setLoading(prev => ({ ...prev, stats: true }));

    try {
      console.log(`Loading stats for ${days} days`);
      
      const response = await reviewService.getReviewStats(days);
      
      console.log('Stats loaded:', response);

      if (response?.data) {
        const formattedStats = formatStatsForDisplay(response.data);
        setStats(formattedStats);
      }

    } catch (err) {
      console.error('Error loading stats:', err);
      // Don't set error for stats, just use defaults
      setStats(reviewService.getDefaultStats(days));
    } finally {
      setLoading(prev => ({ ...prev, stats: false }));
    }
  }, []);

  // Load review by ID
  const loadReviewById = useCallback(async (reviewId) => {
    setLoading(prev => ({ ...prev, detail: true }));
    setError(null);

    try {
      console.log('Loading review:', reviewId);
      
      const response = await reviewService.getReviewById(reviewId);
      
      console.log('Review loaded:', response);

      if (response?.data) {
        return formatReviewForDisplay(response.data);
      }
      
      throw new Error('No review data received');

    } catch (err) {
      console.error('Error loading review:', err);
      setError({
        message: err.message || 'Impossible de charger la révision',
        details: err
      });
      throw err;
    } finally {
      setLoading(prev => ({ ...prev, detail: false }));
    }
  }, []);

  // Refresh all data
  const refreshReviews = useCallback(async () => {
    console.log('Refreshing reviews and stats');
    await Promise.all([
      loadReviews(),
      loadStats()
    ]);
  }, [loadReviews, loadStats]);

  // Update filters
  const updateFilters = useCallback((newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
    // Reset to first page when filters change
    setPagination(prev => ({ ...prev, page: 1 }));
  }, []);

  // Update sort
  const updateSort = useCallback((newSort) => {
    setSort(newSort);
    // Reset to first page when sort changes
    setPagination(prev => ({ ...prev, page: 1 }));
  }, []);

  // Update pagination
  const updatePagination = useCallback((newPagination) => {
    setPagination(prev => ({ ...prev, ...newPagination }));
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Delete review
  const deleteReview = useCallback(async (reviewId) => {
    try {
      await reviewService.deleteReview(reviewId);
      
      // Remove from local state
      setReviews(prev => prev.filter(r => r.id !== reviewId));
      
      // Reload stats
      await loadStats();
      
      return { success: true };
    } catch (err) {
      console.error('Error deleting review:', err);
      throw err;
    }
  }, [loadStats]);

  // Cancel upload/review
  const cancelUpload = useCallback(async (uploadId) => {
    try {
      const response = await reviewService.cancelUpload(uploadId);
      
      // Update local state
      setReviews(prev => prev.map(r => 
        r.upload_id === uploadId 
          ? { ...r, status: 'cancelled' }
          : r
      ));
      
      // Reload stats
      await loadStats();
      
      return response;
    } catch (err) {
      console.error('Error canceling upload:', err);
      throw err;
    }
  }, [loadStats]);

  // Get upload status
  const getUploadStatus = useCallback(async (uploadId) => {
    try {
      return await reviewService.getUploadStatus(uploadId);
    } catch (err) {
      console.error('Error getting upload status:', err);
      throw err;
    }
  }, []);

  // Subscribe to review updates via WebSocket
  const subscribeToReview = useCallback((reviewId) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'subscribe',
        review_id: reviewId
      }));
      console.log('Subscribed to review:', reviewId);
    }
  }, [ws]);

  // Unsubscribe from review updates
  const unsubscribeFromReview = useCallback((reviewId) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'unsubscribe',
        review_id: reviewId
      }));
      console.log('Unsubscribed from review:', reviewId);
    }
  }, [ws]);

  // Initial load
  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // Context value
  const value = {
    // State
    reviews,
    stats,
    loading,
    error,
    filters,
    sort,
    pagination,
    ws,

    // Actions
    loadReviews,
    loadStats,
    loadReviewById,
    refreshReviews,
    deleteReview,
    cancelUpload,
    getUploadStatus,
    
    // Filters and sorting
    setFilters: updateFilters,
    setSort: updateSort,
    setPagination: updatePagination,
    
    // Error handling
    clearError,
    
    // WebSocket
    subscribeToReview,
    unsubscribeFromReview
  };

  return (
    <ReviewContext.Provider value={value}>
      {children}
    </ReviewContext.Provider>
  );
};

export default ReviewContext;