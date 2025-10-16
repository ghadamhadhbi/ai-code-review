// components/common/ErrorBoundary.jsx - Composant ErrorBoundary

import React from 'react';
import {
  AlertTriangle,
  RefreshCw,
  Home,
  Bug,
  Copy,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Info,
  Mail,
  ArrowLeft
} from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      eventId: null,
      showDetails: false,
      isReporting: false,
      reportSent: false
    };
  }

  static getDerivedStateFromError(error) {
    // Met à jour l'état pour afficher l'UI d'erreur
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Capture les détails de l'erreur
    this.setState({
      error,
      errorInfo,
      eventId: this.generateEventId()
    });

    // Log l'erreur (vous pouvez intégrer votre service de logging ici)
    this.logError(error, errorInfo);

    // Notifier le service d'erreurs (Sentry, Bugsnag, etc.)
    if (typeof window !== 'undefined' && window.Sentry) {
      window.Sentry.captureException(error, {
        contexts: {
          react: {
            componentStack: errorInfo.componentStack
          }
        }
      });
    }
  }

  generateEventId = () => {
    return 'err_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  };

  logError = (error, errorInfo) => {
    const errorReport = {
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent,
      error: {
        message: error.message,
        stack: error.stack,
        name: error.name
      },
      errorInfo: {
        componentStack: errorInfo.componentStack
      },
      eventId: this.state.eventId
    };

    console.group('🚨 Error Boundary');
    console.error('Error:', error);
    console.error('Error Info:', errorInfo);
    console.error('Full Report:', errorReport);
    console.groupEnd();

    // Envoyer à votre service de logging
    if (process.env.NODE_ENV === 'production') {
      this.sendErrorReport(errorReport);
    }
  };

  sendErrorReport = async (errorReport) => {
    try {
      await fetch('/api/errors/report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(errorReport)
      });
    } catch (err) {
      console.warn('Failed to send error report:', err);
    }
  };

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      eventId: null,
      showDetails: false,
      reportSent: false
    });
    
    // Recharger la page si nécessaire
    if (this.props.fallbackType === 'reload') {
      window.location.reload();
    }
  };

  handleReportBug = async () => {
    this.setState({ isReporting: true });
    
    try {
      const bugReport = {
        title: `Error: ${this.state.error?.message || 'Unknown error'}`,
        description: this.getErrorDetails(),
        labels: ['bug', 'error-boundary'],
        eventId: this.state.eventId
      };

      // Simuler l'envoi du rapport (remplacer par votre API)
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      this.setState({ reportSent: true });
    } catch (err) {
      console.warn('Failed to report bug:', err);
    } finally {
      this.setState({ isReporting: false });
    }
  };

  copyErrorDetails = () => {
    const details = this.getErrorDetails();
    navigator.clipboard.writeText(details).then(() => {
      // Vous pourriez ajouter une notification toast ici
      console.log('Error details copied to clipboard');
    });
  };

  getErrorDetails = () => {
    const { error, errorInfo, eventId } = this.state;
    return `
Error ID: ${eventId}
Timestamp: ${new Date().toISOString()}
URL: ${window.location.href}
User Agent: ${navigator.userAgent}

Error Message: ${error?.message || 'Unknown error'}
Error Stack:
${error?.stack || 'No stack trace available'}

Component Stack:
${errorInfo?.componentStack || 'No component stack available'}
    `.trim();
  };

  toggleDetails = () => {
    this.setState(prevState => ({
      showDetails: !prevState.showDetails
    }));
  };

  render() {
    if (this.state.hasError) {
      const { error, eventId, showDetails, isReporting, reportSent } = this.state;
      const { 
        fallbackType = 'default',
        showRetry = true,
        showReportBug = true,
        customMessage,
        contactEmail = 'support@votredomaine.com'
      } = this.props;

      return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
          <div className="sm:mx-auto sm:w-full sm:max-w-lg">
            <div className="bg-white dark:bg-gray-800 py-8 px-4 shadow-lg sm:rounded-lg sm:px-10 border border-gray-200 dark:border-gray-700">
              {/* Icône d'erreur */}
              <div className="flex justify-center mb-6">
                <div className="h-16 w-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center">
                  <AlertTriangle className="h-8 w-8 text-red-600 dark:text-red-400" />
                </div>
              </div>

              {/* Titre et message */}
              <div className="text-center mb-8">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                  Oups ! Une erreur s'est produite
                </h1>
                
                <div className="text-gray-600 dark:text-gray-400 space-y-2">
                  <p>
                    {customMessage || 
                     "Nous nous excusons pour ce désagrément. Une erreur inattendue s'est produite dans l'application."
                    }
                  </p>
                  
                  {eventId && (
                    <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
                      <Info className="h-3 w-3 mr-1" />
                      ID d'erreur: {eventId}
                    </div>
                  )}
                </div>
              </div>

              {/* Actions principales */}
              <div className="space-y-4 mb-6">
                {showRetry && (
                  <button
                    onClick={this.handleRetry}
                    className="w-full flex justify-center items-center px-4 py-3 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Réessayer
                  </button>
                )}

                <div className="flex space-x-3">
                  <button
                    onClick={() => window.location.href = '/'}
                    className="flex-1 flex justify-center items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
                  >
                    <Home className="h-4 w-4 mr-2" />
                    Accueil
                  </button>

                  <button
                    onClick={() => window.history.back()}
                    className="flex-1 flex justify-center items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
                  >
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Retour
                  </button>
                </div>
              </div>

              {/* Rapport de bug */}
              {showReportBug && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
                  {!reportSent ? (
                    <div className="text-center">
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                        Aidez-nous à améliorer l'application en signalant cette erreur
                      </p>
                      
                      <div className="flex space-x-3">
                        <button
                          onClick={this.handleReportBug}
                          disabled={isReporting}
                          className="flex-1 flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                        >
                          {isReporting ? (
                            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                          ) : (
                            <Bug className="h-4 w-4 mr-2" />
                          )}
                          {isReporting ? 'Envoi...' : 'Signaler le bug'}
                        </button>

                        <button
                          onClick={this.copyErrorDetails}
                          className="flex justify-center items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
                        >
                          <Copy className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center">
                      <div className="inline-flex items-center px-4 py-2 rounded-md bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-200 text-sm font-medium">
                        <Bug className="h-4 w-4 mr-2" />
                        Rapport envoyé avec succès !
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                        Merci de nous aider à améliorer l'application
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Détails techniques */}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-6 mt-6">
                <button
                  onClick={this.toggleDetails}
                  className="w-full flex justify-between items-center text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors duration-200"
                >
                  <span>Détails techniques</span>
                  {showDetails ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </button>

                {showDetails && (
                  <div className="mt-4 p-4 bg-gray-100 dark:bg-gray-700 rounded-md">
                    <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words overflow-auto max-h-60">
                      {this.getErrorDetails()}
                    </pre>
                  </div>
                )}
              </div>

              {/* Contact */}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-6 mt-6 text-center">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                  Le problème persiste ?
                </p>
                <a
                  href={`mailto:${contactEmail}?subject=Erreur Application (${eventId})`}
                  className="inline-flex items-center text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors duration-200"
                >
                  <Mail className="h-4 w-4 mr-1" />
                  Contactez le support
                  <ExternalLink className="h-3 w-3 ml-1" />
                </a>
              </div>
            </div>
          </div>

          {/* Message d'encouragement */}
          <div className="text-center mt-8">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Nous travaillons constamment pour améliorer votre expérience
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Hook pour utiliser l'ErrorBoundary dans les composants fonctionnels
export const useErrorHandler = () => {
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  const captureError = React.useCallback((error) => {
    setError(error);
  }, []);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  return { captureError, resetError };
};

// Composant wrapper pour les pages critiques
export const CriticalErrorBoundary = ({ children, fallback }) => (
  <ErrorBoundary
    fallbackType="reload"
    customMessage="Une erreur critique s'est produite. La page va être rechargée automatiquement."
    showRetry={true}
    showReportBug={true}
  >
    {children}
  </ErrorBoundary>
);

// Composant wrapper pour les sections non-critiques
export const SectionErrorBoundary = ({ children, sectionName }) => (
  <ErrorBoundary
    fallbackType="default"
    customMessage={`Une erreur s'est produite dans la section ${sectionName}. Les autres fonctionnalités restent disponibles.`}
    showRetry={true}
    showReportBug={false}
  >
    {children}
  </ErrorBoundary>
);

export default ErrorBoundary;