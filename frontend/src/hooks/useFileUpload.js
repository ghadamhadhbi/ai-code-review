// hooks/useFileUpload.js - Hook pour la gestion des uploads de fichiers

import { useState, useCallback, useRef, useEffect } from 'react';
import uploadService from '../services/uploadService';
import { useNotification } from '../context/NotificationContext';
import { useReviewContext } from '../context/ReviewContext';
import { FILE_UPLOAD, SUCCESS_MESSAGES, ERROR_MESSAGES } from '../utils/constants';

export const useFileUpload = (options = {}) => {
  const {
    autoUpload = false,
    maxFiles = FILE_UPLOAD.MAX_FILES,
    maxSize = FILE_UPLOAD.MAX_SIZE,
    allowedExtensions = FILE_UPLOAD.ALLOWED_EXTENSIONS,
    onSuccess,
    onError,
    onProgress,
  } = options;

  const { addNotification } = useNotification();
  const { createReview } = useReviewContext();

  // États
  const [files, setFiles] = useState([]);
  const [validFiles, setValidFiles] = useState([]);
  const [invalidFiles, setInvalidFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const [uploadResults, setUploadResults] = useState([]);
  const [errors, setErrors] = useState([]);
  
  const uploadIdRef = useRef(null);
  const fileInputRef = useRef(null);

  // Validation des fichiers
  const validateFiles = useCallback((fileList) => {
    const validation = uploadService.validateFiles(fileList);
    
    setValidFiles(validation.validFiles);
    setInvalidFiles(validation.invalidFiles);
    setErrors(validation.errors);

    if (validation.errors.length > 0) {
      validation.errors.forEach(error => {
        addNotification({
          type: 'error',
          title: 'Erreur de validation',
          message: error,
        });
      });
    }

    return validation;
  }, [addNotification]);

  // Ajouter des fichiers
  const addFiles = useCallback((newFiles) => {
    const fileArray = Array.from(newFiles);
    const allFiles = [...files, ...fileArray];
    
    // Vérifier le nombre maximum de fichiers
    if (allFiles.length > maxFiles) {
      addNotification({
        type: 'warning',
        title: 'Trop de fichiers',
        message: `Vous ne pouvez télécharger que ${maxFiles} fichiers maximum`,
      });
      return false;
    }

    setFiles(allFiles);
    const validation = validateFiles(allFiles);

    // Upload automatique si activé et fichiers valides
    if (autoUpload && validation.isValid) {
      uploadFiles();
    }

    return validation.isValid;
  }, [files, maxFiles, validateFiles, autoUpload, addNotification]);

  // Supprimer un fichier
  const removeFile = useCallback((index) => {
    setFiles(prev => {
      const newFiles = prev.filter((_, i) => i !== index);
      validateFiles(newFiles);
      return newFiles;
    });
  }, [validateFiles]);

  // Supprimer tous les fichiers
  const clearFiles = useCallback(() => {
    setFiles([]);
    setValidFiles([]);
    setInvalidFiles([]);
    setErrors([]);
    setUploadProgress({});
    setUploadResults([]);
  }, []);

  // Gestion de la progression
  const handleProgress = useCallback((progress, uploadId) => {
    setUploadProgress(prev => ({
      ...prev,
      [uploadId]: progress
    }));
    
    if (onProgress) {
      onProgress(progress, uploadId);
    }
  }, [onProgress]);

  // Upload des fichiers
  const uploadFiles = useCallback(async (filesToUpload = null) => {
    const targetFiles = filesToUpload || files;
    
    if (targetFiles.length === 0) {
      addNotification({
        type: 'warning',
        title: 'Aucun fichier',
        message: 'Veuillez sélectionner au moins un fichier',
      });
      return;
    }

    // Valider avant l'upload
    const validation = validateFiles(targetFiles);
    if (!validation.isValid) {
      return;
    }

    setIsUploading(true);
    setUploadProgress({});
    setErrors([]);

    try {
      const result = await uploadService.uploadFiles(targetFiles, {
        onProgress: handleProgress,
        onSuccess: (uploadResult) => {
          setUploadResults(prev => [...prev, uploadResult]);
          
          addNotification({
            type: 'success',
            title: SUCCESS_MESSAGES.FILE_UPLOADED,
            message: `${uploadResult.files.length} fichier(s) téléchargé(s) avec succès`,
          });

          if (onSuccess) {
            onSuccess(uploadResult);
          }
        },
        onError: (error) => {
          setErrors(prev => [...prev, error]);
          
          addNotification({
            type: 'error',
            title: ERROR_MESSAGES.UPLOAD_FAILED,
            message: error.message,
          });

          if (onError) {
            onError(error);
          }
        },
        metadata: {
          source: 'web_upload',
          timestamp: new Date().toISOString(),
        }
      });

      uploadIdRef.current = result.uploadId;

      // Créer automatiquement une révision si l'upload réussit
      if (result.success && result.reviewId) {
        // La révision est déjà créée par le backend
        addNotification({
          type: 'info',
          title: 'Révision créée',
          message: 'La révision de votre code va commencer',
          link: `/reviews/${result.reviewId}`,
        });
      }

      return result;

    } catch (error) {
      setErrors(prev => [...prev, error]);
      
      addNotification({
        type: 'error',
        title: ERROR_MESSAGES.UPLOAD_FAILED,
        message: error.message || 'Erreur lors du téléchargement',
      });

      if (onError) {
        onError(error);
      }

      throw error;
    } finally {
      setIsUploading(false);
    }
  }, [files, validateFiles, handleProgress, addNotification, onSuccess, onError]);

  // Annuler l'upload
  const cancelUpload = useCallback(() => {
    if (uploadIdRef.current) {
      const cancelled = uploadService.cancelUpload(uploadIdRef.current);
      if (cancelled) {
        setIsUploading(false);
        setUploadProgress({});
        
        addNotification({
          type: 'info',
          title: 'Upload annulé',
          message: 'Le téléchargement a été annulé',
        });
      }
    }
  }, [addNotification]);

  // Retry upload
  const retryUpload = useCallback(() => {
    if (files.length > 0) {
      uploadFiles();
    }
  }, [files, uploadFiles]);

  // Ouvrir le sélecteur de fichiers
  const openFileSelector = useCallback(() => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, []);

  // Gestionnaire de sélection de fichiers
  const handleFileSelect = useCallback((event) => {
    const selectedFiles = event.target.files;
    if (selectedFiles && selectedFiles.length > 0) {
      addFiles(selectedFiles);
    }
    // Reset l'input pour permettre de sélectionner les mêmes fichiers
    if (event.target) {
      event.target.value = '';
    }
  }, [addFiles]);

  // Gestionnaire de drag & drop
  const handleDrop = useCallback((event) => {
    event.preventDefault();
    const droppedFiles = event.dataTransfer.files;
    if (droppedFiles && droppedFiles.length > 0) {
      addFiles(droppedFiles);
    }
  }, [addFiles]);

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
  }, []);

  const handleDragEnter = useCallback((event) => {
    event.preventDefault();
  }, []);

  // Calculer la progression globale
  const globalProgress = Object.values(uploadProgress).reduce((sum, progress) => {
    return sum + progress;
  }, 0) / Math.max(Object.keys(uploadProgress).length, 1);

  // Statistiques des fichiers
  const stats = {
    totalFiles: files.length,
    validFiles: validFiles.length,
    invalidFiles: invalidFiles.length,
    totalSize: validFiles.reduce((sum, file) => sum + file.size, 0),
    isValid: validFiles.length > 0 && invalidFiles.length === 0,
  };

  // Nettoyage à la destruction du composant
  useEffect(() => {
    return () => {
      if (uploadIdRef.current) {
        uploadService.cancelUpload(uploadIdRef.current);
      }
    };
  }, []);

  return {
    // États
    files,
    validFiles,
    invalidFiles,
    isUploading,
    uploadProgress,
    globalProgress,
    uploadResults,
    errors,
    stats,
    
    // Actions
    addFiles,
    removeFile,
    clearFiles,
    uploadFiles,
    cancelUpload,
    retryUpload,
    openFileSelector,
    
    // Gestionnaires d'événements
    handleFileSelect,
    handleDrop,
    handleDragOver,
    handleDragEnter,
    
    // Ref pour l'input file
    fileInputRef,
    
    // Utilitaires
    formatFileSize: uploadService.formatFileSize,
    getFileType: uploadService.getFileType,
    getFileExtension: uploadService.getFileExtension,
  };
};

