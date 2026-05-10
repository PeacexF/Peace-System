import axios from 'axios';

const API_BASE = '/api';  // API for dashboard

export const apiService = {
  async getStatus() {
    try {
      const response = await axios.get(`${API_BASE}/status`);
      return response.data;
    } catch (error) {
      console.error("Status check failed", error);
      return { total_events: 0, status: 'offline' };
    }
  },

  async getLatestMetrics(limit = 30) {
    try {
      const response = await axios.get(`${API_BASE}/metrics/latest`, {
        params: { limit: limit * 10 }
      });

      const rawData = response.data || [];
      
      const sortedData = [...rawData].sort((a, b) => a.timestamp - b.timestamp);

      const grouped = {};
      let lastCpu = 0;
      let lastRam = 0;

      sortedData.forEach((item) => {
        if (!item || !item.timestamp) return;

        const timestampKey = Math.floor(item.timestamp);
        const timeLabel = new Date(timestampKey * 1000).toLocaleTimeString();

        if (!grouped[timestampKey]) {
          grouped[timestampKey] = {
            timestamp: timeLabel,
            raw_time: timestampKey,
            cpu: lastCpu,
            ram: lastRam  
          };
        }

        if (item.source === 'cpu_collector' && item.data) {
          const val = Number(item.data.cpu_usage_percent);
          if (!isNaN(val)) {
            grouped[timestampKey].cpu = val;
            lastCpu = val;
          }
        } else if (item.source === 'ram_collector' && item.data) {
          const val = Number(item.data.used_percent);
          if (!isNaN(val)) {
            grouped[timestampKey].ram = val;
            lastRam = val;
          }
        }
      });

      return Object.values(grouped)
        .sort((a, b) => a.raw_time - b.raw_time)
        .slice(-limit);

    } catch (error) {
      console.error("Metrics fetch failed", error);
      throw error;
    }
  }
};