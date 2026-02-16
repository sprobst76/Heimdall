import { createContext, useContext, useCallback, useState, useRef } from 'react';

export interface Notification {
  id: string;
  title: string;
  message: string;
  category: 'info' | 'quest' | 'tan' | 'device';
  timestamp: string;
}

interface NotificationContextValue {
  notifications: Notification[];
  addNotification: (n: Omit<Notification, 'id' | 'timestamp'>) => void;
  dismissNotification: (id: string) => void;
}

export const NotificationContext = createContext<NotificationContextValue>({
  notifications: [],
  addNotification: () => {},
  dismissNotification: () => {},
});

export function useNotificationState() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismissNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const addNotification = useCallback(
    (n: Omit<Notification, 'id' | 'timestamp'>) => {
      const id = crypto.randomUUID();
      const notification: Notification = {
        ...n,
        id,
        timestamp: new Date().toISOString(),
      };
      setNotifications((prev) => [...prev, notification]);

      // Auto-dismiss after 5 seconds
      const timer = setTimeout(() => {
        setNotifications((prev) => prev.filter((item) => item.id !== id));
        timersRef.current.delete(id);
      }, 5000);
      timersRef.current.set(id, timer);
    },
    [],
  );

  return { notifications, addNotification, dismissNotification };
}

export function useNotifications() {
  return useContext(NotificationContext);
}