// Hook spécialisé pour le drag & drop
export const useDragDrop = (onDrop, options = {}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isDragActive, setIsDragActive] = useState(false);
  const dragCounter = useRef(0);

  const handleDragEnter = useCallback((event) => {
    event.preventDefault();
    dragCounter.current++;
    setIsDragActive(true);
    
    if (event.dataTransfer.items && event.dataTransfer.items.length > 0) {
      setIsDragOver(true);
    }
  }, []);

  const handleDragLeave = useCallback((event) => {
    event.preventDefault();
    dragCounter.current--;
    
    if (dragCounter.current === 0) {
      setIsDragActive(false);
      setIsDragOver(false);
    }
  }, []);

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
  }, []);

  const handleDrop = useCallback((event) => {
    event.preventDefault();
    setIsDragOver(false);
    setIsDragActive(false);
    dragCounter.current = 0;
    
    if (onDrop && event.dataTransfer.files) {
      onDrop(event.dataTransfer.files);
    }
  }, [onDrop]);

  return {
    isDragOver,
    isDragActive,
    dragHandlers: {
      onDragEnter: handleDragEnter,
      onDragLeave: handleDragLeave,
      onDragOver: handleDragOver,
      onDrop: handleDrop,
    },
  };
};

// Hook pour la prévisualisation des fichiers
export const useFilePreview = () => {
  const [previews, setPreviews] = useState({});
  const [loading, setLoading] = useState({});

  const generatePreview = useCallback(async (file) => {
    if (previews[file.name]) {
      return previews[file.name];
    }

    setLoading(prev => ({ ...prev, [file.name]: true }));

    try {
      let preview = null;

      if (file.type.startsWith('image/')) {
        preview = URL.createObjectURL(file);
      } else if (file.type === 'text/plain' || file.name.match(/\.(js|jsx|ts|tsx|py|java|cpp|c|h|css|html|json|xml|md)$/i)) {
        const text = await file.text();
        preview = {
          type: 'text',
          content: text.substring(0, 1000),
          truncated: text.length > 1000,
          language: getLanguageFromExtension(file.name)
        };
      } else if (file.type === 'application/json') {
        const text = await file.text();
        try {
          const json = JSON.parse(text);
          preview = {
            type: 'json',
            content: JSON.stringify(json, null, 2).substring(0, 1000),
            truncated: text.length > 1000
          };
        } catch {
          preview = {
            type: 'text',
            content: text.substring(0, 1000),
            truncated: text.length > 1000
          };
        }
      } else {
        preview = {
          type: 'file',
          name: file.name,
          size: file.size,
          lastModified: file.lastModified
        };
      }

      setPreviews(prev => ({
        ...prev,
        [file.name]: preview
      }));

      return preview;
    } catch (error) {
      console.warn('Erreur lors de la génération de la prévisualisation:', error);
      const fallbackPreview = {
        type: 'error',
        message: 'Impossible de prévisualiser ce fichier'
      };
      
      setPreviews(prev => ({
        ...prev,
        [file.name]: fallbackPreview
      }));
      
      return fallbackPreview;
    } finally {
      setLoading(prev => ({ ...prev, [file.name]: false }));
    }
  }, [previews]);

  const clearPreviews = useCallback(() => {
    // Nettoyer les URLs créées pour les images
    Object.values(previews).forEach(preview => {
      if (typeof preview === 'string' && preview.startsWith('blob:')) {
        URL.revokeObjectURL(preview);
      }
    });
    
    setPreviews({});
    setLoading({});
  }, [previews]);

  const removePreview = useCallback((fileName) => {
    setPreviews(prev => {
      const preview = prev[fileName];
      if (typeof preview === 'string' && preview.startsWith('blob:')) {
        URL.revokeObjectURL(preview);
      }
      
      const { [fileName]: removed, ...rest } = prev;
      return rest;
    });
    
    setLoading(prev => {
      const { [fileName]: removed, ...rest } = prev;
      return rest;
    });
  }, []);

  // Nettoyage à la destruction du composant
  useEffect(() => {
    return () => {
      Object.values(previews).forEach(preview => {
        if (typeof preview === 'string' && preview.startsWith('blob:')) {
          URL.revokeObjectURL(preview);
        }
      });
    };
  }, []);

  return {
    previews,
    loading,
    generatePreview,
    clearPreviews,
    removePreview
  };
};

