// hooks/useWebSocket.js - FIXED WebSocket Hook
import { useEffect, useRef, useCallback, useState } from 'react';

// Use the same WebSocket base URL
const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8003';

const useWebSocket = (endpoint, options = {}) => {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [reconnectCount, setReconnectCount] = useState(0);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const shouldReconnectRef = useRef(true);

  // ✅ FIXED: Simple WebSocket URL construction
  const getWebSocketUrl = useCallback(() => {
    return `${WS_BASE_URL}${endpoint}`;
  }, [endpoint]);

  const connect = useCallback(() => {
    try {
      // Close existing connection if any
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }

      const wsUrl = getWebSocketUrl();
      console.log('🔌 Connecting to WebSocket:', wsUrl);
      
      const newSocket = new WebSocket(wsUrl);

      newSocket.onopen = (event) => {
        console.log('✅ WebSocket connected:', endpoint);
        setIsConnected(true);
        setReconnectCount(0);
        
        // Send initial ping
        try {
          newSocket.send(JSON.stringify({ 
            type: 'ping',
            timestamp: new Date().toISOString()
          }));
        } catch (err) {
          console.error('❌ Error sending initial ping:', err);
        }
        
        onOpen?.(event);
      };

      newSocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📨 WebSocket message received:', data);
          setLastMessage(data);
          onMessage?.(data);
        } catch (err) {
          console.error('❌ Error parsing WebSocket message:', err);
          setLastMessage({ type: 'text', data: event.data });
          onMessage?.(event.data);
        }
      };

      newSocket.onerror = (event) => {
        console.error('❌ WebSocket error:', endpoint, event);
        setIsConnected(false);
        onError?.(event);
      };

      newSocket.onclose = (event) => {
        console.log('🔌 WebSocket closed:', endpoint, {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        });
        setIsConnected(false);
        wsRef.current = null;
        onClose?.(event);

        // Attempt reconnection
        if (
          shouldReconnectRef.current && 
          reconnect && 
          reconnectCount < maxReconnectAttempts
        ) {
          console.log(`🔄 Reconnecting in ${reconnectInterval}ms (${reconnectCount + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectCount(prev => prev + 1);
            connect();
          }, reconnectInterval);
        } else if (reconnectCount >= maxReconnectAttempts) {
          console.error('❌ Max reconnection attempts reached');
        }
      };

      wsRef.current = newSocket;
    } catch (err) {
      console.error('❌ Error creating WebSocket:', err);
      setIsConnected(false);
    }
  }, [
    endpoint,
    getWebSocketUrl,
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnect,
    reconnectInterval,
    maxReconnectAttempts,
    reconnectCount
  ]);
  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        const data = typeof message === 'string' 
          ? message 
          : JSON.stringify(message);
        wsRef.current.send(data);
        return true;
      } catch (err) {
        console.error('❌ Error sending WebSocket message:', err);
        return false;
      }
    } else {
      console.warn('⚠️ WebSocket is not connected');
      return false;
    }
  }, []);

  // Subscribe to specific review updates
  const subscribeToReview = useCallback((reviewId) => {
    return sendMessage({
      type: 'subscribe',
      review_id: reviewId,
      timestamp: new Date().toISOString()
    });
  }, [sendMessage]);

  // Send ping to keep connection alive
  const ping = useCallback(() => {
    return sendMessage({
      type: 'ping',
      timestamp: new Date().toISOString()
    });
  }, [sendMessage]);

  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    // Set up ping interval to keep connection alive
    const pingInterval = setInterval(() => {
      if (isConnected) {
        ping();
      }
    }, 30000); // Ping every 30 seconds

    return () => {
      clearInterval(pingInterval);
      disconnect();
    };
  }, [endpoint]); // Only reconnect if endpoint changes

  return {
    isConnected,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect: connect,
    subscribeToReview,
    ping,
    reconnectCount,
  };
};


export default useWebSocket;