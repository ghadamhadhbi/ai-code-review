// hooks/useLocalStorage.js - Hook pour la gestion du localStorage

import { useState, useEffect, useCallback } from 'react';

export const useLocalStorage = (key, initialValue) => {
  // Fonction pour obtenir la valeur depuis localStorage
  const getStoredValue = useCallback(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Erreur lors de la lecture de localStorage pour la clé "${key}":`, error);
      return initialValue;
    }
  }, [key, initialValue]);

  // État local avec la valeur du localStorage
  const [storedValue, setStoredValue] = useState(getStoredValue);

  // Fonction pour définir une nouvelle valeur
  const setValue = useCallback((value) => {
    try {
      // Permettre à value d'être une fonction pour la même API que useState
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      
      // Sauvegarder l'état
      setStoredValue(valueToStore);
      
      // Sauvegarder dans localStorage
      if (valueToStore === undefined) {
        window.localStorage.removeItem(key);
      } else {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      }
    } catch (error) {
      console.warn(`Erreur lors de l'écriture dans localStorage pour la clé "${key}":`, error);
    }
  }, [key, storedValue]);

  // Fonction pour supprimer la valeur
  const removeValue = useCallback(() => {
    try {
      window.localStorage.removeItem(key);
      setStoredValue(initialValue);
    } catch (error) {
      console.warn(`Erreur lors de la suppression de localStorage pour la clé "${key}":`, error);
    }
  }, [key, initialValue]);

  // Synchroniser avec les changements dans d'autres onglets/fenêtres
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === key && e.newValue !== null) {
        try {
          setStoredValue(JSON.parse(e.newValue));
        } catch (error) {
          console.warn(`Erreur lors de la synchronisation localStorage pour la clé "${key}":`, error);
        }
      } else if (e.key === key && e.newValue === null) {
        setStoredValue(initialValue);
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [key, initialValue]);

  // Vérifier si la valeur a changé dans localStorage (pour la synchronisation)
  useEffect(() => {
    const currentValue = getStoredValue();
    if (JSON.stringify(currentValue) !== JSON.stringify(storedValue)) {
      setStoredValue(currentValue);
    }
  }, [getStoredValue, storedValue]);

  return [storedValue, setValue, removeValue];
};

// Hook pour localStorage avec validation de schéma
export const useValidatedLocalStorage = (key, initialValue, validator) => {
  const [value, setValue, removeValue] = useLocalStorage(key, initialValue);

  const setValidatedValue = useCallback((newValue) => {
    if (validator && !validator(newValue)) {
      console.warn(`Valeur invalide pour la clé "${key}":`, newValue);
      return false;
    }
    setValue(newValue);
    return true;
  }, [setValue, validator, key]);

  return [value, setValidatedValue, removeValue];
};

// Hook pour localStorage avec expiration
export const useLocalStorageWithExpiry = (key, initialValue, ttlMs = 24 * 60 * 60 * 1000) => {
  const [value, setValue, removeValue] = useLocalStorage(key, null);

  const getValueWithExpiry = useCallback(() => {
    if (!value) return initialValue;

    try {
      const { data, timestamp } = value;
      if (Date.now() - timestamp > ttlMs) {
        removeValue();
        return initialValue;
      }
      return data;
    } catch (error) {
      removeValue();
      return initialValue;
    }
  }, [value, initialValue, ttlMs, removeValue]);

  const setValueWithExpiry = useCallback((newValue) => {
    const valueToStore = {
      data: newValue,
      timestamp: Date.now()
    };
    setValue(valueToStore);
  }, [setValue]);

  const currentValue = getValueWithExpiry();

  return [currentValue, setValueWithExpiry, removeValue];
};

// Hook pour localStorage avec compression (pour les grandes données)
export const useCompressedLocalStorage = (key, initialValue) => {
  const compress = useCallback((data) => {
    try {
      return btoa(JSON.stringify(data));
    } catch (error) {
      console.warn('Erreur de compression:', error);
      return data;
    }
  }, []);

  const decompress = useCallback((compressedData) => {
    try {
      return JSON.parse(atob(compressedData));
    } catch (error) {
      console.warn('Erreur de décompression:', error);
      return compressedData;
    }
  }, []);

  const [compressedValue, setCompressedValue, removeValue] = useLocalStorage(key, null);

  const value = compressedValue ? decompress(compressedValue) : initialValue;

  const setValue = useCallback((newValue) => {
    const compressed = compress(newValue);
    setCompressedValue(compressed);
  }, [compress, setCompressedValue]);

  return [value, setValue, removeValue];
};

// Hook pour synchroniser un état avec localStorage
export const useSyncedState = (key, initialValue) => {
  const [storedValue, setStoredValue] = useLocalStorage(key, initialValue);
  const [localValue, setLocalValue] = useState(storedValue);

  // Synchroniser l'état local avec localStorage
  useEffect(() => {
    setLocalValue(storedValue);
  }, [storedValue]);

  // Fonction pour mettre à jour les deux
  const updateValue = useCallback((value) => {
    const newValue = typeof value === 'function' ? value(localValue) : value;
    setLocalValue(newValue);
    setStoredValue(newValue);
  }, [localValue, setStoredValue]);

  return [localValue, updateValue];
};

