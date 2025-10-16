// services/api.js - Configuration de l'API et client HTTP

import axios from 'axios';
import { API_BASE_URL, ERROR_MESSAGES } from '../utils/constants';

// Configuration de base d'Axios
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 secondes
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Intercepteur pour les requêtes
api.interceptors.request.use(
  (config) => {
    // Ajouter un timestamp pour éviter le cache
    config.params = {
      ...config.params,
      _t: Date.now(),
    };

    // Log des requêtes en mode développement
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config);
    }

    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Intercepteur pour les réponses
api.interceptors.response.use(
  (response) => {
    // Log des réponses en mode développement
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, response);
    }

    return response;
  },
  (error) => {
    // Gestion centralisée des erreurs
    console.error('[API Response Error]', error);

    const errorResponse = {
      message: ERROR_MESSAGES.GENERIC_ERROR,
      status: error.response?.status,
      data: error.response?.data,
      originalError: error,
    };

    // Personnalisation des messages d'erreur selon le status
    if (error.code === 'ECONNABORTED') {
      errorResponse.message = 'Timeout - La requête a pris trop de temps';
    } else if (error.code === 'ERR_NETWORK') {
      errorResponse.message = ERROR_MESSAGES.NETWORK_ERROR;
    } else if (error.response) {
      const { status } = error.response;
      
      switch (status) {
        case 400:
          errorResponse.message = 'Requête invalide';
          break;
        case 401:
          errorResponse.message = 'Non autorisé';
          break;
        case 403:
          errorResponse.message = 'Accès refusé';
          break;
        case 404:
          errorResponse.message = 'Ressource non trouvée';
          break;
        case 413:
          errorResponse.message = ERROR_MESSAGES.FILE_TOO_LARGE;
          break;
        case 422:
          errorResponse.message = 'Données invalides';
          break;
        case 429:
          errorResponse.message = 'Trop de requêtes, veuillez patienter';
          break;
        case 500:
          errorResponse.message = ERROR_MESSAGES.SERVER_ERROR;
          break;
        case 502:
          errorResponse.message = 'Service temporairement indisponible';
          break;
        case 503:
          errorResponse.message = 'Service en maintenance';
          break;
        default:
          errorResponse.message = `Erreur ${status}: ${error.response.data?.message || 'Erreur inconnue'}`;
      }

      // Utiliser le message du serveur si disponible
      if (error.response.data?.detail) {
        errorResponse.message = error.response.data.detail;
      } else if (error.response.data?.message) {
        errorResponse.message = error.response.data.message;
      }
    }

    return Promise.reject(errorResponse);
  }
);

// Utilitaires pour les requêtes
export const apiUtils = {
  // GET request
  get: async (url, config = {}) => {
    try {
      const response = await api.get(url, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // POST request
  post: async (url, data = {}, config = {}) => {
    try {
      const response = await api.post(url, data, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // PUT request
  put: async (url, data = {}, config = {}) => {
    try {
      const response = await api.put(url, data, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // PATCH request
  patch: async (url, data = {}, config = {}) => {
    try {
      const response = await api.patch(url, data, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // DELETE request
  delete: async (url, config = {}) => {
    try {
      const response = await api.delete(url, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Upload avec suivi de progression
  upload: async (url, formData, onProgress = null) => {
    try {
      const config = {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress(percentCompleted);
          }
        },
      };

      const response = await api.post(url, formData, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Download de fichier
  download: async (url, filename, onProgress = null) => {
    try {
      const config = {
        responseType: 'blob',
        onDownloadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress(percentCompleted);
          }
        },
      };

      const response = await api.get(url, config);
      
      // Créer un lien de téléchargement
      const blob = new Blob([response.data]);
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Requête avec retry
  retry: async (requestFn, maxRetries = 3, delay = 1000) => {
    let lastError;
    
    for (let i = 0; i < maxRetries; i++) {
      try {
        return await requestFn();
      } catch (error) {
        lastError = error;
        
        // Ne pas retry sur certaines erreurs
        if (error.status && [400, 401, 403, 404, 422].includes(error.status)) {
          throw error;
        }
        
        if (i < maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)));
        }
      }
    }
    
    throw lastError;
  },

  // Annulation de requête
  createCancelToken: () => {
    return axios.CancelToken.source();
  },

  // Vérifier si une erreur est due à l'annulation
  isCancel: (error) => {
    return axios.isCancel(error);
  },
};

// Health check
export const healthCheck = async () => {
  try {
    const response = await apiUtils.get('/api/v1/health');
    return {
      isHealthy: response.status === 'healthy',
      ...response,
    };
  } catch (error) {
    return {
      isHealthy: false,
      error: error.message,
    };
  }
};

// Configuration pour les tests
export const configureApi = (config) => {
  Object.assign(api.defaults, config);
};

export default api;