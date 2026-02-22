import api from './client'

export interface BalanceSnapshot {
  id: number
  storage_account_id: number
  date: string
  amount: number
}

export interface BalanceSnapshotCreate {
  storage_account_id: number
  date: string
  amount: number
}

export const balanceSnapshotsApi = {
  list: (params?: { storage_account_id?: number; date_from?: string; date_to?: string }) =>
    api.get<BalanceSnapshot[]>('/balance-snapshots/', { params }),
  create: (data: BalanceSnapshotCreate) => api.post<BalanceSnapshot>('/balance-snapshots/', data),
  update: (id: number, data: Partial<BalanceSnapshotCreate>) =>
    api.put<BalanceSnapshot>(`/balance-snapshots/${id}`, data),
  delete: (id: number) => api.delete(`/balance-snapshots/${id}`),
}
