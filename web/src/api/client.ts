// API client that toggles between live and mocks based on the VITE_MODE env variable

// Using import.meta.env for Vite environment variables
const USE_LIVE_API = import.meta.env.MODE === 'live';
const API_BASE_URL = 'http://localhost:8000';

async function fetchLive(endpoint: string, options?: RequestInit) {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  return response.json();
}

export const apiClient = {
  getNetwork: async () => {
    if (USE_LIVE_API) {
      return fetchLive('/api/network');
    }
    const module = await import('../mocks/network.json');
    return module.default;
  },

  getAtRisk: async (limit: number = 10) => {
    if (USE_LIVE_API) {
      return fetchLive(`/api/at-risk?limit=${limit}`);
    }
    const module = await import('../mocks/at-risk.json');
    return module.default;
  },

  simulate: async (scenario: any) => {
    if (USE_LIVE_API) {
      return fetchLive('/api/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario }),
      });
    }
    const module = await import('../mocks/simulate.json');
    return module.default;
  },

  intervene: async (baseline_scenario: any, interventions: any[]) => {
    if (USE_LIVE_API) {
      return fetchLive('/api/intervene', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ baseline_scenario, interventions }),
      });
    }
    const module = await import('../mocks/intervene.json');
    return module.default;
  }
};
