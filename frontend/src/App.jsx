import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import { Helmet } from 'react-helmet';

// Contexts
import { AppContextProvider } from './context/AppContext';
import { ReviewProvider } from './context/ReviewContext'; // Changé de ReviewContextProvider à ReviewProvider
import { NotificationContextProvider } from './context/NotificationContext';

// Components
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';
import Footer from './components/common/Footer';
import ErrorBoundary from './components/common/ErrorBoundary';

// Pages
import Home from './pages/Home';
import Upload from './pages/Upload';
import Reviews from './pages/Reviews';
import ReviewDetail from './pages/ReviewDetail';
import Analytics from './pages/Analytics';
import History from './pages/History';
import Settings from './pages/Settings';

// Styles
import './App.css';

// Configure React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <AppContextProvider>
          <NotificationContextProvider>
            <ReviewProvider>
              <Router>
                <div className="min-h-screen bg-gray-50 dark:bg-dark-900">
                  <Helmet>
                    <title>AI Code Review Assistant</title>
                    <meta name="description" content="Assistant de révision de code alimenté par l'IA pour améliorer la qualité de votre code" />
                    <meta name="keywords" content="code review, AI, OpenAI, FastAPI, React, analyse de code" />
                    <link rel="preconnect" href="https://fonts.googleapis.com" />
                    <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="true" />
                    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@300;400;500&display=swap" rel="stylesheet" />
                  </Helmet>
                  
                  {/* Layout Principal */}
                  <div className="flex flex-col lg:flex-row">
                    {/* Sidebar */}
                    <div className="lg:w-64 lg:fixed lg:inset-y-0 lg:z-50">
                      <Sidebar />
                    </div>
                    
                    {/* Contenu Principal */}
                    <div className="flex-1 lg:pl-64">
                      {/* Header */}
                      <Header />
                      
                      {/* Contenu des Pages */}
                      <main className="py-6">
                        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                          <Routes>
                            <Route path="/" element={<Home />} />
                            <Route path="/upload" element={<Upload />} />
                            <Route path="/reviews" element={<Reviews />} />
                            <Route path="/reviews/:id" element={<ReviewDetail />} />
                            <Route path="/analytics" element={<Analytics />} />
                            <Route path="/history" element={<History />} />
                            <Route path="/settings" element={<Settings />} />
                          </Routes>
                        </div>
                      </main>
                      
                      {/* Footer */}
                      <Footer />
                    </div>
                  </div>
                  
                  {/* Toast Notifications */}
                  <Toaster
                    position="top-right"
                    toastOptions={{
                      duration: 4000,
                      style: {
                        background: '#363636',
                        color: '#fff',
                      },
                      success: {
                        duration: 3000,
                        iconTheme: {
                          primary: '#22c55e',
                          secondary: '#fff',
                        },
                      },
                      error: {
                        duration: 5000,
                        iconTheme: {
                          primary: '#ef4444',
                          secondary: '#fff',
                        },
                      },
                    }}
                  />
                </div>
              </Router>
            </ReviewProvider>
          </NotificationContextProvider>
        </AppContextProvider>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}

export default App;