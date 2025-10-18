/**
 * Metrics Context Provider
 * Manages global metrics state and provides hooks for components
 * Location: frontend/src/contexts/MetricsContext.jsx
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import metricsService from '../services/metricsService';

const MetricsContext = createContext(null);

export const MetricsProvider = ({ children }) => {
  const [isServiceHealthy, setIsServiceHealthy] = useState(true);
  const [lastHealthCheck, setLastHealthCheck] = useState(null);

  // Check service health
  const checkHealth = useCallback(async () => {
    try {
      const healthy = await metricsService.checkServiceHealth();
      setIsServiceHealthy(healthy);
      setLastHealthCheck(new Date().toISOString());
      return healthy;
    } catch (error) {
      console.error('Health check failed:', error);
      setIsServiceHealthy(false);
      setLastHealthCheck(new Date().toISOString());
      return false;
    }
  }, []);

  const value = {
    isServiceHealthy,
    lastHealthCheck,
    checkHealth,
    metricsService,
  };

  return (
    <MetricsContext.Provider value={value}>
      {children}
    </MetricsContext.Provider>
  );
};

// Custom hook to use metrics context
export const useMetricsContext = () => {
  const context = useContext(MetricsContext);
  if (!context) {
    throw new Error('useMetricsContext must be used within MetricsProvider');
  }
  return context;
};

export default MetricsContext;