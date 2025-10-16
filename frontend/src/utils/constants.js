// utils/constants.js - Configuration constants

// ============================================================================
// API Configuration
// ============================================================================
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8003';

export const API_ENDPOINTS = {
  // Upload endpoints
  UPLOAD: '/api/upload',
  UPLOAD_STATUS: (uploadId) => `/api/upload/status/${uploadId}`,
  
  // Review endpoints
  REVIEWS: '/api/reviews',
  REVIEW_DETAIL: (reviewId) => `/api/reviews/${reviewId}`,
  REVIEW_STATS: '/api/reviews/stats',
  REVIEW_SUGGESTIONS: (reviewId) => `/api/reviews/${reviewId}/suggestions`,
  REVIEW_FEEDBACK: (reviewId) => `/api/reviews/${reviewId}/feedback`,
  
  // Upload review endpoints
  UPLOAD_REVIEW_STATUS: (uploadId) => `/api/reviews/upload/${uploadId}/status`,
  UPLOAD_REVIEW_CANCEL: (uploadId) => `/api/reviews/upload/${uploadId}/cancel`,
  
  // WebSocket endpoints
  WS_REVIEWS: '/api/reviews/ws/reviews',
  
  // Health check
  HEALTH: '/health'
};

// ============================================================================
// File Upload Configuration
// ============================================================================
export const FILE_UPLOAD = {
  MAX_SIZE: 5 * 1024 * 1024, // 5MB per file
  MAX_FILES: 10,
  ALLOWED_EXTENSIONS: [
    '.py',    // Python
    '.js',    // JavaScript
    '.jsx',   // React JSX
    '.ts',    // TypeScript
    '.tsx',   // React TSX
    '.java',  // Java
    '.cpp',   // C++
    '.c',     // C
    '.h',     // C/C++ Header
    '.go',    // Go
    '.rs',    // Rust
    '.php',   // PHP
    '.rb',    // Ruby
    '.html',  // HTML
    '.css',   // CSS
    '.scss',  // SCSS
    '.sass',  // Sass
    '.json',  // JSON
    '.xml',   // XML
    '.yaml',  // YAML
    '.yml'    // YAML
  ],
  CHUNK_SIZE: 1024 * 1024, // 1MB chunks for large files
};

export const LANGUAGE_MAP = {
  '.py': 'python',
  '.js': 'javascript',
  '.jsx': 'javascript',
  '.ts': 'typescript',
  '.tsx': 'typescript',
  '.java': 'java',
  '.cpp': 'cpp',
  '.c': 'c',
  '.h': 'c',
  '.go': 'go',
  '.rs': 'rust',
  '.php': 'php',
  '.rb': 'ruby',
  '.html': 'html',
  '.css': 'css',
  '.scss': 'scss',
  '.sass': 'sass',
  '.json': 'json',
  '.xml': 'xml',
  '.yaml': 'yaml',
  '.yml': 'yaml'
};

// ============================================================================
// Review Status Configuration
// ============================================================================
export const REVIEW_STATUS = {
  PENDING: 'pending',
  UPLOADED: 'uploaded',
  PROCESSING: 'processing',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
};

export const REVIEW_STATUS_LABELS = {
  [REVIEW_STATUS.PENDING]: 'En attente',
  [REVIEW_STATUS.UPLOADED]: 'Téléchargé',
  [REVIEW_STATUS.PROCESSING]: 'En cours',
  [REVIEW_STATUS.IN_PROGRESS]: 'En cours',
  [REVIEW_STATUS.COMPLETED]: 'Terminé',
  [REVIEW_STATUS.FAILED]: 'Échoué',
  [REVIEW_STATUS.CANCELLED]: 'Annulé'
};

// ============================================================================
// Severity Levels
// ============================================================================
export const SEVERITY_LEVELS = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
  INFO: 'info'
};

export const SEVERITY_LABELS = {
  [SEVERITY_LEVELS.CRITICAL]: 'Critique',
  [SEVERITY_LEVELS.HIGH]: 'Important',
  [SEVERITY_LEVELS.MEDIUM]: 'Moyen',
  [SEVERITY_LEVELS.LOW]: 'Faible',
  [SEVERITY_LEVELS.INFO]: 'Information'
};

export const SEVERITY_COLORS = {
  [SEVERITY_LEVELS.CRITICAL]: {
    bg: 'bg-red-100 dark:bg-red-900/20',
    text: 'text-red-800 dark:text-red-300',
    border: 'border-red-200 dark:border-red-800',
    icon: 'text-red-500'
  },
  [SEVERITY_LEVELS.HIGH]: {
    bg: 'bg-orange-100 dark:bg-orange-900/20',
    text: 'text-orange-800 dark:text-orange-300',
    border: 'border-orange-200 dark:border-orange-800',
    icon: 'text-orange-500'
  },
  [SEVERITY_LEVELS.MEDIUM]: {
    bg: 'bg-yellow-100 dark:bg-yellow-900/20',
    text: 'text-yellow-800 dark:text-yellow-300',
    border: 'border-yellow-200 dark:border-yellow-800',
    icon: 'text-yellow-500'
  },
  [SEVERITY_LEVELS.LOW]: {
    bg: 'bg-blue-100 dark:bg-blue-900/20',
    text: 'text-blue-800 dark:text-blue-300',
    border: 'border-blue-200 dark:border-blue-800',
    icon: 'text-blue-500'
  },
  [SEVERITY_LEVELS.INFO]: {
    bg: 'bg-gray-100 dark:bg-gray-900/20',
    text: 'text-gray-800 dark:text-gray-300',
    border: 'border-gray-200 dark:border-gray-800',
    icon: 'text-gray-500'
  }
};

