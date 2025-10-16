// pages/ReviewDetail.jsx - COMPLETE FIXED VERSION
import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XCircleIcon,
  ClockIcon,
  DocumentTextIcon,
  BugAntIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ShareIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

import reviewService from '../services/reviewService';

const ReviewDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  // State management
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [expandedIssues, setExpandedIssues] = useState({});

  // Fetch review data from API
  useEffect(() => {
    const loadReview = async () => {
      if (!id) {
        setError('ID de révision manquant');
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        console.log('Loading review with ID:', id);
        const response = await reviewService.getReviewById(id);
        console.log('Review loaded:', response);
        
        if (response && response.data) {
          // Parse suggestions if they're a JSON string
          const reviewData = response.data;
          if (typeof reviewData.suggestions === 'string') {
            try {
              reviewData.suggestionsData = JSON.parse(reviewData.suggestions);
            } catch (e) {
              console.error('Error parsing suggestions:', e);
              reviewData.suggestionsData = [];
            }
          } else if (Array.isArray(reviewData.suggestions)) {
            reviewData.suggestionsData = reviewData.suggestions;
          } else {
            reviewData.suggestionsData = [];
          }
          
          setReview(reviewData);
        } else {
          throw new Error('Aucune donnée reçue');
        }
      } catch (err) {
        console.error('Failed to load review:', err);
        setError(err.message || 'Impossible de charger la révision');
      } finally {
        setLoading(false);
      }
    };

    loadReview();
  }, [id]);

  // Toggle issue expansion
  const toggleIssueExpansion = (issueId) => {
    setExpandedIssues(prev => ({
      ...prev,
      [issueId]: !prev[issueId]
    }));
  };

  // Get issue icon based on severity
  const getIssueIcon = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return <XCircleIcon className="h-5 w-5 text-red-500" />;
      case 'high':
        return <ExclamationTriangleIcon className="h-5 w-5 text-orange-500" />;
      case 'medium':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />;
      case 'low':
        return <InformationCircleIcon className="h-5 w-5 text-blue-500" />;
      default:
        return <BugAntIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  // Get issue color based on severity
  const getIssueColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
      case 'high':
        return 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800';
      case 'medium':
        return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800';
      case 'low':
        return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
      default:
        return 'bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800';
    }
  };

  // Get severity badge color
  const getSeverityBadgeColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300';
      case 'high':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-300';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300';
      case 'low':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-300';
    }
  };

  // Get status icon
  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return <CheckCircleIcon className="h-6 w-6 text-green-500" />;
      case 'processing':
      case 'in_progress':
        return <ClockIcon className="h-6 w-6 text-blue-500 animate-spin" />;
      case 'pending':
      case 'uploaded':
        return <ExclamationTriangleIcon className="h-6 w-6 text-yellow-500" />;
      case 'failed':
        return <XCircleIcon className="h-6 w-6 text-red-500" />;
      default:
        return <DocumentTextIcon className="h-6 w-6 text-gray-500" />;
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString('fr-FR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'N/A';
    }
  };

  // Calculate summary statistics
  const getSummary = () => {
    if (!review || !review.suggestionsData) {
      return {
        totalIssues: 0,
        criticalIssues: 0,
        highIssues: 0,
        mediumIssues: 0,
        lowIssues: 0
      };
    }

    const suggestions = review.suggestionsData || [];
    return {
      totalIssues: suggestions.length,
      criticalIssues: suggestions.filter(s => s.severity?.toLowerCase() === 'critical').length,
      highIssues: suggestions.filter(s => s.severity?.toLowerCase() === 'high').length,
      mediumIssues: suggestions.filter(s => s.severity?.toLowerCase() === 'medium').length,
      lowIssues: suggestions.filter(s => s.severity?.toLowerCase() === 'low').length
    };
  };

  // Copy to clipboard
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      alert('Copié dans le presse-papier !');
    });
  };

  // Get score color
  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400';
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400';
    if (score >= 40) return 'text-orange-600 dark:text-orange-400';
    return 'text-red-600 dark:text-red-400';
  };

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg animate-pulse">
          <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
        </div>
        {[1, 2, 3].map(i => (
          <div key={i} className="bg-white dark:bg-gray-800 shadow rounded-lg animate-pulse">
            <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
          </div>
        ))}
      </div>
    );
  }

  // Error state
  if (error || !review) {
    return (
      <div className="text-center py-12">
        <XCircleIcon className="mx-auto h-12 w-12 text-red-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
          {error || 'Révision non trouvée'}
        </h3>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          La révision demandée n'existe pas ou une erreur s'est produite.
        </p>
        <div className="mt-6 space-x-3">
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            <ArrowPathIcon className="mr-2 h-4 w-4" />
            Réessayer
          </button>
          <Link
            to="/reviews"
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            Retour aux révisions
          </Link>
        </div>
      </div>
    );
  }

  const summary = getSummary();
  const suggestions = review.suggestionsData || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="px-4 py-5 sm:px-6">
          <div className="flex items-center justify-between mb-4">
            <Link
              to="/reviews"
              className="inline-flex items-center text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
            >
              <ArrowLeftIcon className="mr-2 h-4 w-4" />
              Retour aux révisions
            </Link>
            <div className="flex items-center space-x-3">
              <button 
                onClick={() => copyToClipboard(window.location.href)}
                className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
              >
                <ShareIcon className="mr-2 h-4 w-4" />
                Partager
              </button>
            </div>
          </div>
          
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              {getStatusIcon(review.status)}
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Révision #{review.id || review.review_id}
                </h1>
                <div className="mt-1 flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                  {review.filename && (
                    <span className="flex items-center">
                      <DocumentTextIcon className="h-4 w-4 mr-1" />
                      {review.filename}
                    </span>
                  )}
                  {review.language && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300">
                      {review.language}
                    </span>
                  )}
                </div>
              </div>
            </div>
            
            {/* Score Badge */}
            {(review.overall_score !== null && review.overall_score !== undefined) && (
              <div className="text-right">
                <div className="text-sm text-gray-500 dark:text-gray-400">Score global</div>
                <div className={`text-3xl font-bold ${getScoreColor(review.overall_score)}`}>
                  {review.overall_score}/100
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Navigation tabs */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="-mb-px flex px-4 overflow-x-auto">
            {[
              { id: 'overview', name: 'Vue d\'ensemble', count: null },
              { id: 'issues', name: 'Problèmes', count: summary.totalIssues },
              { id: 'details', name: 'Détails', count: null }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-3 px-6 border-b-2 font-medium text-sm whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'
                }`}
              >
                {tab.name}
                {tab.count !== null && tab.count > 0 && (
                  <span className="ml-2 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 py-0.5 px-2 rounded-full text-xs">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Summary Card */}
            <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Résumé de la révision
                </h3>
                
                {summary.totalIssues > 0 ? (
                  <div className="grid grid-cols-2 gap-4">
                    {summary.criticalIssues > 0 && (
                      <div className="flex items-center space-x-3">
                        <XCircleIcon className="h-6 w-6 text-red-500" />
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">
                            {summary.criticalIssues}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            Critiques
                          </p>
                        </div>
                      </div>
                    )}
                    
                    {summary.highIssues > 0 && (
                      <div className="flex items-center space-x-3">
                        <ExclamationTriangleIcon className="h-6 w-6 text-orange-500" />
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">
                            {summary.highIssues}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            Importants
                          </p>
                        </div>
                      </div>
                    )}
                    
                    {summary.mediumIssues > 0 && (
                      <div className="flex items-center space-x-3">
                        <ExclamationTriangleIcon className="h-6 w-6 text-yellow-500" />
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">
                            {summary.mediumIssues}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            Moyens
                          </p>
                        </div>
                      </div>
                    )}
                    
                    {summary.lowIssues > 0 && (
                      <div className="flex items-center space-x-3">
                        <InformationCircleIcon className="h-6 w-6 text-blue-500" />
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">
                            {summary.lowIssues}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            Mineurs
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <CheckCircleIcon className="mx-auto h-12 w-12 text-green-500" />
                    <p className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
                      Excellent travail !
                    </p>
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                      Aucun problème détecté dans ce code.
                    </p>
                  </div>
                )}

                {/* Summary text */}
                {review.summary && (
                  <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Analyse globale
                    </h4>
                    <p className="text-sm text-gray-700 dark:text-gray-300">
                      {review.summary}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
          
          {/* Info sidebar */}
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Informations
                </h3>
                <dl className="space-y-3">
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Statut
                    </dt>
                    <dd className="mt-1">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        review.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300' :
                        review.status === 'processing' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300' :
                        review.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300' :
                        'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-300'
                      }`}>
                        {review.status === 'completed' ? 'Terminé' :
                         review.status === 'processing' ? 'En cours' :
                         review.status === 'failed' ? 'Échoué' :
                         review.status}
                      </span>
                    </dd>
                  </div>
                  
                  {review.created_at && (
                    <div>
                      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                        Créée le
                      </dt>
                      <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                        {formatDate(review.created_at)}
                      </dd>
                    </div>
                  )}
                  
                  {review.completed_at && (
                    <div>
                      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                        Terminée le
                      </dt>
                      <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                        {formatDate(review.completed_at)}
                      </dd>
                    </div>
                  )}
                  
                  {review.processing_time_ms && (
                    <div>
                      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                        Durée
                      </dt>
                      <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                        {(review.processing_time_ms / 1000).toFixed(2)}s
                      </dd>
                    </div>
                  )}

                  {review.model_used && (
                    <div>
                      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                        Modèle IA
                      </dt>
                      <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                        {review.model_used}
                      </dd>
                    </div>
                  )}

                  {review.tokens_used > 0 && (
                    <div>
                      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                        Tokens utilisés
                      </dt>
                      <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                        {review.tokens_used.toLocaleString()}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Issues Tab */}
      {activeTab === 'issues' && (
        <div className="space-y-4">
          {suggestions.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-8 text-center">
              <CheckCircleIcon className="mx-auto h-12 w-12 text-green-500" />
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Aucun problème détecté dans ce code !
              </p>
            </div>
          ) : (
            suggestions.map((issue, index) => (
              <div key={index} className={`border rounded-lg ${getIssueColor(issue.severity)}`}>
                <div className="px-4 py-4">
                  <div 
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => toggleIssueExpansion(index)}
                  >
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      {getIssueIcon(issue.severity)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                            {issue.issue || issue.title || issue.suggestion_type || 'Problème détecté'}
                          </h4>
                          {issue.severity && (
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getSeverityBadgeColor(issue.severity)}`}>
                              {issue.severity}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                          {issue.file_path || issue.file || review.filename}
                          {issue.line_number && ` • Ligne ${issue.line_number}`}
                        </p>
                      </div>
                    </div>
                    {expandedIssues[index] ? (
                      <ChevronDownIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
                    ) : (
                      <ChevronRightIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
                    )}
                  </div>
                  
                  {expandedIssues[index] && (
                    <div className="mt-4 space-y-4">
                      <div>
                        <h5 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                          Description
                        </h5>
                        <p className="text-sm text-gray-700 dark:text-gray-300">
                          {issue.description || issue.suggestion || 'Aucune description disponible'}
                        </p>
                      </div>
                      
                      {issue.suggested_fix && (
                        <div>
                          <h5 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                            Correction suggérée
                          </h5>
                          <pre className="bg-gray-900 text-gray-100 p-3 rounded text-xs overflow-x-auto">
                            <code>{issue.suggested_fix}</code>
                          </pre>
                        </div>
                      )}

                      {issue.code_snippet && (
                        <div>
                          <h5 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                            Code concerné
                          </h5>
                          <pre className="bg-gray-900 text-gray-100 p-3 rounded text-xs overflow-x-auto">
                            <code>{issue.code_snippet}</code>
                          </pre>
                        </div>
                      )}

                      {issue.confidence_score !== undefined && issue.confidence_score !== null && (
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          Confiance: {Math.round(issue.confidence_score * 100)}%
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Details Tab */}
      {activeTab === 'details' && (
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Détails complets (JSON)
            </h3>
            <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg text-xs overflow-x-auto">
              <code>{JSON.stringify(review, null, 2)}</code>
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReviewDetail;