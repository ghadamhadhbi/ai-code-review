// services/uploadService.js - Service de téléchargement de fichiers

import { apiUtils } from './api';
import { API_ENDPOINTS, FILE_UPLOAD, ERROR_MESSAGES, SUCCESS_MESSAGES } from '../utils/constants';

class UploadService {
  constructor() {
    this.activeUploads = new Map();
  }

  /**
   * Valider un fichier avant l'upload
   * @param {File} file - Fichier à valider
   * @returns {Object} - Résultat de la validation
   */
  validateFile(file) {
    const errors = [];

    // Vérifier la taille
    if (file.size > FILE_UPLOAD.MAX_SIZE) {
      errors.push(`Le fichier "${file.name}" dépasse la taille maximale de ${FILE_UPLOAD.MAX_SIZE / (1024 * 1024)}MB`);
    }

    // Vérifier l'extension
    const extension = '.' + file.name.split('.').pop().toLowerCase();
    if (!FILE_UPLOAD.ALLOWED_EXTENSIONS.includes(extension)) {
      errors.push(`Le fichier "${file.name}" a un type non supporté (${extension})`);
    }

    // Vérifier que ce n'est pas un dossier
    if (file.size === 0 && file.type === '') {
      errors.push(`"${file.name}" semble être un dossier, veuillez sélectionner des fichiers`);
    }

    return {
      isValid: errors.length === 0,
      errors,
      file: {
        name: file.name,
        size: file.size,
        type: file.type,
        extension,
        lastModified: file.lastModified,
      }
    };
  }

  /**
   * Valider une liste de fichiers
   * @param {FileList|File[]} files - Liste des fichiers
   * @returns {Object} - Résultat de la validation
   */
  validateFiles(files) {
    const fileArray = Array.from(files);
    const validFiles = [];
    const invalidFiles = [];
    const allErrors = [];

    // Vérifier le nombre de fichiers
    if (fileArray.length > FILE_UPLOAD.MAX_FILES) {
      allErrors.push(`Vous ne pouvez télécharger que ${FILE_UPLOAD.MAX_FILES} fichiers maximum`);
      return {
        isValid: false,
        errors: allErrors,
        validFiles: [],
        invalidFiles: fileArray.map(f => ({ file: f, errors: ['Trop de fichiers'] }))
      };
    }

    // Valider chaque fichier
    fileArray.forEach(file => {
      const validation = this.validateFile(file);
      if (validation.isValid) {
        validFiles.push(validation.file);
      } else {
        invalidFiles.push({
          file: validation.file,
          errors: validation.errors
        });
        allErrors.push(...validation.errors);
      }
    });

    return {
      isValid: invalidFiles.length === 0 && validFiles.length > 0,
      errors: allErrors,
      validFiles,
      invalidFiles
    };
  }

  /**
   * Télécharger des fichiers
   * @param {FileList|File[]} files - Fichiers à télécharger
   * @param {Object} options - Options d'upload
   * @returns {Promise} - Promesse avec le résultat de l'upload
   */
  async uploadFiles(files, options = {}) {
    const {
      onProgress = null,
      onFileProgress = null,
      onSuccess = null,
      onError = null,
      metadata = {}
    } = options;

    try {
      // Valider les fichiers
      const validation = this.validateFiles(files);
      if (!validation.isValid) {
        throw new Error(validation.errors.join('\n'));
      }

      // Créer FormData
      const formData = new FormData();
      
      // Ajouter les fichiers
      validation.validFiles.forEach((fileInfo, index) => {
        const originalFile = Array.from(files)[index];
        formData.append('files', originalFile);
      });

      // Ajouter les métadonnées
      formData.append('metadata', JSON.stringify({
        uploadedAt: new Date().toISOString(),
        fileCount: validation.validFiles.length,
        totalSize: validation.validFiles.reduce((sum, f) => sum + f.size, 0),
        ...metadata
      }));

      // Créer un token d'annulation
      const cancelToken = apiUtils.createCancelToken();
      const uploadId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      // Stocker l'upload actif
      this.activeUploads.set(uploadId, {
        cancelToken,
        files: validation.validFiles,
        startTime: Date.now()
      });

      // Fonction de progression globale
      const progressCallback = (progress) => {
        if (onProgress) onProgress(progress, uploadId);
        if (onFileProgress) {
          onFileProgress({
            uploadId,
            progress,
            files: validation.validFiles
          });
        }
      };

      // Effectuer l'upload
      const result = await apiUtils.upload(
        API_ENDPOINTS.UPLOAD,
        formData,
        progressCallback,
        { cancelToken: cancelToken.token }
      );

      // Nettoyer l'upload actif
      this.activeUploads.delete(uploadId);

      const uploadResult = {
        success: true,
        message: SUCCESS_MESSAGES.FILE_UPLOADED,
        uploadId,
        reviewId: result.review_id,
        files: result.files || validation.validFiles,
        metadata: result.metadata,
        estimatedTime: result.estimated_completion_time,
        ...result
      };

      if (onSuccess) onSuccess(uploadResult);
      return uploadResult;

    } catch (error) {
      const errorResult = {
        success: false,
        message: error.message || ERROR_MESSAGES.UPLOAD_FAILED,
        error: error
      };

      if (onError) onError(errorResult);
      throw errorResult;
    }
  }