// Hook pour gérer un cache localStorage avec invalidation
export const useLocalStorageCache = (key, fetcher, dependencies = [], ttlMs = 5 * 60 * 1000) => {
  const [cachedData, setCachedData, removeCachedData] = useLocalStorageWithExpiry(key, null, ttlMs);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async (force = false) => {
    if (!force && cachedData !== null) {
      return cachedData;
    }

    setLoading(true);
    setError(null);

    try {
      const freshData = await fetcher();
      setCachedData(freshData);
      return freshData;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [cachedData, fetcher, setCachedData]);

  // Auto-refresh when dependencies change
  useEffect(() => {
    refresh();
  }, dependencies);

  const invalidate = useCallback(() => {
    removeCachedData();
    setError(null);
  }, [removeCachedData]);

  return {
    data: cachedData,
    loading,
    error,
    refresh,
    invalidate,
    isStale: cachedData === null
  };
};

// Hook pour gérer les préférences utilisateur
export const useUserPreferences = (defaultPreferences = {}) => {
  const [preferences, setPreferences] = useLocalStorage('userPreferences', defaultPreferences);

  const updatePreference = useCallback((key, value) => {
    setPreferences(prev => ({
      ...prev,
      [key]: value
    }));
  }, [setPreferences]);

  const updatePreferences = useCallback((newPreferences) => {
    setPreferences(prev => ({
      ...prev,
      ...newPreferences
    }));
  }, [setPreferences]);

  const resetPreferences = useCallback(() => {
    setPreferences(defaultPreferences);
  }, [setPreferences, defaultPreferences]);

  const getPreference = useCallback((key, fallback = null) => {
    return preferences[key] ?? fallback;
  }, [preferences]);

  return {
    preferences,
    updatePreference,
    updatePreferences,
    resetPreferences,
    getPreference
  };
};

// Hook pour gérer l'historique de navigation personnalisé
export const useNavigationHistory = (maxItems = 10) => {
  const [history, setHistory] = useLocalStorage('navigationHistory', []);

  const addToHistory = useCallback((item) => {
    setHistory(prev => {
      const newHistory = [item, ...prev.filter(h => h.path !== item.path)];
      return newHistory.slice(0, maxItems);
    });
  }, [setHistory, maxItems]);

  const removeFromHistory = useCallback((path) => {
    setHistory(prev => prev.filter(item => item.path !== path));
  }, [setHistory]);

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, [setHistory]);

  const getRecentItems = useCallback((count = 5) => {
    return history.slice(0, count);
  }, [history]);

  return {
    history,
    addToHistory,
    removeFromHistory,
    clearHistory,
    getRecentItems
  };
};

// Hook pour gérer les éléments favoris
export const useFavorites = (key = 'favorites') => {
  const [favorites, setFavorites] = useLocalStorage(key, []);

  const addToFavorites = useCallback((item) => {
    setFavorites(prev => {
      if (prev.some(fav => fav.id === item.id)) {
        return prev;
      }
      return [...prev, { ...item, addedAt: Date.now() }];
    });
  }, [setFavorites]);

  const removeFromFavorites = useCallback((itemId) => {
    setFavorites(prev => prev.filter(item => item.id !== itemId));
  }, [setFavorites]);

  const isFavorite = useCallback((itemId) => {
    return favorites.some(item => item.id === itemId);
  }, [favorites]);

  const toggleFavorite = useCallback((item) => {
    if (isFavorite(item.id)) {
      removeFromFavorites(item.id);
    } else {
      addToFavorites(item);
    }
  }, [isFavorite, addToFavorites, removeFromFavorites]);

  const clearFavorites = useCallback(() => {
    setFavorites([]);
  }, [setFavorites]);

  return {
    favorites,
    addToFavorites,
    removeFromFavorites,
    isFavorite,
    toggleFavorite,
    clearFavorites,
    count: favorites.length
  };
};

// Hook pour gérer les drafts/brouillons
export const useDrafts = (key = 'drafts') => {
  const [drafts, setDrafts] = useLocalStorage(key, {});

  const saveDraft = useCallback((id, data) => {
    setDrafts(prev => ({
      ...prev,
      [id]: {
        data,
        savedAt: Date.now(),
        id
      }
    }));
  }, [setDrafts]);

  const getDraft = useCallback((id) => {
    return drafts[id] || null;
  }, [drafts]);

  const removeDraft = useCallback((id) => {
    setDrafts(prev => {
      const { [id]: removed, ...rest } = prev;
      return rest;
    });
  }, [setDrafts]);

  const clearAllDrafts = useCallback(() => {
    setDrafts({});
  }, [setDrafts]);

  const hasDraft = useCallback((id) => {
    return Boolean(drafts[id]);
  }, [drafts]);

  const getAllDrafts = useCallback(() => {
    return Object.values(drafts).sort((a, b) => b.savedAt - a.savedAt);
  }, [drafts]);

  return {
    drafts: getAllDrafts(),
    saveDraft,
    getDraft,
    removeDraft,
    clearAllDrafts,
    hasDraft,
    count: Object.keys(drafts).length
  };
};