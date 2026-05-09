import { useState, useEffect } from 'react';
import { apiService } from '../services/api';

export const useMetrics = (limit = 30, interval = 2000) => {
    const [metrics, setMetrics] = useState([]);
    const [status, setStatus] = useState({ total_events: 0, status: 'offline' });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const loadData = async () => {
            try {
                const [newStatus, newMetrics] = await Promise.all([
                    apiService.getStatus(),
                    apiService.getLatestMetrics(limit)
                ]);

                setStatus(newStatus);
                setMetrics(newMetrics);
                setError(null);
            } catch (err) {
                console.error("Failed to fetch metrics:", err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        loadData();

        const timer = setInterval(loadData, interval);

        return () => clearInterval(timer);
    }, [limit, interval]);

    return { metrics, status, loading, error };
};