  /**
   * Télécharger un seul fichier
   * @param {File} file - Fichier à télécharger
   * @param {Object} options - Options d'upload
   * @returns {Promise} - Promesse avec le résultat
   */
  async uploadFile(file, options = {}) {
    return this.uploadFiles([file], options);
  }

  /**
   * Annuler un upload
   * @param {string} uploadId - ID de l'upload à annuler
   */
  cancelUpload(uploadId) {
    const upload = this.activeUploads.get(uploadId);
    if (upload) {
      upload.cancelToken.cancel('Upload annulé par l\'utilisateur');
      this.activeUploads.delete(uploadId);
      return true;
    }
    return false;
  }

  /**
   * Obtenir le statut d'un upload actif
   * @param {string} uploadId - ID de l'upload
   * @returns {Object|null} - Statut de l'upload
   */
  getUploadStatus(uploadId) {
    return this.activeUploads.get(uploadId) || null;
  }

  /**
   * Obtenir tous les uploads actifs
   * @returns {Array} - Liste des uploads actifs
   */
  getActiveUploads() {
    return Array.from(this.activeUploads.entries()).map(([id, upload]) => ({
      id,
      ...upload,
      duration: Date.now() - upload.startTime
    }));
  }

  /**
   * Vérifier le statut du serveur pour les uploads
   * @returns {Promise<Object>} - Statut du serveur
   */
  async checkServerStatus() {
    try {
      const response = await apiUtils.get('/api/v1/upload/status');
      return {
        available: true,
        ...response
      };
    } catch (error) {
      return {
        available: false,
        error: error.message
      };
    }
  }

  /**
   * Obtenir l'historique des uploads
   * @param {Object} params - Paramètres de filtre
   * @returns {Promise<Object>} - Historique des uploads
   */
  async getUploadHistory(params = {}) {
    try {
      const response = await apiUtils.get('/api/v1/upload/history', { params });
      return response;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Supprimer un upload de l'historique
   * @param {string} uploadId - ID de l'upload à supprimer
   * @returns {Promise<Object>} - Résultat de la suppression
   */
  async deleteUpload(uploadId) {
    try {
      const response = await apiUtils.delete(`/api/v1/upload/${uploadId}`);
      return response;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Formater la taille d'un fichier
   * @param {number} bytes - Taille en bytes
   * @returns {string} - Taille formatée
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * Extraire l'extension d'un fichier
   * @param {string} filename - Nom du fichier
   * @returns {string} - Extension du fichier
   */
  getFileExtension(filename) {
    return '.' + filename.split('.').pop().toLowerCase();
  }

  /**
   * Déterminer le type de fichier basé sur l'extension
   * @param {string} filename - Nom du fichier
   * @returns {string} - Type de fichier
   */
  getFileType(filename) {
    const extension = this.getFileExtension(filename);
    
    const typeMap = {
      '.py': 'python',
      '.js': 'javascript',
      '.jsx': 'javascript',
      '.ts': 'typescript',
      '.tsx': 'typescript',
      '.java': 'java',
      '.cpp': 'cpp',
      '.c': 'c',
      '.h': 'c',
      '.go': 'go',
      '.rs': 'rust',
      '.php': 'php',
      '.rb': 'ruby',
      '.html': 'html',
      '.css': 'css',
      '.scss': 'scss',
      '.sass': 'sass',
      '.json': 'json',
      '.xml': 'xml',
      '.yaml': 'yaml',
      '.yml': 'yaml'
    };

    return typeMap[extension] || 'text';
  }

  /**
   * Nettoyer tous les uploads actifs (à utiliser lors du démontage du composant)
   */
  cleanup() {
    for (const [uploadId, upload] of this.activeUploads.entries()) {
      upload.cancelToken.cancel('Nettoyage de l\'application');
    }
    this.activeUploads.clear();
  }
}

// Créer une instance singleton
const uploadService = new UploadService();

export default uploadService;