// ============================================================================
// Priority Levels
// ============================================================================
export const PRIORITY_LEVELS = {
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low'
};

export const PRIORITY_LABELS = {
  [PRIORITY_LEVELS.HIGH]: 'Haute',
  [PRIORITY_LEVELS.MEDIUM]: 'Moyenne',
  [PRIORITY_LEVELS.LOW]: 'Basse'
};

// ============================================================================
// Pagination
// ============================================================================
export const PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_PAGE_SIZE: 20,
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100]
};

// ============================================================================
// Error Messages
// ============================================================================
export const ERROR_MESSAGES = {
  // Network errors
  NETWORK_ERROR: 'Erreur de connexion au serveur. Veuillez vérifier votre connexion internet.',
  TIMEOUT: 'La requête a pris trop de temps. Veuillez réessayer.',
  
  // Upload errors
  UPLOAD_FAILED: 'Échec du téléchargement. Veuillez réessayer.',
  FILE_TOO_LARGE: 'Le fichier est trop volumineux. Taille maximale: 5MB.',
  INVALID_FILE_TYPE: 'Type de fichier non supporté.',
  TOO_MANY_FILES: 'Trop de fichiers. Maximum: 10 fichiers.',
  
  // Review errors
  REVIEW_NOT_FOUND: 'Révision non trouvée.',
  REVIEW_LOAD_FAILED: 'Impossible de charger la révision.',
  
  // API errors
  SERVER_ERROR: 'Erreur serveur. Veuillez réessayer plus tard.',
  UNAUTHORIZED: 'Non autorisé. Veuillez vous reconnecter.',
  FORBIDDEN: 'Accès refusé.',
  NOT_FOUND: 'Ressource non trouvée.',
  
  // Generic
  GENERIC_ERROR: 'Une erreur inattendue s\'est produite.',
  VALIDATION_ERROR: 'Données invalides.'
};

// ============================================================================
// Success Messages
// ============================================================================
export const SUCCESS_MESSAGES = {
  FILE_UPLOADED: 'Fichiers téléchargés avec succès !',
  REVIEW_COMPLETED: 'Révision terminée avec succès !',
  REVIEW_CANCELLED: 'Révision annulée.',
  REVIEW_DELETED: 'Révision supprimée.',
  FEEDBACK_SUBMITTED: 'Feedback envoyé avec succès !'
};

// ============================================================================
// WebSocket Configuration
// ============================================================================
export const WEBSOCKET = {
  RECONNECT_INTERVAL: 5000, // 5 seconds
  HEARTBEAT_INTERVAL: 30000, // 30 seconds
  MAX_RECONNECT_ATTEMPTS: 5
};

// ============================================================================
// Local Storage Keys
// ============================================================================
export const STORAGE_KEYS = {
  THEME: 'code-review-theme',
  USER_PREFERENCES: 'code-review-preferences',
  RECENT_SEARCHES: 'code-review-recent-searches',
  FILTERS: 'code-review-filters'
};

// ============================================================================
// Date/Time Formats
// ============================================================================
export const DATE_FORMATS = {
  FULL: 'dd/MM/yyyy HH:mm:ss',
  DATE: 'dd/MM/yyyy',
  TIME: 'HH:mm:ss',
  RELATIVE: 'relative' // e.g., "il y a 2 heures"
};

// ============================================================================
// Chart Configuration
// ============================================================================
export const CHART_COLORS = {
  PRIMARY: '#3B82F6', // blue-500
  SUCCESS: '#10B981', // green-500
  WARNING: '#F59E0B', // yellow-500
  DANGER: '#EF4444',  // red-500
  INFO: '#6366F1',    // indigo-500
  GRAY: '#6B7280'     // gray-500
};

// ============================================================================
// Animation Configuration
// ============================================================================
export const ANIMATION = {
  DURATION: {
    FAST: 150,
    NORMAL: 300,
    SLOW: 500
  },
  EASING: {
    EASE_IN: 'ease-in',
    EASE_OUT: 'ease-out',
    EASE_IN_OUT: 'ease-in-out'
  }
};

// ============================================================================
// Feature Flags
// ============================================================================
export const FEATURES = {
  WEBSOCKET_ENABLED: true,
  DARK_MODE_ENABLED: true,
  ANALYTICS_ENABLED: true,
  FEEDBACK_ENABLED: true,
  EXPORT_ENABLED: true,
  NOTIFICATIONS_ENABLED: true
};

