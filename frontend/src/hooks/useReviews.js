
// ============================================================================
// PART 2: React Hooks for API Integration
// ============================================================================

// hooks/useReviewAPI.js
import { useState, useEffect, useCallback, useRef } from 'react';
import reviewService, { handleApiError, formatReviewForDisplay } from '../services/reviewService';

/**
 * Hook: useReviews - Fetch and manage reviews list
 */
export const useReviews = (initialFilters = {}) => {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState(initialFilters);

  const fetchReviews = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await reviewService.getReviews(filters);
      const formattedReviews = response.data.map(formatReviewForDisplay);
      setReviews(formattedReviews);
    } catch (err) {
      const errorInfo = handleApiError(err);
      setError(errorInfo.message);
      console.error('Failed to fetch reviews:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  const refetch = useCallback(() => {
    fetchReviews();
  }, [fetchReviews]);

  const updateFilters = useCallback((newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
  }, []);

  return {
    reviews,
    loading,
    error,
    refetch,
    filters,
    updateFilters
  };
};

/**
 * Hook: useReview - Fetch single review by ID
 */
export const useReview = (reviewId) => {
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchReview = useCallback(async () => {
    if (!reviewId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await reviewService.getReviewById(reviewId);
      const formattedReview = formatReviewForDisplay(response.data);
      setReview(formattedReview);
    } catch (err) {
      const errorInfo = handleApiError(err);
      setError(errorInfo.message);
      console.error('Failed to fetch review:', err);
    } finally {
      setLoading(false);
    }
  }, [reviewId]);

  useEffect(() => {
    fetchReview();
  }, [fetchReview]);

  return {
    review,
    loading,
    error,
    refetch: fetchReview
  };
};

/**
 * Hook: useUploadFiles - Handle file uploads
 */
export const useUploadFiles = () => {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);

  const uploadFiles = useCallback(async (files, metadata = {}) => {
    setUploading(true);
    setError(null);
    setUploadResult(null);

    try {
      const formData = new FormData();
      
      // Add files
      files.forEach(file => {
        formData.append('files', file);
      });

      // Add metadata
      if (metadata.author_email) {
        formData.append('author_email', metadata.author_email);
      }
      if (metadata.description) {
        formData.append('description', metadata.description);
      }
      if (metadata.language) {
        formData.append('language', metadata.language);
      }

      const result = await reviewService.uploadFiles(formData);
      setUploadResult(result);
      return result;
    } catch (err) {
      const errorInfo = handleApiError(err);
      setError(errorInfo.message);
      console.error('Failed to upload files:', err);
      throw err;
    } finally {
      setUploading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setError(null);
    setUploadResult(null);
  }, []);

  return {
    uploadFiles,
    uploading,
    error,
    uploadResult,
    reset
  };
};

/**
 * Hook: useReviewStats - Fetch review statistics
 */
export const useReviewStats = (days = 7) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await reviewService.getReviewStats(days);
      setStats(response.data);
    } catch (err) {
      // Don't show error for stats - just use default
      console.warn('Stats not available:', err);
      setStats({
        period_days: days,
        summary: {
          total_reviews: 0,
          completed_reviews: 0,
          failed_reviews: 0,
          pending_reviews: 0,
          average_score: 0,
          average_processing_time_ms: 0,
          total_tokens_used: 0
        },
        severity_distribution: [],
        issue_type_distribution: []
      });
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return {
    stats,
    loading,
    error,
    refetch: fetchStats
  };
};

/**
 * Hook: usePolling - Poll for updates
 */
export const usePolling = (callback, interval = 5000, enabled = true) => {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;

    const tick = () => {
      savedCallback.current();
    };

    // Call immediately
    tick();

    // Then set up interval
    const id = setInterval(tick, interval);
    return () => clearInterval(id);
  }, [interval, enabled]);
};