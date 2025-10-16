// context/NotificationContext.jsx - Context pour les notifications

import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import { NOTIFICATION_TYPE } from '../utils/constants';

// Types d'actions
const ActionTypes = {
  ADD_NOTIFICATION: 'ADD_NOTIFICATION',
  REMOVE_NOTIFICATION: 'REMOVE_NOTIFICATION',
  MARK_AS_READ: 'MARK_AS_READ',
  MARK_ALL_AS_READ: 'MARK_ALL_AS_READ',
  CLEAR_ALL: 'CLEAR_ALL',
  SET_NOTIFICATIONS: 'SET_NOTIFICATIONS',
};

// État initial
const initialState = {
  notifications: [],
  unreadCount: 0,
};

// Reducer
const notificationReducer = (state, action) => {
  switch (action.type) {
    case ActionTypes.ADD_NOTIFICATION: {
      const newNotification = {
        id: Date.now() + Math.random(),
        timestamp: new Date().toISOString(),
        read: false,
        ...action.payload,
      };

      const notifications = [newNotification, ...state.notifications];
      
      return {
        ...state,
        notifications,
        unreadCount: notifications.filter(n => !n.read).length,
      };
    }

    case ActionTypes.REMOVE_NOTIFICATION: {
      const notifications = state.notifications.filter(
        notification => notification.id !== action.payload
      );
      
      return {
        ...state,
        notifications,
        unreadCount: notifications.filter(n => !n.read).length,
      };
    }

    case ActionTypes.MARK_AS_READ: {
      const notifications = state.notifications.map(notification =>
        notification.id === action.payload
          ? { ...notification, read: true }
          : notification
      );
      
      return {
        ...state,
        notifications,
        unreadCount: notifications.filter(n => !n.read).length,
      };
    }

    case ActionTypes.MARK_ALL_AS_READ: {
      const notifications = state.notifications.map(notification => ({
        ...notification,
        read: true,
      }));
      
      return {
        ...state,
        notifications,
        unreadCount: 0,
      };
    }

    case ActionTypes.CLEAR_ALL: {
      return {
        ...state,
        notifications: [],
        unreadCount: 0,
      };
    }

    case ActionTypes.SET_NOTIFICATIONS: {
      const notifications = action.payload;
      return {
        ...state,
        notifications,
        unreadCount: notifications.filter(n => !n.read).length,
      };
    }

    default:
      return state;
  }
};

// Context
const NotificationContext = createContext();

