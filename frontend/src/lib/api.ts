import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

export const snapshotAPI = {
  get: async () => {
    const res = await fetch(`${API_URL}/api/ops/snapshot`, { cache: 'no-store' });
    if (!res.ok) {
      throw new Error('Unable to load operational snapshot');
    }
    return { data: await res.json() };
  },
};

export const incidentsAPI = {
  list: (params?: { zone_id?: string; status?: string; limit?: number }) =>
    api.get('/api/incidents', { params }),
  create: (data: { report_text: string; source: string; zone_id?: string }) =>
    api.post('/api/incidents', data),
};

export const resourcesAPI = {
  list: (params?: { status?: string; type?: string; agency_id?: string }) =>
    api.get('/api/resources', { params }),
  patch: (id: string, data: { status?: string; current_zone_id?: string | null; eta_minutes?: number | null; reason?: string }) =>
    api.patch(`/api/resources/${id}`, data),
};

export const plansAPI = {
  generate: (data?: { trigger?: string }) => api.post('/api/plans/generate', data || {}),
  replan: (data?: { trigger?: string }) => api.post('/api/plans/replan', data || { trigger: 'manual_replan' }),
  latest: () => api.get('/api/plans/latest'),
  approve: (planId: string) => api.post(`/api/plans/${planId}/approve`),
  reject: (planId: string) => api.post(`/api/plans/${planId}/reject`),
};

export const coordinationAPI = {
  listTasks: (params?: { status?: string }) => api.get('/api/coordination/tasks', { params }),
  approveTask: (taskId: string) => api.post(`/api/coordination/tasks/${taskId}/approve`),
  rejectTask: (taskId: string) => api.post(`/api/coordination/tasks/${taskId}/reject`),
};

export const auditAPI = {
  list: (params?: { limit?: number }) => api.get('/api/audit', { params }),
};

export const simulationAPI = {
  loadDemo: () => api.post('/api/simulation/load-demo'),
  reset: () => api.post('/api/simulation/reset'),
  injectUrgent: () => api.post('/api/simulation/inject-urgent-report'),
  blockRoute: () => api.post('/api/simulation/block-route'),
  disableResource: () => api.post('/api/simulation/disable-resource'),
  increaseDemand: () => api.post('/api/simulation/increase-demand'),
  runReplan: () => api.post('/api/simulation/run-replan'),
};

export default api;