// Hook pour la compression des fichiers
export const useFileCompression = () => {
  const [isCompressing, setIsCompressing] = useState(false);
  const [compressionProgress, setCompressionProgress] = useState({});

  const compressImage = useCallback(async (file, options = {}) => {
    const {
      maxWidth = 1920,
      maxHeight = 1080,
      quality = 0.8,
      format = 'image/jpeg'
    } = options;

    if (!file.type.startsWith('image/')) {
      throw new Error('Ce fichier n\'est pas une image');
    }

    setIsCompressing(true);
    setCompressionProgress({ [file.name]: 0 });

    try {
      return new Promise((resolve, reject) => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();

        img.onload = () => {
          // Calculer les nouvelles dimensions
          let { width, height } = img;
          
          if (width > height) {
            if (width > maxWidth) {
              height = (height * maxWidth) / width;
              width = maxWidth;
            }
          } else {
            if (height > maxHeight) {
              width = (width * maxHeight) / height;
              height = maxHeight;
            }
          }

          canvas.width = width;
          canvas.height = height;

          // Dessiner l'image redimensionnée
          ctx.drawImage(img, 0, 0, width, height);
          
          setCompressionProgress({ [file.name]: 50 });

          // Convertir en blob
          canvas.toBlob((blob) => {
            if (blob) {
              setCompressionProgress({ [file.name]: 100 });
              
              // Créer un nouveau fichier avec le blob compressé
              const compressedFile = new File([blob], file.name, {
                type: format,
                lastModified: Date.now()
              });
              
              resolve({
                original: file,
                compressed: compressedFile,
                reduction: ((file.size - blob.size) / file.size * 100).toFixed(1)
              });
            } else {
              reject(new Error('Erreur lors de la compression'));
            }
          }, format, quality);
        };

        img.onerror = () => {
          reject(new Error('Erreur lors du chargement de l\'image'));
        };

        img.src = URL.createObjectURL(file);
      });
    } catch (error) {
      throw error;
    } finally {
      setIsCompressing(false);
      setCompressionProgress({});
    }
  }, []);

  return {
    isCompressing,
    compressionProgress,
    compressImage
  };
};

