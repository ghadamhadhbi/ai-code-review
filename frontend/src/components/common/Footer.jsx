// components/common/Footer.jsx - Composant Footer

import React from 'react';
import { Link } from 'react-router-dom';
import {
  Github,
  Twitter,
  Linkedin,
  Mail,
  Heart,
  Code,
  Shield,
  Zap,
  ExternalLink,
  BookOpen,
  MessageSquare,
  Users,
  Award
} from 'lucide-react';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  const footerLinks = {
    product: [
      { name: 'Fonctionnalités', href: '/features' },
      { name: 'Tarification', href: '/pricing' },
      { name: 'API Documentation', href: '/docs/api' },
      { name: 'Intégrations', href: '/integrations' },
      { name: 'Changelog', href: '/changelog' }
    ],
    resources: [
      { name: 'Guide de démarrage', href: '/docs/getting-started' },
      { name: 'Tutoriels', href: '/tutorials' },
      { name: 'Meilleures pratiques', href: '/best-practices' },
      { name: 'Exemples de code', href: '/examples' },
      { name: 'Blog', href: '/blog' }
    ],
    support: [
      { name: 'Centre d\'aide', href: '/help' },
      { name: 'Contact', href: '/contact' },
      { name: 'Communauté', href: '/community' },
      { name: 'Statut du service', href: '/status' },
      { name: 'Signaler un bug', href: '/bug-report' }
    ],
    company: [
      { name: 'À propos', href: '/about' },
      { name: 'Équipe', href: '/team' },
      { name: 'Carrières', href: '/careers' },
      { name: 'Presse', href: '/press' },
      { name: 'Partenaires', href: '/partners' }
    ],
    legal: [
      { name: 'Confidentialité', href: '/privacy' },
      { name: 'Conditions d\'utilisation', href: '/terms' },
      { name: 'Cookies', href: '/cookies' },
      { name: 'Sécurité', href: '/security' },
      { name: 'RGPD', href: '/gdpr' }
    ]
  };

  const socialLinks = [
    {
      name: 'GitHub',
      href: 'https://github.com/votre-org',
      icon: Github,
      color: 'hover:text-gray-900 dark:hover:text-white'
    },
    {
      name: 'Twitter',
      href: 'https://twitter.com/votre-compte',
      icon: Twitter,
      color: 'hover:text-blue-400'
    },
    {
      name: 'LinkedIn',
      href: 'https://linkedin.com/company/votre-entreprise',
      icon: Linkedin,
      color: 'hover:text-blue-600'
    },
    {
      name: 'Email',
      href: 'mailto:contact@votredomaine.com',
      icon: Mail,
      color: 'hover:text-red-500'
    }
  ];

  const features = [
    {
      icon: Code,
      title: 'Analyse intelligente',
      description: 'IA avancée pour une révision approfondie'
    },
    {
      icon: Zap,
      title: 'Rapide et efficace',
      description: 'Résultats en quelques minutes'
    },
    {
      icon: Shield,
      title: 'Sécurisé',
      description: 'Vos données sont protégées'
    }
  ];

  const stats = [
    { label: 'Révisions effectuées', value: '10,000+' },
    { label: 'Développeurs actifs', value: '2,500+' },
    { label: 'Langages supportés', value: '25+' },
    { label: 'Taux de satisfaction', value: '98%' }
  ];

  return (
    <footer className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
      {/* Section principale */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Statistiques */}
        <div className="py-12 border-b border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <div key={index} className="text-center">
                <div className="text-2xl md:text-3xl font-bold text-blue-600 dark:text-blue-400 mb-2">
                  {stat.value}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Liens principaux */}
        <div className="py-12 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-8">
          {/* Logo et description */}
          <div className="col-span-2 md:col-span-3 lg:col-span-2">
            <div className="flex items-center mb-4">
              <div className="h-8 w-8 bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">AI</span>
              </div>
              <h3 className="ml-2 text-lg font-semibold text-gray-900 dark:text-white">
                AI Code Review
              </h3>
            </div>
            <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-sm">
              Révision de code alimentée par l'IA pour améliorer la qualité, 
              la sécurité et la performance de vos projets.
            </p>
            
            {/* Fonctionnalités clés */}
            <div className="space-y-3">
              {features.map((feature, index) => (
                <div key={index} className="flex items-center">
                  <feature.icon className="h-4 w-4 text-blue-500 mr-3" />
                  <div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {feature.title}
                    </span>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {feature.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Produit */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
              Produit
            </h4>
            <ul className="space-y-3">
              {footerLinks.product.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors duration-200"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Ressources */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
              Ressources
            </h4>
            <ul className="space-y-3">
              {footerLinks.resources.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors duration-200"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Support */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
              Support
            </h4>
            <ul className="space-y-3">
              {footerLinks.support.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors duration-200"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Entreprise */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
              Entreprise
            </h4>
            <ul className="space-y-3">
              {footerLinks.company.map((link) => (
                <li key={link.name}>
                  <Link
                    to={link.href}
                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors duration-200"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Newsletter */}
        <div className="py-8 border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-md mx-auto text-center">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Restez informé
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Recevez les dernières mises à jour et conseils de révision de code
            </p>
            <form className="flex flex-col sm:flex-row gap-3">
              <input
                type="email"
                placeholder="Votre adresse email"
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
              />
              <button
                type="submit"
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors duration-200 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                S'abonner
              </button>
            </form>
          </div>
        </div>

        {/* Footer bottom */}
        <div className="py-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            {/* Copyright */}
            <div className="flex items-center text-sm text-gray-600 dark:text-gray-400 mb-4 md:mb-0">
              <span>© {currentYear} AI Code Review. Créé avec</span>
              <Heart className="h-4 w-4 text-red-500 mx-1" />
              <span>par l'équipe de développement</span>
            </div>

            {/* Liens légaux */}
            <div className="flex flex-wrap justify-center gap-6 mb-4 md:mb-0">
              {footerLinks.legal.map((link, index) => (
                <React.Fragment key={link.name}>
                  <Link
                    to={link.href}
                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors duration-200"
                  >
                    {link.name}
                  </Link>
                  {index < footerLinks.legal.length - 1 && (
                    <span className="text-gray-400">•</span>
                  )}
                </React.Fragment>
              ))}
            </div>

            {/* Réseaux sociaux */}
            <div className="flex space-x-4">
              {socialLinks.map((social) => (
                <a
                  key={social.name}
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`text-gray-400 ${social.color} transition-colors duration-200`}
                  aria-label={social.name}
                >
                  <social.icon className="h-5 w-5" />
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Badges de certification/sécurité */}
      <div className="bg-gray-50 dark:bg-gray-800 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap justify-center items-center gap-8">
            <div className="flex items-center text-xs text-gray-500 dark:text-gray-400">
              <Shield className="h-4 w-4 mr-2" />
              <span>Certifié SOC 2</span>
            </div>
            <div className="flex items-center text-xs text-gray-500 dark:text-gray-400">
              <Award className="h-4 w-4 mr-2" />
              <span>ISO 27001</span>
            </div>
            <div className="flex items-center text-xs text-gray-500 dark:text-gray-400">
              <Users className="h-4 w-4 mr-2" />
              <span>RGPD Conforme</span>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Hébergé en Europe • Chiffrement bout à bout
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;