// pages/Upload.jsx - COMPLETE WITH REAL API
import React, { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CloudArrowUpIcon,
  DocumentTextIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

import reviewService from '../services/reviewService';

const Upload = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  // State
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  
  // Optional metadata
  const [metadata, setMetadata] = useState({
    author_email: '',
    description: '',
    language: ''
  });

  // File validation
  const ALLOWED_EXTENSIONS = [
    '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h',
    '.go', '.rs', '.php', '.rb', '.html', '.css', '.scss', '.json'
  ];
  const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
  const MAX_FILES = 10;

  const validateFile = (file) => {
    const errors = [];
    const extension = '.' + file.name.split('.').pop().toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      errors.push(`Type de fichier non supporté: ${extension}`);
    }

    if (file.size > MAX_FILE_SIZE) {
      errors.push(`Fichier trop volumineux (max 5MB): ${(file.size / 1024 / 1024).toFixed(2)}MB`);
    }

    if (file.size === 0) {
      errors.push('Fichier vide');
    }

    return errors;
  };

  const handleFiles = (newFiles) => {
    setError(null);
    setSuccess(null);

    const fileArray = Array.from(newFiles);
    
    // Check total count
    if (files.length + fileArray.length > MAX_FILES) {
      setError(`Vous ne pouvez télécharger que ${MAX_FILES} fichiers maximum`);
      return;
    }

    // Validate and add files
    const validFiles = [];
    const errors = [];

    fileArray.forEach(file => {
      const fileErrors = validateFile(file);
      
      if (fileErrors.length === 0) {
        // Check for duplicates
        if (!files.some(f => f.name === file.name)) {
          validFiles.push({
            file,
            name: file.name,
            size: file.size,
            type: file.type,
            extension: '.' + file.name.split('.').pop().toLowerCase(),
            id: `${file.name}-${Date.now()}-${Math.random()}`
          });
        } else {
          errors.push(`Fichier déjà ajouté: ${file.name}`);
        }
      } else {
        errors.push(...fileErrors.map(err => `${file.name}: ${err}`));
      }
    });

    if (errors.length > 0) {
      setError(errors.join('\n'));
    }

    if (validFiles.length > 0) {
      setFiles(prev => [...prev, ...validFiles]);
    }
  };

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  }, [files]);

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const removeFile = (fileId) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
    setError(null);
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Veuillez sélectionner au moins un fichier');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);
    setUploadProgress(0);

    try {
      // Create FormData
      const formData = new FormData();
      
      files.forEach(fileObj => {
        formData.append('files', fileObj.file);
      });

      // Add optional metadata
      if (metadata.author_email) {
        formData.append('author_email', metadata.author_email);
      }
      if (metadata.description) {
        formData.append('description', metadata.description);
      }
      if (metadata.language) {
        formData.append('language', metadata.language);
      }

      console.log('Uploading files:', files.map(f => f.name));

      // Simulate progress (since we can't track actual progress easily)
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 300);

      // Upload files
      const result = await reviewService.uploadFiles(formData);

      clearInterval(progressInterval);
      setUploadProgress(100);

      console.log('Upload successful:', result);

      setSuccess({
        message: 'Fichiers téléchargés avec succès !',
        upload_id: result.upload_id,
        review_id: result.review_id,
        file_count: result.file_count
      });

      // Clear files after 2 seconds and redirect
      setTimeout(() => {
        if (result.review_id) {
          navigate(`/reviews/${result.review_id}`);
        } else {
          navigate('/reviews');
        }
      }, 2000);

    } catch (err) {
      console.error('Upload error:', err);
      setError(err.message || 'Échec du téléchargement. Veuillez réessayer.');
      setUploadProgress(0);
    } finally {
      setUploading(false);
    }
  };

  const handleReset = () => {
    setFiles([]);
    setError(null);
    setSuccess(null);
    setUploadProgress(0);
    setMetadata({
      author_email: '',
      description: '',
      language: ''
    });
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const getTotalSize = () => {
    return files.reduce((sum, f) => sum + f.size, 0);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="px-4 py-5 sm:px-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Télécharger des fichiers
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Envoyez vos fichiers de code pour une révision IA complète
          </p>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-400 mr-3 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-300">
                Erreur de téléchargement
              </h3>
              <div className="mt-2 text-sm text-red-700 dark:text-red-400 whitespace-pre-line">
                {error}
              </div>
            </div>
            <button
              onClick={() => setError(null)}
              className="flex-shrink-0 ml-3 text-red-400 hover:text-red-600"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}

      {/* Success Alert */}
      {success && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="flex">
            <CheckCircleIcon className="h-5 w-5 text-green-400 mr-3 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-green-800 dark:text-green-300">
                Téléchargement réussi !
              </h3>
              <div className="mt-2 text-sm text-green-700 dark:text-green-400">
                {success.message}
                <br />
                {success.file_count} fichier(s) en cours de traitement...
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Area */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          {/* Drag and Drop Zone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-300 dark:border-gray-600'
            }`}
          >
            <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
            <div className="mt-4">
              <p className="text-lg font-medium text-gray-900 dark:text-white">
                Glissez-déposez vos fichiers ici
              </p>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                ou
              </p>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileInput}
                accept={ALLOWED_EXTENSIONS.join(',')}
                className="hidden"
                id="file-upload"
                disabled={uploading}
              />
              <label
                htmlFor="file-upload"
                className="mt-2 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 cursor-pointer disabled:opacity-50"
              >
                Parcourir les fichiers
              </label>
            </div>
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              {ALLOWED_EXTENSIONS.join(', ')} (max {MAX_FILES} fichiers, 5MB chacun)
            </p>
          </div>

          {/* Optional Metadata */}
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Email (optionnel)
              </label>
              <input
                type="email"
                value={metadata.author_email}
                onChange={(e) => setMetadata(prev => ({ ...prev, author_email: e.target.value }))}
                placeholder="votre@email.com"
                className="block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                disabled={uploading}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Langage principal (optionnel)
              </label>
              <select
                value={metadata.language}
                onChange={(e) => setMetadata(prev => ({ ...prev, language: e.target.value }))}
                className="block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                disabled={uploading}
              >
                <option value="">Sélectionner...</option>
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="typescript">TypeScript</option>
                <option value="java">Java</option>
                <option value="cpp">C++</option>
                <option value="go">Go</option>
                <option value="rust">Rust</option>
                <option value="php">PHP</option>
                <option value="ruby">Ruby</option>
              </select>
            </div>
            
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Description (optionnel)
              </label>
              <textarea
                value={metadata.description}
                onChange={(e) => setMetadata(prev => ({ ...prev, description: e.target.value }))}
                rows={3}
                placeholder="Décrivez brièvement votre code..."
                className="block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                disabled={uploading}
              />
            </div>
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                Fichiers sélectionnés ({files.length})
              </h3>
              <ul className="space-y-2 max-h-60 overflow-y-auto">
                {files.map((file) => (
                  <li
                    key={file.id}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                  >
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      <DocumentTextIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {file.name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {formatFileSize(file.size)} • {file.extension}
                        </p>
                      </div>
                    </div>
                    {!uploading && (
                      <button
                        onClick={() => removeFile(file.id)}
                        className="ml-3 text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                      >
                        <XMarkIcon className="h-5 w-5" />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
              
              <div className="mt-3 flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
                <span>Total: {formatFileSize(getTotalSize())}</span>
                {!uploading && (
                  <button
                    onClick={handleReset}
                    className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                  >
                    Tout effacer
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Upload Progress */}
          {uploading && (
            <div className="mt-6">
              <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
                <span>Téléchargement en cours...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="mt-6 flex items-center justify-between">
            <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
              <InformationCircleIcon className="h-5 w-5" />
              <span>Les fichiers seront analysés automatiquement</span>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={handleReset}
                disabled={uploading || files.length === 0}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Réinitialiser
              </button>
              
              <button
                onClick={handleUpload}
                disabled={uploading || files.length === 0}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploading ? (
                  <>
                    <ArrowPathIcon className="animate-spin -ml-1 mr-2 h-4 w-4" />
                    Téléchargement...
                  </>
                ) : (
                  <>
                    <CloudArrowUpIcon className="-ml-1 mr-2 h-5 w-5" />
                    Télécharger
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <div className="bg-blue-50 dark:bg-blue-900/20 overflow-hidden shadow rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <CheckCircleIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                  Analyse automatique
                </h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  L'IA commence l'analyse immédiatement
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-green-50 dark:bg-green-900/20 overflow-hidden shadow rounded-lg border border-green-200 dark:border-green-800">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <CheckCircleIcon className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                  Suggestions détaillées
                </h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Recevez des recommandations précises
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-purple-50 dark:bg-purple-900/20 overflow-hidden shadow rounded-lg border border-purple-200 dark:border-purple-800">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <CheckCircleIcon className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                  Notifications en temps réel
                </h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Suivez la progression en direct
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;