// pages/Home.jsx - COMPLETE VERSION WITH REAL API
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowUpTrayIcon,
  DocumentTextIcon,
  ChartBarIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  PlusIcon,
  ArrowRightIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

import reviewService from '../services/reviewService';

const Home = () => {
  const [stats, setStats] = useState({
    total_reviews: 0,
    pending_reviews: 0,
    processing_reviews: 0,
    completed_reviews: 0,
    failed_reviews: 0,
    average_score: null,
    total_suggestions: 0
  });
  
  const [recentReviews, setRecentReviews] = useState([]);
  const [loading, setLoading] = useState({ stats: true, reviews: true });
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [user] = useState({ name: 'Utilisateur' });

  // Load data on mount
  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading({ stats: true, reviews: true });
    setError(null);

    try {
      // Load statistics and recent reviews in parallel
      const [statsResponse, reviewsResponse] = await Promise.all([
        reviewService.getReviewStats(7).catch(err => {
          console.warn('Stats API error:', err);
          return { data: reviewService.getDefaultStats(7) };
        }),
        reviewService.getReviews({ page: 1, page_size: 5, sort: 'created_desc' }).catch(err => {
          console.warn('Reviews API error:', err);
          return { data: [], pagination: { total: 0 } };
        })
      ]);

      console.log('Dashboard data loaded:', { statsResponse, reviewsResponse });

      // Update stats
      if (statsResponse?.data) {
        setStats(statsResponse.data);
      }

      // Update recent reviews
      if (reviewsResponse?.data) {
        setRecentReviews(reviewsResponse.data.slice(0, 5));
      }

    } catch (err) {
      console.error('Error loading dashboard:', err);
      setError('Impossible de charger les données du tableau de bord');
    } finally {
      setLoading({ stats: false, reviews: false });
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadDashboardData();
    setTimeout(() => setRefreshing(false), 500);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Récemment';
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return 'À l\'instant';
      if (diffMins < 60) return `Il y a ${diffMins}m`;
      if (diffHours < 24) return `Il y a ${diffHours}h`;
      if (diffDays < 7) return `Il y a ${diffDays}j`;
      return date.toLocaleDateString('fr-FR');
    } catch {
      return 'Récemment';
    }
  };

  const getStatusMessage = () => {
    const activeCount = stats.processing_reviews || 0;
    const pendingCount = stats.pending_reviews || 0;

    if (activeCount > 0) {
      return {
        type: 'info',
        message: `${activeCount} révision${activeCount > 1 ? 's' : ''} en cours`,
        icon: ClockIcon
      };
    }
    
    if (pendingCount > 0) {
      return {
        type: 'warning',
        message: `${pendingCount} révision${pendingCount > 1 ? 's' : ''} en attente`,
        icon: ExclamationTriangleIcon
      };
    }

    return {
      type: 'success',
      message: 'Toutes les révisions sont à jour',
      icon: CheckCircleIcon
    };
  };

  const quickActions = [
    {
      name: 'Nouveau Upload',
      description: 'Télécharger des fichiers pour révision',
      href: '/upload',
      icon: ArrowUpTrayIcon,
      color: 'bg-blue-500 hover:bg-blue-600',
      primary: true
    },
    {
      name: 'Voir les Révisions',
      description: 'Consulter toutes les révisions',
      href: '/reviews',
      icon: DocumentTextIcon,
      color: 'bg-green-500 hover:bg-green-600'
    },
    {
      name: 'Analytics',
      description: 'Analyser les métriques',
      href: '/analytics',
      icon: ChartBarIcon,
      color: 'bg-purple-500 hover:bg-purple-600'
    },
    {
      name: 'Historique',
      description: 'Voir l\'historique complet',
      href: '/history',
      icon: ClockIcon,
      color: 'bg-orange-500 hover:bg-orange-600'
    }
  ];

  const statusMessage = getStatusMessage();
  const StatusIcon = statusMessage.icon;

  // Loading state
  if (loading.stats && loading.reviews && !error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Chargement du tableau de bord...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-400 mr-3" />
            <div className="flex-1">
              <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
            </div>
            <button
              onClick={handleRefresh}
              className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200"
            >
              <ArrowPathIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Bonjour{user?.name ? `, ${user.name}` : ''} ! 👋
              </h1>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Bienvenue dans votre assistant de révision de code IA
              </p>
            </div>
            
            <div className="flex items-center space-x-3">
              {/* Status Badge */}
              <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                statusMessage.type === 'success' 
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300'
                  : statusMessage.type === 'warning'
                  ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300'
                  : 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300'
              }`}>
                <StatusIcon className="w-4 h-4 mr-2" />
                {statusMessage.message}
              </div>
              
              {/* Refresh Button */}
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                <ArrowPathIcon className={`-ml-0.5 mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                {refreshing ? 'Actualisation...' : 'Actualiser'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Actions rapides
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {quickActions.map((action) => {
              const IconComponent = action.icon;
              return (
                <Link
                  key={action.name}
                  to={action.href}
                  className={`relative group bg-white dark:bg-gray-700 p-6 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 transition-all duration-200 hover:shadow-md ${
                    action.primary ? 'ring-1 ring-blue-500 bg-blue-50 dark:bg-blue-900/20' : ''
                  }`}
                >
                  <div>
                    <span className={`rounded-lg inline-flex p-3 ${action.color} text-white`}>
                      <IconComponent className="h-6 w-6" />
                    </span>
                  </div>
                  <div className="mt-4">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                      {action.name}
                    </h3>
                    <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                      {action.description}
                    </p>
                  </div>
                  <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    <ArrowRightIcon className="h-5 w-5 text-gray-400" />
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <DocumentTextIcon className="h-8 w-8 text-blue-500" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Total Révisions
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {loading.stats ? '...' : (stats.total_reviews || 0)}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ClockIcon className="h-8 w-8 text-yellow-500" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    En Attente
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {loading.stats ? '...' : (stats.pending_reviews || 0)}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ArrowRightIcon className="h-8 w-8 text-green-500" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    En Cours
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {loading.stats ? '...' : (stats.processing_reviews || 0)}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <CheckCircleIcon className="h-8 w-8 text-purple-500" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Terminées
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {loading.stats ? '...' : (stats.completed_reviews || 0)}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Activity */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
                Activité Récente
              </h3>
              <Link 
                to="/reviews"
                className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
              >
                Voir tout
              </Link>
            </div>
            
            {loading.reviews ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                  </div>
                ))}
              </div>
            ) : recentReviews && recentReviews.length > 0 ? (
              <div className="space-y-3">
                {recentReviews.map((review, index) => (
                  <Link
                    key={review.id || index}
                    to={`/reviews/${review.id}`}
                    className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700 last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700 -mx-2 px-2 rounded transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {review.title || review.filename || `Révision ${index + 1}`}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {review.status === 'completed' ? 'Terminé' :
                         review.status === 'processing' ? 'En cours' :
                         review.status === 'pending' ? 'En attente' :
                         review.status || 'Inconnu'}
                      </p>
                    </div>
                    <div className="text-xs text-gray-400 ml-4">
                      {formatDate(review.created_at || review.createdAt)}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                Aucune activité récente
              </p>
            )}
          </div>
        </div>
        
        {/* Info Cards */}
        <div className="space-y-6">
          {/* Pending Reviews Alert */}
          {stats.pending_reviews > 0 && (
            <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
              <div className="p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <ExclamationTriangleIcon className="h-8 w-8 text-yellow-500" />
                  </div>
                  <div className="ml-4 flex-1">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                      Révisions en attente
                    </h3>
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                      {stats.pending_reviews} révision{stats.pending_reviews > 1 ? 's' : ''} 
                      {' '}attend{stats.pending_reviews > 1 ? 'ent' : ''} d'être traitée{stats.pending_reviews > 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Average Score */}
          {stats.average_score !== null && stats.average_score !== undefined && (
            <div className="bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 overflow-hidden shadow rounded-lg border border-green-200 dark:border-green-800">
              <div className="p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="h-12 w-12 bg-green-500 rounded-lg flex items-center justify-center">
                      <span className="text-white text-xl font-bold">
                        {Math.round(stats.average_score)}
                      </span>
                    </div>
                  </div>
                  <div className="ml-4">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                      Score Moyen
                    </h3>
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                      Basé sur {stats.completed_reviews} révision{stats.completed_reviews > 1 ? 's' : ''} terminée{stats.completed_reviews > 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Tips */}
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 overflow-hidden shadow rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="h-8 w-8 bg-blue-500 rounded-lg flex items-center justify-center">
                    <span className="text-white text-sm font-bold">💡</span>
                  </div>
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    Conseil du jour
                  </h3>
                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    Utilisez des noms de fichiers descriptifs pour obtenir de meilleures suggestions de révision.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Getting Started Section */}
      {stats.total_reviews === 0 && (
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="px-6 py-8">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Première fois ici ?
              </h2>
              <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
                Découvrez comment utiliser l'assistant de révision de code IA
              </p>
              <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="text-center">
                  <div className="mx-auto h-12 w-12 bg-blue-100 dark:bg-blue-900/50 rounded-lg flex items-center justify-center">
                    <ArrowUpTrayIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
                    1. Téléchargez
                  </h3>
                  <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                    Glissez-déposez vos fichiers de code ou sélectionnez-les
                  </p>
                </div>
                
                <div className="text-center">
                  <div className="mx-auto h-12 w-12 bg-blue-100 dark:bg-blue-900/50 rounded-lg flex items-center justify-center">
                    <span className="text-xl">🤖</span>
                  </div>
                  <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
                    2. L'IA analyse
                  </h3>
                  <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                    Notre IA examine votre code et génère des suggestions
                  </p>
                </div>
                
                <div className="text-center">
                  <div className="mx-auto h-12 w-12 bg-blue-100 dark:bg-blue-900/50 rounded-lg flex items-center justify-center">
                    <CheckCircleIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
                    3. Améliorez
                  </h3>
                  <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                    Consultez les suggestions et améliorez votre code
                  </p>
                </div>
              </div>
              
              <div className="mt-8">
                <Link
                  to="/upload"
                  className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
                >
                  <PlusIcon className="mr-2 h-5 w-5" />
                  Commencer maintenant
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Home;