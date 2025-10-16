// services/websocketService.js - WebSocket Service for Real-time Review Updates

const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8003';

/**
 * WebSocket Service for handling real-time review updates
 */
class WebSocketService {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
    this.isConnecting = false;
    this.isClosing = false;
    this.subscribers = new Map(); // reviewId -> Set of callbacks
    this.globalSubscribers = new Set(); // Callbacks for all events
    this.pingInterval = null;
    this.connectionPromise = null;
  }

  /**
   * Connect to WebSocket server
   */
connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return Promise.resolve();
    }

    if (this.isConnecting) {
      console.log('WebSocket connection already in progress');
      return this.connectionPromise;
    }

    this.isConnecting = true;
    this.connectionPromise = new Promise((resolve, reject) => {
      try {
        // ✅ FIXED: Use correct WebSocket endpoint path
        const wsUrl = `${WS_BASE_URL}/ws/reviews`;
        console.log('🔌 Connecting to WebSocket:', wsUrl);
        
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('✅ WebSocket connected successfully');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.startPingInterval();
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          this.isConnecting = false;
          reject(error);
        };

        this.ws.onclose = (event) => {
          console.log('🔌 WebSocket closed:', event.code, event.reason);
          this.isConnecting = false;
          this.stopPingInterval();
          
          // Auto-reconnect if not intentionally closed
          if (!this.isClosing && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`🔄 Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            setTimeout(() => this.connect(), this.reconnectDelay);
          }
        };

      } catch (error) {
        console.error('💥 Failed to create WebSocket connection:', error);
        this.isConnecting = false;
        reject(error);
      }
    });

    return this.connectionPromise;
  }


  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    this.isClosing = true;
    this.stopPingInterval();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.subscribers.clear();
    this.globalSubscribers.clear();
    this.reconnectAttempts = 0;
    this.isClosing = false;
    
    console.log('WebSocket disconnected');
  }

  /**
   * Send a message to the server
   */
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message);
    }
  }

  /**
   * Start ping interval to keep connection alive
   */
  startPingInterval() {
    this.stopPingInterval();
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 30000); // Ping every 30 seconds
  }

  /**
   * Stop ping interval
   */
  stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Handle incoming WebSocket messages
   */
  handleMessage(event) {
    try {
      const message = JSON.parse(event.data);
      console.log('WebSocket message received:', message);

      // Handle different message types
      switch (message.type) {
        case 'connection_established':
          console.log('Connection established:', message.message);
          break;

        case 'pong':
          // Ping response - connection is alive
          break;

        case 'subscribed':
          console.log('Subscribed to review:', message.review_id);
          break;

        case 'unsubscribed':
          console.log('Unsubscribed from review:', message.review_id);
          break;

        case 'review_started':
          this.notifySubscribers(message.review_id, 'started', message.data);
          break;

        case 'review_progress':
          this.notifySubscribers(message.review_id, 'progress', message.data);
          break;

        case 'review_completed':
          this.notifySubscribers(message.review_id, 'completed', message.data);
          break;

        case 'review_failed':
          this.notifySubscribers(message.review_id, 'failed', message.data);
          break;

        case 'error':
          console.error('Server error:', message.message);
          break;

        default:
          console.log('Unknown message type:', message.type);
      }

      // Notify global subscribers
      this.globalSubscribers.forEach(callback => {
        try {
          callback(message);
        } catch (error) {
          console.error('Error in global subscriber callback:', error);
        }
      });

    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  /**
   * Notify subscribers of a specific review
   */
  notifySubscribers(reviewId, eventType, data) {
    const callbacks = this.subscribers.get(reviewId);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback({
            reviewId,
            eventType,
            data,
            timestamp: new Date()
          });
        } catch (error) {
          console.error('Error in subscriber callback:', error);
        }
      });
    }
  }

  /**
   * Subscribe to updates for a specific review
   */
  subscribeToReview(reviewId, callback) {
    if (!this.subscribers.has(reviewId)) {
      this.subscribers.set(reviewId, new Set());
    }
    
    this.subscribers.get(reviewId).add(callback);
    
    // Send subscription message to server
    this.send({
      type: 'subscribe',
      review_id: reviewId
    });

    // Return unsubscribe function
    return () => this.unsubscribeFromReview(reviewId, callback);
  }

  /**
   * Unsubscribe from updates for a specific review
   */
  unsubscribeFromReview(reviewId, callback) {
    const callbacks = this.subscribers.get(reviewId);
    if (callbacks) {
      callbacks.delete(callback);
      
      // If no more callbacks for this review, unsubscribe from server
      if (callbacks.size === 0) {
        this.subscribers.delete(reviewId);
        this.send({
          type: 'unsubscribe',
          review_id: reviewId
        });
      }
    }
  }

  /**
   * Subscribe to all WebSocket messages (global)
   */
  subscribeGlobal(callback) {
    this.globalSubscribers.add(callback);
    
    // Return unsubscribe function
    return () => this.globalSubscribers.delete(callback);
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Get current connection state
   */
  getConnectionState() {
    if (!this.ws) return 'disconnected';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'closing';
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'unknown';
    }
  }
}

// Create and export singleton instance
const websocketService = new WebSocketService();
export default websocketService;


/**
 * React Hook for using WebSocket with a specific review
 */
export const useReviewWebSocket = (reviewId) => {
  const [status, setStatus] = React.useState('idle');
  const [data, setData] = React.useState(null);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (!reviewId) return;

    // Connect to WebSocket
    websocketService.connect().catch(err => {
      console.error('Failed to connect to WebSocket:', err);
      setError(err);
    });

    // Subscribe to review updates
    const unsubscribe = websocketService.subscribeToReview(reviewId, (message) => {
      setStatus(message.eventType);
      setData(message.data);
      
      if (message.eventType === 'failed') {
        setError(message.data.error);
      }
    });

    // Cleanup on unmount
    return () => {
      unsubscribe();
    };
  }, [reviewId]);

  return { status, data, error, isConnected: websocketService.isConnected() };
};


/**
 * React Hook for global WebSocket connection
 */
export const useGlobalWebSocket = () => {
  const [connected, setConnected] = React.useState(false);
  const [messages, setMessages] = React.useState([]);

  React.useEffect(() => {
    // Connect to WebSocket
    websocketService.connect()
      .then(() => setConnected(true))
      .catch(err => {
        console.error('Failed to connect to WebSocket:', err);
        setConnected(false);
      });

    // Subscribe to all messages
    const unsubscribe = websocketService.subscribeGlobal((message) => {
      setMessages(prev => [...prev, message]);
    });

    // Update connection status
    const checkConnection = setInterval(() => {
      setConnected(websocketService.isConnected());
    }, 5000);

    // Cleanup on unmount
    return () => {
      unsubscribe();
      clearInterval(checkConnection);
    };
  }, []);

  return { 
    connected, 
    messages,
    connectionState: websocketService.getConnectionState()
  };
};