// components/common/Header.jsx - Composant Header

import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Bars3Icon, 
  BellIcon, 
  MagnifyingGlassIcon,
  SunIcon,
  MoonIcon,
  Cog6ToothIcon,
  ChevronDownIcon
} from '@heroicons/react/24/outline';
import { useAppContext, useTheme } from '../../context/AppContext';
import { useNotification } from '../../context/NotificationContext';

const Header = () => {
  const { toggleSidebar, user } = useAppContext();
  const { theme, toggleTheme } = useTheme();
  const { notifications, unreadCount, markAsRead } = useNotification();
  
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  const notificationRef = useRef(null);
  const userMenuRef = useRef(null);

  // Fermer les menus quand on clique ailleurs
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (notificationRef.current && !notificationRef.current.contains(event.target)) {
        setShowNotifications(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setShowUserMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // Navigation vers la page de recherche avec le query
      console.log('Recherche:', searchQuery);
    }
  };

  const handleNotificationClick = (notification) => {
    markAsRead(notification.id);
    // Navigation vers l'élément concerné si applicable
    if (notification.link) {
      window.location.href = notification.link;
    }
  };

  return (
    <header className="bg-white dark:bg-dark-800 shadow-sm border-b border-gray-200 dark:border-dark-600 sticky top-0 z-40">
      <div className="mx-auto max-w-full px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Côté gauche - Menu hamburger et logo */}
          <div className="flex items-center">
            <button
              onClick={toggleSidebar}
              className="inline-flex items-center justify-center rounded-md p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-dark-700 hover:text-gray-900 dark:hover:text-white focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500 lg:hidden"
              aria-label="Ouvrir le menu"
            >
              <Bars3Icon className="h-6 w-6" />
            </button>
            
            {/* Logo et titre pour mobile */}
            <div className="ml-4 flex lg:ml-0">
              <Link to="/" className="flex items-center">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600 text-white font-bold text-sm">
                  AI
                </div>
                <span className="ml-2 text-xl font-bold text-gray-900 dark:text-white hidden sm:block">
                  Code Review
                </span>
              </Link>
            </div>
          </div>

          {/* Centre - Barre de recherche */}
          <div className="hidden md:flex flex-1 justify-center px-6 lg:px-8">
            <div className="w-full max-w-lg">
              <form onSubmit={handleSearch} className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Rechercher des révisions, fichiers..."
                  className="block w-full rounded-md border-gray-300 dark:border-dark-600 bg-white dark:bg-dark-700 pl-10 pr-3 py-2 text-sm placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </form>
            </div>
          </div>

          {/* Côté droit - Actions */}
          <div className="flex items-center space-x-4">
            {/* Recherche mobile */}
            <button className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white md:hidden">
              <MagnifyingGlassIcon className="h-6 w-6" />
            </button>

            {/* Basculement thème */}
            <button
              onClick={toggleTheme}
              className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white rounded-md hover:bg-gray-100 dark:hover:bg-dark-700 transition-colors"
              aria-label={theme === 'dark' ? 'Passer au thème clair' : 'Passer au thème sombre'}
            >
              {theme === 'dark' ? (
                <SunIcon className="h-5 w-5" />
              ) : (
                <MoonIcon className="h-5 w-5" />
              )}
            </button>

            {/* Notifications */}
            <div className="relative" ref={notificationRef}>
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white rounded-md hover:bg-gray-100 dark:hover:bg-dark-700 transition-colors relative"
                aria-label="Notifications"
              >
                <BellIcon className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-medium leading-4 text-white bg-danger-500 rounded-full min-w-[18px] h-[18px]">
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
              </button>

              {/* Menu déroulant des notifications */}
              {showNotifications && (
                <div className="absolute right-0 z-50 mt-2 w-80 origin-top-right rounded-md bg-white dark:bg-dark-800 py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                  <div className="px-4 py-2 border-b border-gray-200 dark:border-dark-600">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                      Notifications ({unreadCount})
                    </h3>
                  </div>
                  
                  <div className="max-h-80 overflow-y-auto">
                    {notifications.length > 0 ? (
                      notifications.slice(0, 5).map((notification) => (
                        <div
                          key={notification.id}
                          onClick={() => handleNotificationClick(notification)}
                          className={`px-4 py-3 hover:bg-gray-50 dark:hover:bg-dark-700 cursor-pointer border-l-4 ${
                            notification.read 
                              ? 'border-transparent' 
                              : 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                          }`}
                        >
                          <div className="flex items-start">
                            <div className="flex-1">
                              <p className={`text-sm ${notification.read ? 'text-gray-600 dark:text-gray-400' : 'text-gray-900 dark:text-white font-medium'}`}>
                                {notification.title}
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                {notification.message}
                              </p>
                              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                                {new Date(notification.timestamp).toLocaleString('fr-FR')}
                              </p>
                            </div>
                            {!notification.read && (
                              <div className="w-2 h-2 bg-primary-500 rounded-full mt-2 ml-2"></div>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="px-4 py-8 text-center">
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Aucune notification
                        </p>
                      </div>
                    )}
                  </div>
                  
                  {notifications.length > 5 && (
                    <div className="px-4 py-2 border-t border-gray-200 dark:border-dark-600">
                      <Link
                        to="/notifications"
                        className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-500 font-medium"
                      >
                        Voir toutes les notifications →
                      </Link>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Menu utilisateur */}
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center space-x-2 p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white rounded-md hover:bg-gray-100 dark:hover:bg-dark-700 transition-colors"
                aria-label="Menu utilisateur"
              >
                <div className="h-8 w-8 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                  <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
                    {user?.name?.charAt(0).toUpperCase() || 'U'}
                  </span>
                </div>
                <ChevronDownIcon className="h-4 w-4 hidden sm:block" />
              </button>

              {/* Menu déroulant utilisateur */}
              {showUserMenu && (
                <div className="absolute right-0 z-50 mt-2 w-48 origin-top-right rounded-md bg-white dark:bg-dark-800 py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                  {user && (
                    <div className="px-4 py-2 border-b border-gray-200 dark:border-dark-600">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {user.name || 'Utilisateur'}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {user.email || 'user@example.com'}
                      </p>
                    </div>
                  )}
                  
                  <Link
                    to="/settings"
                    className="flex items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-dark-700"
                    onClick={() => setShowUserMenu(false)}
                  >
                    <Cog6ToothIcon className="mr-3 h-4 w-4" />
                    Paramètres
                  </Link>
                  
                  <button
                    onClick={() => {
                      setShowUserMenu(false);
                      // Logique de déconnexion
                      console.log('Déconnexion');
                    }}
                    className="flex w-full items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-dark-700"
                  >
                    <svg
                      className="mr-3 h-4 w-4"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                    Se déconnecter
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;