// Provider
export const NotificationContextProvider = ({ children }) => {
  const [state, dispatch] = useReducer(notificationReducer, initialState);

  // Charger les notifications depuis le localStorage au démarrage
  useEffect(() => {
    const savedNotifications = localStorage.getItem('notifications');
    if (savedNotifications) {
      try {
        const notifications = JSON.parse(savedNotifications);
        dispatch({ type: ActionTypes.SET_NOTIFICATIONS, payload: notifications });
      } catch (error) {
        console.warn('Impossible de charger les notifications sauvegardées:', error);
      }
    }
  }, []);

  // Sauvegarder les notifications dans le localStorage
  useEffect(() => {
    localStorage.setItem('notifications', JSON.stringify(state.notifications));
  }, [state.notifications]);

  // Actions
  const actions = {
    // Ajouter une notification
    addNotification: useCallback((notification) => {
      // Validation des données
      if (!notification.title && !notification.message) {
        console.warn('Notification requires title or message');
        return;
      }

      const validTypes = Object.values(NOTIFICATION_TYPE);
      const type = validTypes.includes(notification.type) 
        ? notification.type 
        : NOTIFICATION_TYPE.INFO;

      dispatch({
        type: ActionTypes.ADD_NOTIFICATION,
        payload: {
          ...notification,
          type,
          title: notification.title || 'Notification',
        },
      });

      // Auto-suppression après délai (optionnel)
      if (notification.autoDelete !== false) {
        const delay = notification.duration || (type === NOTIFICATION_TYPE.ERROR ? 10000 : 5000);
        setTimeout(() => {
          actions.removeNotification(notification.id || Date.now());
        }, delay);
      }
    }, []),

    // Supprimer une notification
    removeNotification: useCallback((id) => {
      dispatch({
        type: ActionTypes.REMOVE_NOTIFICATION,
        payload: id,
      });
    }, []),

    // Marquer comme lu
    markAsRead: useCallback((id) => {
      dispatch({
        type: ActionTypes.MARK_AS_READ,
        payload: id,
      });
    }, []),

    // Marquer toutes comme lues
    markAllAsRead: useCallback(() => {
      dispatch({ type: ActionTypes.MARK_ALL_AS_READ });
    }, []),

    // Effacer toutes les notifications
    clearAll: useCallback(() => {
      dispatch({ type: ActionTypes.CLEAR_ALL });
    }, []),

    // Notifications typées pour plus de facilité
    success: useCallback((title, message, options = {}) => {
      actions.addNotification({
        type: NOTIFICATION_TYPE.SUCCESS,
        title,
        message,
        ...options,
      });
    }, []),

    error: useCallback((title, message, options = {}) => {
      actions.addNotification({
        type: NOTIFICATION_TYPE.ERROR,
        title,
        message,
        autoDelete: false, // Les erreurs restent jusqu'à suppression manuelle
        ...options,
      });
    }, []),

    warning: useCallback((title, message, options = {}) => {
      actions.addNotification({
        type: NOTIFICATION_TYPE.WARNING,
        title,
        message,
        duration: 7000, // Plus long pour les avertissements
        ...options,
      });
    }, []),

    info: useCallback((title, message, options = {}) => {
      actions.addNotification({
        type: NOTIFICATION_TYPE.INFO,
        title,
        message,
        ...options,
      });
    }, []),

    // Notification de révision
    reviewNotification: useCallback((reviewId, title, message, type = NOTIFICATION_TYPE.INFO, options = {}) => {
      actions.addNotification({
        type,
        title,
        message,
        link: `/reviews/${reviewId}`,
        category: 'review',
        reviewId,
        ...options,
      });
    }, []),

    // Notification d'upload
    uploadNotification: useCallback((uploadId, title, message, type = NOTIFICATION_TYPE.INFO, options = {}) => {
      actions.addNotification({
        type,
        title,
        message,
        category: 'upload',
        uploadId,
        ...options,
      });
    }, []),

    // Obtenir les notifications par catégorie
    getNotificationsByCategory: useCallback((category) => {
      return state.notifications.filter(notification => 
        notification.category === category
      );
    }, [state.notifications]),

    // Obtenir les notifications non lues
    getUnreadNotifications: useCallback(() => {
      return state.notifications.filter(notification => !notification.read);
    }, [state.notifications]),

    // Obtenir les notifications récentes (dernières 24h)
    getRecentNotifications: useCallback(() => {
      const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
      return state.notifications.filter(notification => 
        new Date(notification.timestamp) > oneDayAgo
      );
    }, [state.notifications]),

    // Nettoyer les anciennes notifications (plus de 7 jours)
    cleanupOldNotifications: useCallback(() => {
      const oneWeekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
      const recentNotifications = state.notifications.filter(notification => 
        new Date(notification.timestamp) > oneWeekAgo
      );
      
      dispatch({
        type: ActionTypes.SET_NOTIFICATIONS,
        payload: recentNotifications,
      });
    }, [state.notifications]),

    // Dupliquer une notification (pour retry par exemple)
    duplicateNotification: useCallback((id) => {
      const originalNotification = state.notifications.find(n => n.id === id);
      if (originalNotification) {
        const { id: _, timestamp: __, ...notificationData } = originalNotification;
        actions.addNotification({
          ...notificationData,
          title: `[RETRY] ${notificationData.title}`,
        });
      }
    }, [state.notifications]),
  };

  // Nettoyage automatique des anciennes notifications (tous les jours)
  useEffect(() => {
    const interval = setInterval(() => {
      actions.cleanupOldNotifications();
    }, 24 * 60 * 60 * 1000); // 24 heures

    return () => clearInterval(interval);
  }, [actions.cleanupOldNotifications]);

  // Gestion des notifications du navigateur (si permission accordée)
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'granted') {
      // Écouter les nouvelles notifications importantes
      state.notifications
        .filter(n => 
          !n.read && 
          (n.type === NOTIFICATION_TYPE.ERROR || n.category === 'review') &&
          new Date(n.timestamp) > new Date(Date.now() - 1000) // Dernière seconde
        )
        .forEach(notification => {
          new Notification(notification.title, {
            body: notification.message,
            icon: '/favicon.ico',
            tag: notification.id.toString(),
          });
        });
    }
  }, [state.notifications]);

  // Valeur du contexte
  const value = {
    ...state,
    ...actions,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

// Hook personnalisé
export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationContextProvider');
  }
  return context;
};

// Hooks spécialisés pour différents types de notifications
export const useSuccessNotification = () => {
  const { success } = useNotification();
  return success;
};

export const useErrorNotification = () => {
  const { error } = useNotification();
  return error;
};

export const useWarningNotification = () => {
  const { warning } = useNotification();
  return warning;
};

export const useInfoNotification = () => {
  const { info } = useNotification();
  return info;
};

export const useReviewNotifications = () => {
  const { reviewNotification, getNotificationsByCategory } = useNotification();
  return {
    addReviewNotification: reviewNotification,
    getReviewNotifications: () => getNotificationsByCategory('review'),
  };
};

export const useUploadNotifications = () => {
  const { uploadNotification, getNotificationsByCategory } = useNotification();
  return {
    addUploadNotification: uploadNotification,
    getUploadNotifications: () => getNotificationsByCategory('upload'),
  };
};