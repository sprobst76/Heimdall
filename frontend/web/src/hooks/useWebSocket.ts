import { useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface WebSocketMessage {
  type: string;
  keys?: string[][];
  event?: string;
  [key: string]: unknown;
}

export function useDashboardWebSocket() {
  const queryClient = useQueryClient();
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const reconnectDelayRef = useRef(1000);
  const mountedRef = useRef(true);
  const shouldReconnectRef = useRef(true);

  const connect = useCallback(() => {
    const token = localStorage.getItem('access_token');
    if (!token || !mountedRef.current) return;

    // Build WebSocket URL from current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/portal/ws`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        // Send JWT token as first message for authentication
        ws.send(token);
      };

      ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);

          if (data.type === 'auth_ok') {
            setIsConnected(true);
            reconnectDelayRef.current = 1000; // Reset backoff on success
          } else if (data.type === 'auth_error') {
            // Token invalid, don't reconnect
            shouldReconnectRef.current = false;
            ws.close();
          } else if (data.type === 'invalidate' && data.keys) {
            // Invalidate TanStack Query cache for each key
            for (const key of data.keys) {
              queryClient.invalidateQueries({ queryKey: key });
            }
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;

        // Reconnect with exponential backoff
        if (mountedRef.current && shouldReconnectRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 30000);
            connect();
          }, reconnectDelayRef.current);
        }
      };

      ws.onerror = () => {
        // onclose will fire after onerror, handling reconnection
      };
    } catch {
      // WebSocket constructor can throw in some environments
    }
  }, [queryClient]);

  useEffect(() => {
    mountedRef.current = true;
    shouldReconnectRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { isConnected };
}
