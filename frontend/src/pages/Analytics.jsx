import React, { useState, useEffect } from 'react';
import { useQuery } from 'react-query';
import { 
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { 
  TrendingUp, TrendingDown, AlertCircle, Clock, 
  Code, Zap, Shield, Activity 
} from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8003';

const Analytics = () => {
  const [timeRange, setTimeRange] = useState(30);
  const [performanceHours, setPerformanceHours] = useState(24);

  // Fetch issue analytics
  const { data: issueData, isLoading: issueLoading } = useQuery(
    ['issues', timeRange],
    async () => {
      const response = await fetch(`${API_BASE_URL}/api/analytics/issues?days=${timeRange}`);
      if (!response.ok) throw new Error('Failed to fetch issue analytics');
      return response.json();
    },
    { refetchInterval: 60000 }
  );

  // Fetch performance analytics
  const { data: performanceData, isLoading: performanceLoading } = useQuery(
    ['performance', performanceHours],
    async () => {
      const response = await fetch(`${API_BASE_URL}/api/analytics/performance?hours=${performanceHours}`);
      if (!response.ok) throw new Error('Failed to fetch performance analytics');
      return response.json();
    },
    { refetchInterval: 60000 }
  );

  // Fetch quality analytics
  const { data: qualityData, isLoading: qualityLoading } = useQuery(
    ['quality', timeRange],
    async () => {
      const response = await fetch(`${API_BASE_URL}/api/analytics/quality?days=${timeRange}`);
      if (!response.ok) throw new Error('Failed to fetch quality analytics');
      return response.json();
    },
    { refetchInterval: 60000 }
  );

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

  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };

  const formatIssueTypeData = () => {
    if (!issueData?.issue_types) return [];
    const grouped = {};
    issueData.issue_types.forEach(item => {
      if (!grouped[item.type]) {
        grouped[item.type] = { type: item.type, total: 0 };
      }
      grouped[item.type][item.severity] = item.count;
      grouped[item.type].total += item.count;
    });
    return Object.values(grouped).sort((a, b) => b.total - a.total);
  };

  const formatSeverityTrendData = () => {
    if (!issueData?.severity_trends) return [];
    const grouped = {};
    issueData.severity_trends.forEach(item => {
      if (!grouped[item.date]) {
        grouped[item.date] = { date: item.date };
      }
      grouped[item.date][item.severity] = item.count;
    });
    return Object.values(grouped).sort((a, b) => 
      new Date(b.date) - new Date(a.date)
    ).slice(0, 14).reverse();
  };

  const StatCard = ({ title, value, icon: Icon, trend, color = 'blue' }) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
          <p className={`text-3xl font-bold mt-2 text-${color}-600`}>{value}</p>
          {trend && (
            <div className="flex items-center mt-2 text-sm">
              {trend > 0 ? (
                <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-500 mr-1" />
              )}
              <span className={trend > 0 ? 'text-green-500' : 'text-red-500'}>
                {Math.abs(trend)}%
              </span>
            </div>
          )}
        </div>
        <div className={`p-3 bg-${color}-100 dark:bg-${color}-900/20 rounded-lg`}>
          <Icon className={`w-6 h-6 text-${color}-600`} />
        </div>
      </div>
    </div>
  );

  if (issueLoading || performanceLoading || qualityLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Analyses & Statistiques
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Métriques détaillées de révision de code
          </p>
        </div>
        <div className="flex gap-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800"
          >
            <option value={7}>7 jours</option>
            <option value={30}>30 jours</option>
            <option value={60}>60 jours</option>
            <option value={90}>90 jours</option>
          </select>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Issues Totaux"
          value={issueData?.issue_types?.reduce((sum, i) => sum + i.count, 0) || 0}
          icon={AlertCircle}
          color="red"
        />
        <StatCard
          title="Score Moyen"
          value={qualityData?.quality_distribution?.[0]?.avg_score?.toFixed(1) || 'N/A'}
          icon={TrendingUp}
          color="green"
        />
        <StatCard
          title="Temps Moyen"
          value={`${(performanceData?.hourly_performance?.[0]?.avg_time_ms / 1000)?.toFixed(1) || 0}s`}
          icon={Clock}
          color="blue"
        />
        <StatCard
          title="Tokens Utilisés"
          value={performanceData?.token_usage?.[0]?.total_tokens || 0}
          icon={Zap}
          color="purple"
        />
      </div>

      {/* Issue Types Distribution */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">
          Distribution des Types d'Issues
        </h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={formatIssueTypeData()}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="type" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="critical" stackId="a" fill={COLORS.critical} name="Critique" />
            <Bar dataKey="high" stackId="a" fill={COLORS.high} name="Élevée" />
            <Bar dataKey="medium" stackId="a" fill={COLORS.medium} name="Moyenne" />
            <Bar dataKey="low" stackId="a" fill={COLORS.low} name="Faible" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Severity Trends */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">
          Tendances de Sévérité
        </h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={formatSeverityTrendData()}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="critical" stroke={COLORS.critical} name="Critique" />
            <Line type="monotone" dataKey="high" stroke={COLORS.high} name="Élevée" />
            <Line type="monotone" dataKey="medium" stroke={COLORS.medium} name="Moyenne" />
            <Line type="monotone" dataKey="low" stroke={COLORS.low} name="Faible" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Common Issues */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">
          Issues les Plus Fréquents
        </h2>
        <div className="space-y-3">
          {issueData?.common_issues?.slice(0, 10).map((issue, idx) => (
            <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="flex-1">
                <p className="font-medium text-gray-900 dark:text-white">{issue.title}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`px-2 py-1 text-xs rounded ${
                    issue.severity === 'critical' ? 'bg-red-100 text-red-800' :
                    issue.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                    issue.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {issue.severity}
                  </span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">{issue.type}</span>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{issue.frequency}</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">occurrences</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quality Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">
            Distribution Qualité
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={qualityData?.quality_distribution || []}
                dataKey="count"
                nameKey="tier"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label
              >
                {qualityData?.quality_distribution?.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[entry.tier]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">
            Qualité par Langage
          </h2>
          <div className="space-y-3">
            {qualityData?.language_quality?.map((lang, idx) => (
              <div key={idx} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Code className="w-5 h-5 text-gray-600" />
                  <span className="font-medium text-gray-900 dark:text-white">{lang.language}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {lang.review_count} révisions
                  </span>
                  <span className="font-bold text-green-600">{lang.avg_score.toFixed(1)}</span>
                  <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full"
                      style={{ width: `${lang.good_rate}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            Performance Horaire
          </h2>
          <select
            value={performanceHours}
            onChange={(e) => setPerformanceHours(Number(e.target.value))}
            className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
          >
            <option value={24}>24h</option>
            <option value={72}>72h</option>
            <option value={168}>7 jours</option>
          </select>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={performanceData?.hourly_performance?.slice(0, 24).reverse() || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="hour" 
              tickFormatter={(value) => new Date(value).toLocaleTimeString('fr-FR', { hour: '2-digit' })}
            />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="avg_time_ms" stroke="#3b82f6" name="Temps moyen (ms)" />
            <Line type="monotone" dataKey="p95_time_ms" stroke="#f97316" name="P95 (ms)" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default Analytics;