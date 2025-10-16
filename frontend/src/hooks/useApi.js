// hooks/useApi.js - Hook pour les appels API avec React Query

import { useQuery, useMutation, useQueryClient } from 'react-query';
import { apiUtils } from '../services/api';
import { useNotification } from '../context/NotificationContext';

// Hook générique pour les requêtes GET
export const useApiQuery = (queryKey, queryFn, options = {}) => {
  const { addNotification } = useNotification();
  
  return useQuery(queryKey, queryFn, {
    onError: (error) => {
      if (options.showErrorNotification !== false) {
        addNotification({
          type: 'error',
          title: 'Erreur de chargement',
          message: error.message || 'Une erreur est survenue lors du chargement des données',
        });
      }
    },
    retry: (failureCount, error) => {
      // Ne pas retry sur certaines erreurs
      if (error.status && [400, 401, 403, 404].includes(error.status)) {
        return false;
      }
      return failureCount < 3;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
    ...options,
  });
};

// Hook générique pour les mutations
export const useApiMutation = (mutationFn, options = {}) => {
  const { addNotification } = useNotification();
  const queryClient = useQueryClient();

  return useMutation(mutationFn, {
    onSuccess: (data, variables, context) => {
      if (options.successMessage) {
        addNotification({
          type: 'success',
          title: 'Succès',
          message: typeof options.successMessage === 'function' 
            ? options.successMessage(data, variables) 
            : options.successMessage,
        });
      }
      
      // Invalider les queries liées
      if (options.invalidateQueries) {
        const queries = Array.isArray(options.invalidateQueries) 
          ? options.invalidateQueries 
          : [options.invalidateQueries];
        queries.forEach(queryKey => {
          queryClient.invalidateQueries(queryKey);
        });
      }

      options.onSuccess?.(data, variables, context);
    },
    onError: (error, variables, context) => {
      if (options.showErrorNotification !== false) {
        addNotification({
          type: 'error',
          title: 'Erreur',
          message: error.message || 'Une erreur est survenue',
        });
      }
      
      options.onError?.(error, variables, context);
    },
    ...options,
  });
};

// Hook pour les requêtes avec pagination
export const usePaginatedQuery = (queryKey, queryFn, options = {}) => {
  const { page = 1, pageSize = 20, ...otherOptions } = options;
  
  return useApiQuery(
    [...queryKey, { page, pageSize }],
    () => queryFn({ page, pageSize }),
    {
      keepPreviousData: true,
      ...otherOptions,
    }
  );
};

// Hook pour les requêtes avec recherche et débounce
export const useSearchQuery = (queryKey, queryFn, searchTerm, options = {}) => {
  const { debounceMs = 300, ...otherOptions } = options;
  
  return useApiQuery(
    [...queryKey, { search: searchTerm }],
    () => queryFn(searchTerm),
    {
      enabled: searchTerm.length >= 2, // Minimum 2 caractères
      staleTime: 30 * 1000, // 30 secondes pour les recherches
      ...otherOptions,
    }
  );
};

// Hook pour les requêtes en temps réel (polling)
export const useRealtimeQuery = (queryKey, queryFn, options = {}) => {
  const { interval = 30000, ...otherOptions } = options;
  
  return useApiQuery(queryKey, queryFn, {
    refetchInterval: interval,
    refetchIntervalInBackground: true,
    ...otherOptions,
  });
};

// Hook pour les requêtes avec retry automatique
export const useRetryQuery = (queryKey, queryFn, options = {}) => {
  const { maxRetries = 3, retryDelay = 1000, ...otherOptions } = options;
  
  return useApiQuery(queryKey, queryFn, {
    retry: (failureCount, error) => {
      if (failureCount >= maxRetries) return false;
      if (error.status && [400, 401, 403, 404].includes(error.status)) {
        return false;
      }
      return true;
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    ...otherOptions,
  });
};

// Hook pour les mutations en batch
export const useBatchMutation = (mutationFn, options = {}) => {
  const { addNotification } = useNotification();
  
  return useApiMutation(
    async (items) => {
      const results = [];
      const errors = [];
      
      for (const item of items) {
        try {
          const result = await mutationFn(item);
          results.push({ item, result, success: true });
        } catch (error) {
          errors.push({ item, error, success: false });
        }
      }
      
      return { results, errors };
    },
    {
      onSuccess: (data) => {
        const { results, errors } = data;
        
        if (results.length > 0) {
          addNotification({
            type: 'success',
            title: 'Traitement terminé',
            message: `${results.length} élément(s) traité(s) avec succès`,
          });
        }
        
        if (errors.length > 0) {
          addNotification({
            type: 'warning',
            title: 'Erreurs partielles',
            message: `${errors.length} élément(s) ont échoué`,
          });
        }
      },
      ...options,
    }
  );
};

// Hook pour les uploads avec progression
export const useUploadMutation = (uploadFn, options = {}) => {
  const { addNotification } = useNotification();
  
  return useApiMutation(
    async ({ file, onProgress }) => {
      return uploadFn(file, onProgress);
    },
    {
      onSuccess: (data) => {
        addNotification({
          type: 'success',
          title: 'Upload terminé',
          message: 'Le fichier a été téléchargé avec succès',
        });
      },
      onError: (error) => {
        addNotification({
          type: 'error',
          title: 'Erreur d\'upload',
          message: error.message || 'Erreur lors du téléchargement',
        });
      },
      ...options,
    }
  );
};

// Hook pour optimistic updates
export const useOptimisticMutation = (mutationFn, options = {}) => {
  const queryClient = useQueryClient();
  const { queryKey, updateFn, ...otherOptions } = options;
  
  return useApiMutation(mutationFn, {
    onMutate: async (variables) => {
      // Annuler les requêtes sortantes
      await queryClient.cancelQueries(queryKey);
      
      // Snapshot des données actuelles
      const previousData = queryClient.getQueryData(queryKey);
      
      // Mise à jour optimiste
      if (updateFn) {
        queryClient.setQueryData(queryKey, updateFn(previousData, variables));
      }
      
      return { previousData };
    },
    onError: (error, variables, context) => {
      // Restaurer les données précédentes en cas d'erreur
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
    },
    onSettled: () => {
      // Toujours refetch après settled
      queryClient.invalidateQueries(queryKey);
    },
    ...otherOptions,
  });
};

// Hook pour les mutations avec confirmation
export const useConfirmedMutation = (mutationFn, options = {}) => {
  const { confirmMessage = 'Êtes-vous sûr ?', ...otherOptions } = options;
  
  return useApiMutation(
    async (variables) => {
      const confirmed = window.confirm(confirmMessage);
      if (!confirmed) {
        throw new Error('Action annulée par l\'utilisateur');
      }
      return mutationFn(variables);
    },
    otherOptions
  );
};

// Hook pour les requêtes dépendantes
export const useDependentQueries = (queries) => {
  const results = [];
  
  for (let i = 0; i < queries.length; i++) {
    const { queryKey, queryFn, enabled = true, ...options } = queries[i];
    
    // Chaque requête dépend du succès de la précédente
    const isEnabled = enabled && (i === 0 || results[i - 1]?.isSuccess);
    
    const result = useApiQuery(
      queryKey,
      queryFn,
      {
        enabled: isEnabled,
        ...options,
      }
    );
    
    results.push(result);
  }
  
  return results;
};

// Hook pour les requêtes en parallèle
export const useParallelQueries = (queries) => {
  return queries.map(({ queryKey, queryFn, ...options }) =>
    useApiQuery(queryKey, queryFn, options)
  );
};

// Hook pour invalidate queries
export const useInvalidateQueries = () => {
  const queryClient = useQueryClient();
  
  return {
    invalidate: (queryKey) => queryClient.invalidateQueries(queryKey),
    invalidateAll: () => queryClient.invalidateQueries(),
    refetch: (queryKey) => queryClient.refetchQueries(queryKey),
    reset: (queryKey) => queryClient.resetQueries(queryKey),
    remove: (queryKey) => queryClient.removeQueries(queryKey),
  };
};

// Hook pour l'état global des requêtes
export const useGlobalLoadingState = () => {
  const queryClient = useQueryClient();
  const queries = queryClient.getQueryCache().getAll();
  
  const isLoading = queries.some(query => query.state.isFetching);
  const hasErrors = queries.some(query => query.state.isError);
  const loadingCount = queries.filter(query => query.state.isFetching).length;
  const errorCount = queries.filter(query => query.state.isError).length;
  
  return {
    isLoading,
    hasErrors,
    loadingCount,
    errorCount,
    totalQueries: queries.length,
  };
};

export default {
  useApiQuery,
  useApiMutation,
  usePaginatedQuery,
  useSearchQuery,
  useRealtimeQuery,
  useRetryQuery,
  useBatchMutation,
  useUploadMutation,
  useOptimisticMutation,
  useConfirmedMutation,
  useDependentQueries,
  useParallelQueries,
  useInvalidateQueries,
  useGlobalLoadingState,
};