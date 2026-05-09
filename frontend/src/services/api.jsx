import axios from 'axios';

const API_BASE = '/api';

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
        params: { limit: limit * 5 } 
      });

      const rawData = response.data;

      const grouped = rawData.reduce((acc, item) => {
        const key = Math.floor(item.timestamp); 
        const timeLabel = new Date(key * 1000).toLocaleTimeString();

        if (!acc[key]) {
          acc[key] = { timestamp: timeLabel, raw_time: key };
        }

        if (item.source === 'cpu_collector') {
          acc[key].cpu = item.data.cpu_usage_percent;
        } else if (item.source === 'ram_collector') {
          acc[key].ram = item.data.used_percent;
        }
        
        return acc;
      }, {});

      return Object.values(grouped)
        .sort((a, b) => a.raw_time - b.raw_time)
        .slice(-limit);

    } catch (error) {
      console.error("Metrics fetch failed", error);
      throw error;
    }
  }
};