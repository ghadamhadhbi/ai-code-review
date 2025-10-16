// components/common/Sidebar.jsx - Composant de navigation latérale

import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
  HomeIcon,
  ArrowUpTrayIcon,
  DocumentTextIcon,
  ChartBarIcon,
  ClockIcon,
  Cog6ToothIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import { 
  HomeIcon as HomeIconSolid,
  ArrowUpTrayIcon as ArrowUpTrayIconSolid,
  DocumentTextIcon as DocumentTextIconSolid,
  ChartBarIcon as ChartBarIconSolid,
  ClockIcon as ClockIconSolid,
  Cog6ToothIcon as Cog6ToothIconSolid
} from '@heroicons/react/24/solid';
import { useSidebar } from '../../context/AppContext';
import { useReviewContext } from '../../context/ReviewContext';

const Sidebar = () => {
  const { sidebarOpen, setSidebarOpen } = useSidebar();
  const { stats } = useReviewContext();
  const location = useLocation();

  // Configuration de la navigation
  const navigationItems = [
    {
      name: 'Tableau de bord',
      href: '/',
      icon: HomeIcon,
      iconSolid: HomeIconSolid,
      description: 'Vue d\'ensemble des activités'
    },
    {
      name: 'Upload de fichiers',
      href: '/upload',
      icon: ArrowUpTrayIcon,
      iconSolid: ArrowUpTrayIconSolid,
      description: 'Télécharger des fichiers à analyser'
    },
    {
      name: 'Révisions',
      href: '/reviews',
      icon: DocumentTextIcon,
      iconSolid: DocumentTextIconSolid,
      description: 'Voir toutes les révisions de code',
      badge: stats?.pendingReviews || 0
    },
    {
      name: 'Analytiques',
      href: '/analytics',
      icon: ChartBarIcon,
      iconSolid: ChartBarIconSolid,
      description: 'Métriques et statistiques'
    },
    {
      name: 'Historique',
      href: '/history',
      icon: ClockIcon,
      iconSolid: ClockIconSolid,
      description: 'Historique des uploads et révisions'
    }
  ];

  const settingsItems = [
    {
      name: 'Paramètres',
      href: '/settings',
      icon: Cog6ToothIcon,
      iconSolid: Cog6ToothIconSolid,
      description: 'Configuration de l\'application'
    }
  ];

  const isActiveRoute = (href) => {
    if (href === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(href);
  };

  const NavItem = ({ item, onClick }) => {
    const active = isActiveRoute(item.href);
    const Icon = active ? item.iconSolid : item.icon;

    return (
      <NavLink
        to={item.href}
        onClick={onClick}
        className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-all duration-200 ${
          active
            ? 'bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300 border-r-2 border-primary-500'
            : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-dark-700 hover:text-gray-900 dark:hover:text-white'
        }`}
      >
        <Icon
          className={`mr-3 h-5 w-5 flex-shrink-0 transition-colors ${
            active 
              ? 'text-primary-600 dark:text-primary-400' 
              : 'text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300'
          }`}
        />
        <span className="truncate">{item.name}</span>
        {item.badge > 0 && (
          <span className="ml-auto inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-600 text-white min-w-[20px]">
            {item.badge > 99 ? '99+' : item.badge}
          </span>
        )}
      </NavLink>
    );
  };

  const SidebarContent = () => (
    <div className="flex h-full flex-col">
      {/* Header avec logo */}
      <div className="flex h-16 flex-shrink-0 items-center border-b border-gray-200 dark:border-dark-600 px-4">
        <div className="flex items-center">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600 text-white font-bold text-sm">
            AI
          </div>
          <span className="ml-2 text-lg font-bold text-gray-900 dark:text-white">
            Code Review
          </span>
        </div>
        
        {/* Bouton de fermeture (mobile) */}
        <button
          type="button"
          className="ml-auto -mr-2 flex h-10 w-10 items-center justify-center rounded-md p-2 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        >
          <XMarkIcon className="h-6 w-6 text-gray-600 dark:text-gray-400" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 bg-white dark:bg-dark-800 px-2 py-4 overflow-y-auto">
        {/* Navigation principale */}
        <div className="space-y-1">
          {navigationItems.map((item) => (
            <div key={item.name} className="group relative">
              <NavItem 
                item={item} 
                onClick={() => {
                  // Fermer la sidebar sur mobile après navigation
                  if (window.innerWidth < 1024) {
                    setSidebarOpen(false);
                  }
                }} 
              />
              
              {/* Tooltip pour la description */}
              <div className="opacity-0 group-hover:opacity-100 absolute left-full ml-2 px-2 py-1 bg-gray-900 dark:bg-dark-600 text-white text-xs rounded-md whitespace-nowrap z-50 transition-opacity duration-200 pointer-events-none top-1/2 transform -translate-y-1/2">
                {item.description}
                <div className="absolute top-1/2 left-0 transform -translate-y-1/2 -translate-x-1 border-4 border-transparent border-r-gray-900 dark:border-r-dark-600"></div>
              </div>
            </div>
          ))}
        </div>

        {/* Séparateur */}
        <div className="border-t border-gray-200 dark:border-dark-600 my-4"></div>

        {/* Navigation paramètres */}
        <div className="space-y-1">
          {settingsItems.map((item) => (
            <div key={item.name} className="group relative">
              <NavItem 
                item={item} 
                onClick={() => {
                  if (window.innerWidth < 1024) {
                    setSidebarOpen(false);
                  }
                }} 
              />
              
              <div className="opacity-0 group-hover:opacity-100 absolute left-full ml-2 px-2 py-1 bg-gray-900 dark:bg-dark-600 text-white text-xs rounded-md whitespace-nowrap z-50 transition-opacity duration-200 pointer-events-none top-1/2 transform -translate-y-1/2">
                {item.description}
                <div className="absolute top-1/2 left-0 transform -translate-y-1/2 -translate-x-1 border-4 border-transparent border-r-gray-900 dark:border-r-dark-600"></div>
              </div>
            </div>
          ))}
        </div>

        {/* Statistiques rapides */}
        <div className="mt-8 px-3">
          <div className="bg-gray-50 dark:bg-dark-700 rounded-lg p-3">
            <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
              Statistiques
            </h4>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600 dark:text-gray-300">Révisions actives</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {stats?.activeReviews || 0}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600 dark:text-gray-300">Terminées aujourd'hui</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {stats?.completedToday || 0}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600 dark:text-gray-300">Taux de succès</span>
                <span className="text-sm font-medium text-success-600 dark:text-success-400">
                  {stats?.successRate || 0}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Version de l'application */}
        <div className="mt-auto px-3 py-4 border-t border-gray-200 dark:border-dark-600">
          <div className="text-xs text-gray-400 dark:text-gray-500 text-center">
            Version 1.0.0
          </div>
        </div>
      </nav>
    </div>
  );

  return (
    <>
      {/* Sidebar Desktop */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex min-h-0 flex-1 flex-col bg-white dark:bg-dark-800 border-r border-gray-200 dark:border-dark-600">
          <SidebarContent />
        </div>
      </div>

      {/* Overlay Mobile */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        >
          <div className="fixed inset-0 bg-gray-600 bg-opacity-75 transition-opacity" />
        </div>
      )}

      {/* Sidebar Mobile */}
      <div className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col transform transition-transform duration-300 ease-in-out lg:hidden ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex min-h-0 flex-1 flex-col bg-white dark:bg-dark-800 shadow-xl">
          <SidebarContent />
        </div>
      </div>
    </>
  );
};

export default Sidebar;