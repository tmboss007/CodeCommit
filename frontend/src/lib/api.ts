import axios from 'axios';
import type { Zone, Incident, Resource, Allocation, CoordinationTask, AuditEvent, AllocationPlan } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const zonesAPI = {
  list: () => api.get<Zone[]>('/api/zones'),
  get: (id: string) => api.get<Zone>(`/api/zones/${id}`),
};

export const incidentsAPI = {
  list: (params?: { zone_id?: string; status?: string; limit?: number }) =>
    api.get<Incident[]>('/api/incidents', { params }),
  get: (id: string) => api.get<Incident>(`/api/incidents/${id}`),
  create: (data: { report_text: string; source: string; source_reference?: string }) =>
    api.post<any>('/api/incidents', data),
};

export const resourcesAPI = {
  list: (params?: { status?: string; type?: string }) =>
    api.get<Resource[]>('/api/resources', { params }),
};

export const plansAPI = {
  generate: (data?: { trigger?: string; correlation_id?: string }) =>
    api.post<AllocationPlan>('/api/plans/generate', data || {}),
  replan: (data?: { trigger?: string; correlation_id?: string }) =>
    api.post<AllocationPlan>('/api/plans/replan', data || {}),
};

export const coordinationAPI = {
  listTasks: (params?: { status?: string; agency_id?: string }) =>
    api.get<CoordinationTask[]>('/api/coordination/tasks', { params }),
  approveTask: (taskId: string) =>
    api.post(`/api/coordination/tasks/${taskId}/approve`),
  rejectTask: (taskId: string) =>
    api.post(`/api/coordination/tasks/${taskId}/reject`),
};

export const auditAPI = {
  list: (params?: { event_type?: string; correlation_id?: string; limit?: number }) =>
    api.get<AuditEvent[]>('/api/audit', { params }),
};

export default api;
