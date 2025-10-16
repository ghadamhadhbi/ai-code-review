import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { useLocalStorage } from '../hooks/useLocalStorage';

// Types d'actions
const ActionTypes = {
  SET_THEME: 'SET_THEME',
  SET_SIDEBAR_OPEN: 'SET_SIDEBAR_OPEN',
  SET_LOADING: 'SET_LOADING',
  SET_USER: 'SET_USER',
  SET_SETTINGS: 'SET_SETTINGS',
  SET_ERROR: 'SET_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',
};

// État initial
const initialState = {
  theme: 'light',
  sidebarOpen: true,
  loading: false,
  user: null,
  settings: {
    notifications: true,
    autoRefresh: true,
    refreshInterval: 30000, // 30 secondes
    maxFileSize: 5, // MB
    allowedExtensions: ['.py', '.js', '.java', '.cpp', '.c', '.h', '.jsx', '.tsx', '.ts', '.go', '.rs', '.php', '.rb'],
  },
  error: null,
};

// Reducer
const appReducer = (state, action) => {
  switch (action.type) {
    case ActionTypes.SET_THEME:
      return {
        ...state,
        theme: action.payload,
      };
    case ActionTypes.SET_SIDEBAR_OPEN:
      return {
        ...state,
        sidebarOpen: action.payload,
      };
    case ActionTypes.SET_LOADING:
      return {
        ...state,
        loading: action.payload,
      };
    case ActionTypes.SET_USER:
      return {
        ...state,
        user: action.payload,
      };
    case ActionTypes.SET_SETTINGS:
      return {
        ...state,
        settings: {
          ...state.settings,
          ...action.payload,
        },
      };
    case ActionTypes.SET_ERROR:
      return {
        ...state,
        error: action.payload,
      };
    case ActionTypes.CLEAR_ERROR:
      return {
        ...state,
        error: null,
      };
    default:
      return state;
  }
};

// Context
const AppContext = createContext();

// Provider
export const AppContextProvider = ({ children }) => {
  const [storedTheme] = useLocalStorage('theme', 'light');
  const [storedSettings] = useLocalStorage('settings', initialState.settings);
  
  const [state, dispatch] = useReducer(appReducer, {
    ...initialState,
    theme: storedTheme,
    settings: { ...initialState.settings, ...storedSettings },
  });

  // Actions
  const actions = {
    setTheme: (theme) => {
      dispatch({ type: ActionTypes.SET_THEME, payload: theme });
      localStorage.setItem('theme', theme);
      
      // Appliquer le thème au document
      if (theme === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    },

    setSidebarOpen: (open) => {
      dispatch({ type: ActionTypes.SET_SIDEBAR_OPEN, payload: open });
    },

    setLoading: (loading) => {
      dispatch({ type: ActionTypes.SET_LOADING, payload: loading });
    },

    setUser: (user) => {
      dispatch({ type: ActionTypes.SET_USER, payload: user });
    },

    updateSettings: (newSettings) => {
      const updatedSettings = { ...state.settings, ...newSettings };
      dispatch({ type: ActionTypes.SET_SETTINGS, payload: newSettings });
      localStorage.setItem('settings', JSON.stringify(updatedSettings));
    },

    setError: (error) => {
      dispatch({ type: ActionTypes.SET_ERROR, payload: error });
    },

    clearError: () => {
      dispatch({ type: ActionTypes.CLEAR_ERROR });
    },

    toggleTheme: () => {
      const newTheme = state.theme === 'light' ? 'dark' : 'light';
      actions.setTheme(newTheme);
    },

    toggleSidebar: () => {
      actions.setSidebarOpen(!state.sidebarOpen);
    },
  };

  // Effets
  useEffect(() => {
    // Appliquer le thème initial
    if (state.theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, []);

  // Détecter les préférences système pour le thème
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e) => {
      if (!localStorage.getItem('theme')) {
        actions.setTheme(e.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  const value = {
    ...state,
    ...actions,
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
};

// Hook personnalisé
export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppContextProvider');
  }
  return context;
};

// Sélecteurs
export const useTheme = () => {
  const { theme, setTheme, toggleTheme } = useAppContext();
  return { theme, setTheme, toggleTheme };
};

export const useSidebar = () => {
  const { sidebarOpen, setSidebarOpen, toggleSidebar } = useAppContext();
  return { sidebarOpen, setSidebarOpen, toggleSidebar };
};

export const useLoading = () => {
  const { loading, setLoading } = useAppContext();
  return { loading, setLoading };
};

export const useError = () => {
  const { error, setError, clearError } = useAppContext();
  return { error, setError, clearError };
};

export const useSettings = () => {
  const { settings, updateSettings } = useAppContext();
  return { settings, updateSettings };
};