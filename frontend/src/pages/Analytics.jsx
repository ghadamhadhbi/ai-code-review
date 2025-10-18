import React, { useState, useEffect, useMemo, createContext, useContext, useCallback } from 'react';
import { 
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { 
  TrendingUp, AlertCircle, Clock, 
  Code, Zap, RefreshCw, AlertTriangle 
} from 'lucide-react';

// Metrics Service
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class MetricsService {
  async getDashboardStats(days = 7) {
    const response = await fetch(`${API_BASE_URL}/api/analytics/stats?days=${days}`);
    if (!response.ok) throw new Error('Failed to fetch dashboard stats');
    return response.json();
  }

  async getIssueAnalytics(days = 30) {
    const response = await fetch(`${API_BASE_URL}/api/analytics/issues?days=${days}`);
    if (!response.ok) throw new Error('Failed to fetch issue analytics');
    return response.json();
  }

  async getPerformanceAnalytics(hours = 24) {
    const response = await fetch(`${API_BASE_URL}/api/analytics/performance?hours=${hours}`);
    if (!response.ok) throw new Error('Failed to fetch performance analytics');
    return response.json();
  }

  async getQualityAnalytics(days = 30) {
    const response = await fetch(`${API_BASE_URL}/api/analytics/quality?days=${days}`);
    if (!response.ok) throw new Error('Failed to fetch quality analytics');
    return response.json();
  }

  async getAllAnalytics(params = {}) {
    const {
      statsDays = 7,
      issuesDays = 30,
      performanceHours = 24,
      qualityDays = 30,
    } = params;

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
  }
}

const metricsService = new MetricsService();

// Context
const MetricsContext = createContext(null);

const MetricsProvider = ({ children }) => {
  const [isServiceHealthy, setIsServiceHealthy] = useState(true);

  const checkHealth = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`, { timeout: 5000 });
      const data = await response.json();
      const healthy = data.components?.database === 'healthy';
      setIsServiceHealthy(healthy);
      return healthy;
    } catch (error) {
      console.error('Health check failed:', error);
      setIsServiceHealthy(false);
      return false;
    }
  }, []);

  return (
    <MetricsContext.Provider value={{ isServiceHealthy, checkHealth, metricsService }}>
      {children}
    </MetricsContext.Provider>
  );
};

const useMetricsContext = () => {
  const context = useContext(MetricsContext);
  if (!context) throw new Error('useMetricsContext must be used within MetricsProvider');
  return context;
};

// Custom Hook
const useMetrics = (params = {}) => {
  const {
    statsDays = 7,
    issuesDays = 30,
    performanceHours = 24,
    qualityDays = 30,
    autoRefresh = true,
    refreshInterval = 60000,
  } = params;

  const { metricsService, isServiceHealthy } = useMetricsContext();

  const [data, setData] = useState({
    stats: null,
    issues: null,
    performance: null,
    quality: null,
  });

  const [loading, setLoading] = useState({
    stats: true,
    issues: true,
    performance: true,
    quality: true,
  });

  const [errors, setErrors] = useState({
    stats: null,
    issues: null,
    performance: null,
    quality: null,
  });

  const [isInitialLoad, setIsInitialLoad] = useState(true);

  const fetchAllAnalytics = useCallback(async () => {
    if (!isServiceHealthy) {
      console.warn('Metrics service is not healthy, skipping fetch');
      return;
    }

    try {
      const result = await metricsService.getAllAnalytics({
        statsDays,
        issuesDays,
        performanceHours,
        qualityDays,
      });

      setData({
        stats: result.stats,
        issues: result.issues,
        performance: result.performance,
        quality: result.quality,
      });

      setErrors(result.errors);

      setLoading({
        stats: false,
        issues: false,
        performance: false,
        quality: false,
      });

      setIsInitialLoad(false);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      setErrors({
        stats: error.message,
        issues: error.message,
        performance: error.message,
        quality: error.message,
      });
      setLoading({
        stats: false,
        issues: false,
        performance: false,
        quality: false,
      });
      setIsInitialLoad(false);
    }
  }, [metricsService, isServiceHealthy, statsDays, issuesDays, performanceHours, qualityDays]);

  const fetchIssues = useCallback(async (days = issuesDays) => {
    setLoading(prev => ({ ...prev, issues: true }));
    try {
      const issues = await metricsService.getIssueAnalytics(days);
      setData(prev => ({ ...prev, issues }));
      setErrors(prev => ({ ...prev, issues: null }));
    } catch (error) {
      setErrors(prev => ({ ...prev, issues: error.message }));
    } finally {
      setLoading(prev => ({ ...prev, issues: false }));
    }
  }, [metricsService, issuesDays]);

  const fetchPerformance = useCallback(async (hours = performanceHours) => {
    setLoading(prev => ({ ...prev, performance: true }));
    try {
      const performance = await metricsService.getPerformanceAnalytics(hours);
      setData(prev => ({ ...prev, performance }));
      setErrors(prev => ({ ...prev, performance: null }));
    } catch (error) {
      setErrors(prev => ({ ...prev, performance: error.message }));
    } finally {
      setLoading(prev => ({ ...prev, performance: false }));
    }
  }, [metricsService, performanceHours]);

  const fetchQuality = useCallback(async (days = qualityDays) => {
    setLoading(prev => ({ ...prev, quality: true }));
    try {
      const quality = await metricsService.getQualityAnalytics(days);
      setData(prev => ({ ...prev, quality }));
      setErrors(prev => ({ ...prev, quality: null }));
    } catch (error) {
      setErrors(prev => ({ ...prev, quality: error.message }));
    } finally {
      setLoading(prev => ({ ...prev, quality: false }));
    }
  }, [metricsService, qualityDays]);

  useEffect(() => {
    fetchAllAnalytics();
  }, [fetchAllAnalytics]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchAllAnalytics, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchAllAnalytics]);

  const isLoading = Object.values(loading).some(v => v);
  const hasErrors = Object.values(errors).some(v => v !== null);

  return {
    data,
    loading,
    errors,
    isLoading,
    hasErrors,
    isInitialLoad,
    refresh: fetchAllAnalytics,
    fetchIssues,
    fetchPerformance,
    fetchQuality,
    isServiceHealthy,
  };
};

// Analytics Component
const AnalyticsContent = () => {
  const [timeRange, setTimeRange] = useState(30);
  const [performanceHours, setPerformanceHours] = useState(24);

  const {
    data,
    loading,
    errors,
    isLoading,
    hasErrors,
    isInitialLoad,
    refresh,
    fetchIssues,
    fetchPerformance,
    fetchQuality,
  } = useMetrics({
    statsDays: 7,
    issuesDays: timeRange,
    performanceHours,
    qualityDays: timeRange,
    autoRefresh: true,
    refreshInterval: 60000,
  });

  const { stats, issues, performance, quality } = data;

  useEffect(() => {
    if (!isInitialLoad) {
      fetchIssues(timeRange);
      fetchQuality(timeRange);
    }
  }, [timeRange, fetchIssues, fetchQuality, isInitialLoad]);

  useEffect(() => {
    if (!isInitialLoad) {
      fetchPerformance(performanceHours);
    }
  }, [performanceHours, fetchPerformance, isInitialLoad]);

  const COLORS = {
    critical: '#ef4444',
    high: '#f97316',
    medium: '#f59e0b',
    low: '#3b82f6',
    excellent: '#22c55e',
    good: '#84cc16',
    fair: '#eab308',
    poor: '#f97316',
    very_poor: '#ef4444'
  };

  const issueTypeData = useMemo(() => {
    if (!issues?.issue_types) return [];
    const grouped = {};
    issues.issue_types.forEach(item => {
      if (!grouped[item.type]) {
        grouped[item.type] = { type: item.type, total: 0 };
      }
      grouped[item.type][item.severity] = item.count;
      grouped[item.type].total += item.count;
    });
    return Object.values(grouped).sort((a, b) => b.total - a.total);
  }, [issues]);

  const severityTrendData = useMemo(() => {
    if (!issues?.severity_trends) return [];
    const grouped = {};
    issues.severity_trends.forEach(item => {
      if (!grouped[item.date]) {
        grouped[item.date] = { date: item.date };
      }
      grouped[item.date][item.severity] = item.count;
    });
    return Object.values(grouped)
      .sort((a, b) => new Date(b.date) - new Date(a.date))
      .slice(0, 14)
      .reverse();
  }, [issues]);

  const totalIssues = useMemo(() => {
    return issues?.issue_types?.reduce((sum, i) => sum + i.count, 0) || 0;
  }, [issues]);

  const avgScore = useMemo(() => {
    return quality?.quality_distribution?.[0]?.avg_score?.toFixed(1) || 'N/A';
  }, [quality]);

  const avgTime = useMemo(() => {
    const avgMs = performance?.hourly_performance?.[0]?.avg_time_ms;
    return avgMs ? `${(avgMs / 1000).toFixed(1)}s` : '0s';
  }, [performance]);

  const totalTokens = useMemo(() => {
    return performance?.token_usage?.[0]?.total_tokens || 0;
  }, [performance]);

  const StatCard = ({ title, value, icon: Icon, color = 'blue', isLoading = false }) => (
    <div className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600 font-medium mb-2">{title}</p>
          {isLoading ? (
            <div className="h-9 w-20 bg-gray-200 animate-pulse rounded" />
          ) : (
            <p className={`text-3xl font-bold text-${color}-600`}>{value}</p>
          )}
        </div>
        <div className={`p-4 bg-${color}-100 rounded-lg`}>
          <Icon className={`w-8 h-8 text-${color}-600`} />
        </div>
      </div>
    </div>
  );

  const ErrorDisplay = ({ message }) => (
    <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
      <div className="flex items-center">
        <AlertTriangle className="w-5 h-5 text-red-500 mr-3" />
        <div>
          <h3 className="font-semibold text-red-900">Erreur de chargement</h3>
          <p className="text-sm text-red-700">{message}</p>
        </div>
      </div>
    </div>
  );

  if (isInitialLoad) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
          <p className="text-xl text-gray-700 font-semibold">Chargement des analyses...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between bg-white rounded-lg shadow-lg p-6">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Analyses & Statistiques
            </h1>
            <p className="text-gray-600">
              Métriques détaillées de révision de code
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={refresh}
              disabled={isLoading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-semibold shadow-md hover:shadow-lg transition-all"
            >
              <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
              Actualiser
            </button>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(Number(e.target.value))}
              className="px-4 py-3 border-2 border-gray-300 rounded-lg bg-white font-semibold focus:border-blue-500 focus:outline-none"
            >
              <option value={7}>7 jours</option>
              <option value={30}>30 jours</option>
              <option value={60}>60 jours</option>
              <option value={90}>90 jours</option>
            </select>
          </div>
        </div>

        {hasErrors && (
          <div>
            {errors.issues && <ErrorDisplay message={errors.issues} />}
            {errors.performance && <ErrorDisplay message={errors.performance} />}
            {errors.quality && <ErrorDisplay message={errors.quality} />}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Issues Totaux"
            value={totalIssues}
            icon={AlertCircle}
            color="red"
            isLoading={loading.issues}
          />
          <StatCard
            title="Score Moyen"
            value={avgScore}
            icon={TrendingUp}
            color="green"
            isLoading={loading.quality}
          />
          <StatCard
            title="Temps Moyen"
            value={avgTime}
            icon={Clock}
            color="blue"
            isLoading={loading.performance}
          />
          <StatCard
            title="Tokens Utilisés"
            value={totalTokens}
            icon={Zap}
            color="purple"
            isLoading={loading.performance}
          />
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold mb-6 text-gray-900">
            Distribution des Types d'Issues
          </h2>
          {loading.issues ? (
            <div className="h-80 flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-600"></div>
            </div>
          ) : issueTypeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={issueTypeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="type" stroke="#6b7280" />
                <YAxis stroke="#6b7280" />
                <Tooltip />
                <Legend />
                <Bar dataKey="critical" stackId="a" fill={COLORS.critical} name="Critique" />
                <Bar dataKey="high" stackId="a" fill={COLORS.high} name="Élevée" />
                <Bar dataKey="medium" stackId="a" fill={COLORS.medium} name="Moyenne" />
                <Bar dataKey="low" stackId="a" fill={COLORS.low} name="Faible" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-80 flex items-center justify-center text-gray-500">
              Aucune donnée disponible
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold mb-6 text-gray-900">
            Tendances de Sévérité
          </h2>
          {loading.issues ? (
            <div className="h-80 flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-600"></div>
            </div>
          ) : severityTrendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={severityTrendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" stroke="#6b7280" />
                <YAxis stroke="#6b7280" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="critical" stroke={COLORS.critical} strokeWidth={2} name="Critique" />
                <Line type="monotone" dataKey="high" stroke={COLORS.high} strokeWidth={2} name="Élevée" />
                <Line type="monotone" dataKey="medium" stroke={COLORS.medium} strokeWidth={2} name="Moyenne" />
                <Line type="monotone" dataKey="low" stroke={COLORS.low} strokeWidth={2} name="Faible" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-80 flex items-center justify-center text-gray-500">
              Aucune donnée disponible
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold mb-6 text-gray-900">
            Issues les Plus Fréquents
          </h2>
          {loading.issues ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-20 bg-gray-200 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : issues?.common_issues?.length > 0 ? (
            <div className="space-y-3">
              {issues.common_issues.slice(0, 10).map((issue, idx) => (
                <div key={idx} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                  <div className="flex-1">
                    <p className="font-semibold text-gray-900">{issue.title}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className={`px-3 py-1 text-xs font-semibold rounded-full ${
                        issue.severity === 'critical' ? 'bg-red-100 text-red-800' :
                        issue.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                        issue.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {issue.severity}
                      </span>
                      <span className="text-sm text-gray-600">{issue.type}</span>
                    </div>
                  </div>
                  <div className="text-right ml-4">
                    <p className="text-3xl font-bold text-gray-900">{issue.frequency}</p>
                    <p className="text-sm text-gray-600">occurrences</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              Aucun issue fréquent trouvé
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-6 text-gray-900">
              Distribution Qualité
            </h2>
            {loading.quality ? (
              <div className="h-80 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-600"></div>
              </div>
            ) : quality?.quality_distribution?.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie
                    data={quality.quality_distribution}
                    dataKey="count"
                    nameKey="tier"
                    cx="50%"
                    cy="50%"
                    outerRadius={120}
                    label
                  >
                    {quality.quality_distribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[entry.tier]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-80 flex items-center justify-center text-gray-500">
                Aucune donnée disponible
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-6 text-gray-900">
              Qualité par Langage
            </h2>
            {loading.quality ? (
              <div className="space-y-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-16 bg-gray-200 rounded animate-pulse" />
                ))}
              </div>
            ) : quality?.language_quality?.length > 0 ? (
              <div className="space-y-4">
                {quality.language_quality.map((lang, idx) => (
                  <div key={idx} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <Code className="w-6 h-6 text-gray-600" />
                      <span className="font-semibold text-gray-900">{lang.language}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-gray-600">
                        {lang.review_count} révisions
                      </span>
                      <span className="font-bold text-green-600 text-lg">{lang.avg_score.toFixed(1)}</span>
                      <div className="w-24 bg-gray-200 rounded-full h-3">
                        <div
                          className="bg-green-500 h-3 rounded-full"
                          style={{ width: `${lang.good_rate}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                Aucune donnée disponible
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Performance Horaire
            </h2>
            <select
              value={performanceHours}
              onChange={(e) => setPerformanceHours(Number(e.target.value))}
              className="px-4 py-2 border-2 border-gray-300 rounded-lg bg-white font-semibold focus:border-blue-500 focus:outline-none"
            >
              <option value={24}>24h</option>
              <option value={72}>72h</option>
              <option value={168}>7 jours</option>
            </select>
          </div>
          {loading.performance ? (
            <div className="h-80 flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-600"></div>
            </div>
          ) : performance?.hourly_performance?.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={performance.hourly_performance.slice(0, 24).reverse()}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis 
                  dataKey="hour" 
                  stroke="#6b7280"
                  tickFormatter={(value) => new Date(value).toLocaleTimeString('fr-FR', { hour: '2-digit' })}
                />
                <YAxis stroke="#6b7280" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="avg_time_ms" stroke="#3b82f6" strokeWidth={2} name="Temps moyen (ms)" />
                <Line type="monotone" dataKey="p95_time_ms" stroke="#f97316" strokeWidth={2} name="P95 (ms)" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-80 flex items-center justify-center text-gray-500">
              Aucune donnée disponible
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Main Component with Provider
const Analytics = () => {
  return (
    <MetricsProvider>
      <AnalyticsContent />
    </MetricsProvider>
  );
};

export default Analytics;