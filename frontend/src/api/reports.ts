import api from './client'

export const reportsApi = {
  requestExport: () => api.post<{ job_id: string }>('/reports/export'),
  getStatus: (jobId: string) => api.get<{ status: string }>(`/reports/export/${jobId}/status`),
  downloadExport: (jobId: string) =>
    api.get(`/reports/export/${jobId}/download`, { responseType: 'blob' }),
}
