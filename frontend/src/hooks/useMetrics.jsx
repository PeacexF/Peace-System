import { useState, useEffect, useRef } from 'react';
import { apiService } from '../services/api';

export const useMetrics = (limit = 30) => {
  const [metrics, setMetrics] = useState([]);
  const [status, setStatus] = useState({ total_events: 0, status: 'offline' });
  const [error, setError] = useState(null);
  
  const lastData = useRef({ cpu: 0, ram: 0 });

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const [currStatus, history] = await Promise.all([
          apiService.getStatus(),
          apiService.getLatestMetrics(limit)
        ]);
        setStatus(currStatus);
        setMetrics(history);
        
        if (history.length > 0) {
          const last = history[history.length - 1];
          lastData.current = { cpu: last.cpu || 0, ram: last.ram || 0 };
        }
      } catch (err) {
        setError(`Failed to load initial data: ${err}`);
      }
    };

    loadHistory();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws`);

    socket.onmessage = (event) => {
      const rawEvent = JSON.parse(event.data);
      
      const timeLabel = new Date(rawEvent.timestamp * 1000).toLocaleTimeString();
      
      setMetrics((prev) => {
        const newDataPoint = {
          timestamp: timeLabel,
          cpu: rawEvent.source === 'cpu_collector' ? rawEvent.data.cpu_usage_percent : lastData.current.cpu,  // love those '?', actula good js feature
          ram: rawEvent.source === 'ram_collector' ? rawEvent.data.used_percent : lastData.current.ram,
        };

        lastData.current = { cpu: newDataPoint.cpu, ram: newDataPoint.ram };

        const updated = [...prev, newDataPoint];
        return updated.slice(-limit);
      });
    };

    socket.onopen = () => setStatus(prev => ({ ...prev, status: 'online' }));
    socket.onclose = () => setStatus(prev => ({ ...prev, status: 'offline' }));
    socket.onerror = () => setError("WebSocket connection error");

    return () => socket.close();
  }, [limit]);

  return { metrics, status, error };
};