// ============================================================================
// Application Metadata
// ============================================================================
export const APP_INFO = {
  NAME: 'Code Review AI',
  VERSION: '1.0.0',
  DESCRIPTION: 'Assistant intelligent de révision de code',
  AUTHOR: 'Your Company',
  SUPPORT_EMAIL: 'support@example.com'
};

// ============================================================================
// Validation Rules
// ============================================================================
export const VALIDATION = {
  EMAIL_REGEX: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  MAX_DESCRIPTION_LENGTH: 1000,
  MIN_DESCRIPTION_LENGTH: 10,
  MAX_FILENAME_LENGTH: 255
};

// ============================================================================
// Timeouts
// ============================================================================
export const TIMEOUTS = {
  API_REQUEST: 30000,      // 30 seconds
  UPLOAD_REQUEST: 120000,  // 2 minutes
  WEBSOCKET_PING: 30000,   // 30 seconds
  NOTIFICATION_DURATION: 5000 // 5 seconds
};

// ============================================================================
// Sort Options
// ============================================================================
export const SORT_OPTIONS = [
  { value: 'created_desc', label: 'Plus récent' },
  { value: 'created_asc', label: 'Plus ancien' },
  { value: 'status', label: 'Statut' },
  { value: 'priority', label: 'Priorité' },
  { value: 'score', label: 'Score' },
  { value: 'filename', label: 'Nom de fichier' }
];

// ============================================================================
// Filter Options
// ============================================================================
export const STATUS_FILTER_OPTIONS = [
  { value: '', label: 'Tous les statuts' },
  { value: REVIEW_STATUS.PENDING, label: REVIEW_STATUS_LABELS[REVIEW_STATUS.PENDING] },
  { value: REVIEW_STATUS.PROCESSING, label: REVIEW_STATUS_LABELS[REVIEW_STATUS.PROCESSING] },
  { value: REVIEW_STATUS.COMPLETED, label: REVIEW_STATUS_LABELS[REVIEW_STATUS.COMPLETED] },
  { value: REVIEW_STATUS.FAILED, label: REVIEW_STATUS_LABELS[REVIEW_STATUS.FAILED] }
];

export const PRIORITY_FILTER_OPTIONS = [
  { value: '', label: 'Toutes les priorités' },
  { value: PRIORITY_LEVELS.HIGH, label: PRIORITY_LABELS[PRIORITY_LEVELS.HIGH] },
  { value: PRIORITY_LEVELS.MEDIUM, label: PRIORITY_LABELS[PRIORITY_LEVELS.MEDIUM] },
  { value: PRIORITY_LEVELS.LOW, label: PRIORITY_LABELS[PRIORITY_LEVELS.LOW] }
];

export const SEVERITY_FILTER_OPTIONS = [
  { value: '', label: 'Toutes les sévérités' },
  { value: SEVERITY_LEVELS.CRITICAL, label: SEVERITY_LABELS[SEVERITY_LEVELS.CRITICAL] },
  { value: SEVERITY_LEVELS.HIGH, label: SEVERITY_LABELS[SEVERITY_LEVELS.HIGH] },
  { value: SEVERITY_LEVELS.MEDIUM, label: SEVERITY_LABELS[SEVERITY_LEVELS.MEDIUM] },
  { value: SEVERITY_LEVELS.LOW, label: SEVERITY_LABELS[SEVERITY_LEVELS.LOW] }
];

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get WebSocket URL from HTTP URL
 */
export const getWebSocketUrl = (httpUrl = API_BASE_URL) => {
  return httpUrl.replace(/^http/, 'ws');
};

/**
 * Format bytes to human readable size
 */
export const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * Format duration in milliseconds to human readable format
 */
export const formatDuration = (ms) => {
  if (!ms || ms < 0) return 'N/A';
  
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
};

/**
 * Validate email address
 */
export const isValidEmail = (email) => {
  return VALIDATION.EMAIL_REGEX.test(email);
};

/**
 * Get file extension from filename
 */
export const getFileExtension = (filename) => {
  const lastDot = filename.lastIndexOf('.');
  return lastDot > 0 ? filename.substring(lastDot).toLowerCase() : '';
};

/**
 * Get language from file extension
 */
export const getLanguageFromExtension = (extension) => {
  return LANGUAGE_MAP[extension] || 'text';
};

export default {
  API_BASE_URL,
  API_ENDPOINTS,
  FILE_UPLOAD,
  LANGUAGE_MAP,
  REVIEW_STATUS,
  REVIEW_STATUS_LABELS,
  SEVERITY_LEVELS,
  SEVERITY_LABELS,
  SEVERITY_COLORS,
  PRIORITY_LEVELS,
  PRIORITY_LABELS,
  PAGINATION,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
  WEBSOCKET,
  STORAGE_KEYS,
  DATE_FORMATS,
  CHART_COLORS,
  ANIMATION,
  FEATURES,
  APP_INFO,
  VALIDATION,
  TIMEOUTS,
  SORT_OPTIONS,
  STATUS_FILTER_OPTIONS,
  PRIORITY_FILTER_OPTIONS,
  SEVERITY_FILTER_OPTIONS,
  getWebSocketUrl,
  formatBytes,
  formatDuration,
  isValidEmail,
  getFileExtension,
  getLanguageFromExtension
};