// Hook pour l'analyse des fichiers
export const useFileAnalysis = () => {
  const [analysisResults, setAnalysisResults] = useState({});
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const analyzeFile = useCallback(async (file) => {
    if (analysisResults[file.name]) {
      return analysisResults[file.name];
    }

    setIsAnalyzing(true);

    try {
      const analysis = {
        name: file.name,
        size: file.size,
        type: file.type,
        extension: getFileExtension(file.name),
        lastModified: new Date(file.lastModified),
        isCode: isCodeFile(file.name),
        language: getLanguageFromExtension(file.name),
        estimated_lines: 0,
        complexity_score: 0
      };

      // Analyse plus approfondie pour les fichiers de code
      if (analysis.isCode && file.size < 10 * 1024 * 1024) { // Limite à 10MB
        const content = await file.text();
        analysis.estimated_lines = content.split('\n').length;
        analysis.content_preview = content.substring(0, 500);
        
        // Score de complexité basique
        const complexityIndicators = [
          /function\s+\w+/g,
          /class\s+\w+/g,
          /if\s*\(/g,
          /for\s*\(/g,
          /while\s*\(/g,
          /switch\s*\(/g,
          /try\s*{/g,
          /catch\s*\(/g
        ];
        
        analysis.complexity_score = complexityIndicators.reduce((score, pattern) => {
          const matches = content.match(pattern);
          return score + (matches ? matches.length : 0);
        }, 0);
      }

      setAnalysisResults(prev => ({
        ...prev,
        [file.name]: analysis
      }));

      return analysis;
    } catch (error) {
      console.warn('Erreur lors de l\'analyse du fichier:', error);
      const errorAnalysis = {
        name: file.name,
        size: file.size,
        type: file.type,
        error: 'Impossible d\'analyser ce fichier'
      };
      
      setAnalysisResults(prev => ({
        ...prev,
        [file.name]: errorAnalysis
      }));
      
      return errorAnalysis;
    } finally {
      setIsAnalyzing(false);
    }
  }, [analysisResults]);

  const clearAnalysis = useCallback(() => {
    setAnalysisResults({});
  }, []);

  return {
    analysisResults,
    isAnalyzing,
    analyzeFile,
    clearAnalysis
  };
};

// Fonctions utilitaires
const getFileExtension = (fileName) => {
  return fileName.split('.').pop()?.toLowerCase() || '';
};

const getLanguageFromExtension = (fileName) => {
  const ext = getFileExtension(fileName);
  const languageMap = {
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    py: 'python',
    java: 'java',
    cpp: 'cpp',
    c: 'c',
    h: 'c',
    css: 'css',
    html: 'html',
    json: 'json',
    xml: 'xml',
    md: 'markdown',
    php: 'php',
    rb: 'ruby',
    go: 'go',
    rs: 'rust',
    swift: 'swift',
    kt: 'kotlin'
  };
  
  return languageMap[ext] || 'text';
};

const isCodeFile = (fileName) => {
  const codeExtensions = [
    'js', 'jsx', 'ts', 'tsx', 'py', 'java', 'cpp', 'c', 'h', 
    'css', 'html', 'json', 'xml', 'php', 'rb', 'go', 'rs', 
    'swift', 'kt', 'scala', 'dart', 'vue', 'svelte'
  ];
  
  const ext = getFileExtension(fileName);
  return codeExtensions.includes(ext);
};