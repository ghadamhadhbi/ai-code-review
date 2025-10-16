import React, { useState, useMemo } from 'react';
import { useQuery } from 'react-query';
import { useNavigate } from 'react-router-dom';
import { 
  Search, Filter, Download, Calendar, User, 
  FileCode, TrendingUp, AlertTriangle, CheckCircle,
  XCircle, Clock, ChevronDown, ChevronUp, Eye
} from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8003';

const History = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [languageFilter, setLanguageFilter] = useState('all');
  const [sortBy, setSortBy] = useState('date_desc');
  const [expandedRow, setExpandedRow] = useState(null);

  // Fetch reviews history
  const { data: reviews, isLoading, refetch } = useQuery(
    'reviewHistory',
    async () => {
      const response = await fetch(`${API_BASE_URL}/api/reviews`);
      if (!response.ok) throw new Error('Failed to fetch reviews');
      return response.json();
    },
    { refetchInterval: 30000 }
  );

  // Filter and sort reviews
  const filteredReviews = useMemo(() => {
    if (!reviews?.reviews) return [];
    
    let filtered = reviews.reviews.filter(review => {
      const matchesSearch = !searchTerm || 
        review.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        review.author_email?.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesStatus = statusFilter === 'all' || review.status === statusFilter;
      const matchesLanguage = languageFilter === 'all' || review.language === languageFilter;
      
      return matchesSearch && matchesStatus && matchesLanguage;
    });

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'date_desc':
          return new Date(b.created_at) - new Date(a.created_at);
        case 'date_asc':
          return new Date(a.created_at) - new Date(b.created_at);
        case 'score_desc':
          return (b.overall_score || 0) - (a.overall_score || 0);
        case 'score_asc':
          return (a.overall_score || 0) - (b.overall_score || 0);
        default:
          return 0;
      }
    });

    return filtered;
  }, [reviews, searchTerm, statusFilter, languageFilter, sortBy]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'processing':
        return <Clock className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-yellow-500" />;
      default:
        return <AlertTriangle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      completed: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300',
      failed: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300',
      processing: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300',
      pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300',
      cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-300'
    };

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}>
        {status}
      </span>
    );
  };

  const getScoreColor = (score) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 80) return 'text-blue-600';
    if (score >= 70) return 'text-yellow-600';
    if (score >= 60) return 'text-orange-600';
    return 'text-red-600';
  };

  const exportToCSV = () => {
    const headers = ['Date', 'Auteur', 'Langage', 'Fichiers', 'Score', 'Statut', 'Description'];
    const rows = filteredReviews.map(review => [
      new Date(review.created_at).toLocaleString('fr-FR'),
      review.author_email || 'N/A',
      review.language || 'N/A',
      review.file_count || 0,
      review.overall_score || 'N/A',
      review.status,
      review.description || ''
    ]);

    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `review-history-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  const uniqueLanguages = useMemo(() => {
    if (!reviews?.reviews) return [];
    return [...new Set(reviews.reviews.map(r => r.language).filter(Boolean))];
  }, [reviews]);

  if (isLoading) {
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
            Historique des Révisions
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            {filteredReviews.length} révision{filteredReviews.length !== 1 ? 's' : ''} trouvée{filteredReviews.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={exportToCSV}
          disabled={filteredReviews.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Download className="w-4 h-4" />
          Exporter CSV
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Rechercher..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="all">Tous les statuts</option>
            <option value="completed">Terminé</option>
            <option value="processing">En cours</option>
            <option value="pending">En attente</option>
            <option value="failed">Échec</option>
          </select>

          {/* Language Filter */}
          <select
            value={languageFilter}
            onChange={(e) => setLanguageFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="all">Tous les langages</option>
            {uniqueLanguages.map(lang => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>

          {/* Sort */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="date_desc">Plus récent</option>
            <option value="date_asc">Plus ancien</option>
            <option value="score_desc">Score décroissant</option>
            <option value="score_asc">Score croissant</option>
          </select>
        </div>
      </div>

      {/* Reviews Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Auteur
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Langage
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Fichiers
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Statut
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {filteredReviews.map((review) => (
                <React.Fragment key={review.id}>
                  <tr className="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900 dark:text-white">
                        <Calendar className="w-4 h-4 mr-2 text-gray-400" />
                        {new Date(review.created_at).toLocaleDateString('fr-FR', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm">
                        <User className="w-4 h-4 mr-2 text-gray-400" />
                        <span className="text-gray-900 dark:text-white">
                          {review.author_email || 'Anonyme'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm">
                        <FileCode className="w-4 h-4 mr-2 text-gray-400" />
                        <span className="text-gray-900 dark:text-white">
                          {review.language || 'N/A'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {review.file_count || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {review.overall_score !== null && review.overall_score !== undefined ? (
                        <div className="flex items-center">
                          <TrendingUp className={`w-4 h-4 mr-2 ${getScoreColor(review.overall_score)}`} />
                          <span className={`text-lg font-bold ${getScoreColor(review.overall_score)}`}>
                            {review.overall_score}/100
                          </span>
                        </div>
                      ) : (
                        <span className="text-sm text-gray-500">N/A</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(review.status)}
                        {getStatusBadge(review.status)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setExpandedRow(expandedRow === review.id ? null : review.id)}
                          className="p-2 text-gray-600 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400"
                        >
                          {expandedRow === review.id ? (
                            <ChevronUp className="w-5 h-5" />
                          ) : (
                            <ChevronDown className="w-5 h-5" />
                          )}
                        </button>
                        <button
                          onClick={() => navigate(`/reviews/${review.id}`)}
                          className="p-2 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                        >
                          <Eye className="w-5 h-5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                  
                  {/* Expanded Row */}
                  {expandedRow === review.id && (
                    <tr className="bg-gray-50 dark:bg-gray-700">
                      <td colSpan="7" className="px-6 py-4">
                        <div className="space-y-4">
                          {/* Description */}
                          {review.description && (
                            <div>
                              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                Description
                              </h4>
                              <p className="text-sm text-gray-600 dark:text-gray-400">
                                {review.description}
                              </p>
                            </div>
                          )}

                          {/* Summary */}
                          {review.summary && (
                            <div>
                              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                Résumé de la Révision
                              </h4>
                              <p className="text-sm text-gray-600 dark:text-gray-400">
                                {review.summary}
                              </p>
                            </div>
                          )}

                          {/* Statistics */}
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="bg-white dark:bg-gray-800 rounded-lg p-3">
                              <p className="text-xs text-gray-600 dark:text-gray-400">Taille Totale</p>
                              <p className="text-lg font-bold text-gray-900 dark:text-white">
                                {((review.total_size_bytes || 0) / 1024).toFixed(1)} KB
                              </p>
                            </div>
                            <div className="bg-white dark:bg-gray-800 rounded-lg p-3">
                              <p className="text-xs text-gray-600 dark:text-gray-400">Modèle IA</p>
                              <p className="text-lg font-bold text-gray-900 dark:text-white">
                                {review.model_used || 'N/A'}
                              </p>
                            </div>
                            <div className="bg-white dark:bg-gray-800 rounded-lg p-3">
                              <p className="text-xs text-gray-600 dark:text-gray-400">Tokens</p>
                              <p className="text-lg font-bold text-gray-900 dark:text-white">
                                {review.tokens_used || 0}
                              </p>
                            </div>
                            <div className="bg-white dark:bg-gray-800 rounded-lg p-3">
                              <p className="text-xs text-gray-600 dark:text-gray-400">Temps de Traitement</p>
                              <p className="text-lg font-bold text-gray-900 dark:text-white">
                                {review.processing_time_ms ? `${(review.processing_time_ms / 1000).toFixed(2)}s` : 'N/A'}
                              </p>
                            </div>
                          </div>

                          {/* Issues Count */}
                          {review.suggestion_count !== undefined && (
                            <div>
                              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                Issues Détectés
                              </h4>
                              <div className="flex items-center gap-4">
                                <span className="px-3 py-1 bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300 rounded-full text-sm">
                                  {review.critical_count || 0} Critiques
                                </span>
                                <span className="px-3 py-1 bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-300 rounded-full text-sm">
                                  {review.high_count || 0} Élevés
                                </span>
                                <span className="px-3 py-1 bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300 rounded-full text-sm">
                                  {review.medium_count || 0} Moyens
                                </span>
                                <span className="px-3 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300 rounded-full text-sm">
                                  {review.low_count || 0} Faibles
                                </span>
                              </div>
                            </div>
                          )}

                          {/* Error Message */}
                          {review.error_message && (
                            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
                              <h4 className="text-sm font-semibold text-red-800 dark:text-red-300 mb-1">
                                Erreur
                              </h4>
                              <p className="text-sm text-red-600 dark:text-red-400">
                                {review.error_message}
                              </p>
                            </div>
                          )}

                          {/* Action Buttons */}
                          <div className="flex gap-3 pt-2">
                            <button
                              onClick={() => navigate(`/reviews/${review.id}`)}
                              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
                            >
                              <Eye className="w-4 h-4" />
                              Voir les Détails
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>

        {/* Empty State */}
        {filteredReviews.length === 0 && (
          <div className="text-center py-12">
            <FileCode className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Aucune révision trouvée
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              {searchTerm || statusFilter !== 'all' || languageFilter !== 'all'
                ? 'Essayez de modifier vos filtres de recherche'
                : 'Commencez par télécharger votre code pour obtenir une révision'}
            </p>
          </div>
        )}
      </div>

      {/* Pagination (if needed) */}
      {filteredReviews.length > 50 && (
        <div className="flex items-center justify-center gap-2">
          <button className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
            Précédent
          </button>
          <span className="px-4 py-2 text-gray-600 dark:text-gray-400">
            Page 1
          </span>
          <button className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">
            Suivant
          </button>
        </div>
      )}
    </div>
  );
};

export default History;