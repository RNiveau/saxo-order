import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface AccountInfo {
  account_id: string;
  account_name: string;
  total_fund: number;
  available_fund: number;
}

export interface AccountsListResponse {
  accounts: AccountInfo[];
}

export interface AvailableFundResponse {
  account_id: string;
  account_name: string;
  total_fund: number;
  available_fund: number;
  open_orders_commitment: number;
  actual_available_fund: number;
}

export const fundService = {
  getAccounts: async (): Promise<AccountsListResponse> => {
    const response = await api.get<AccountsListResponse>('/api/fund/accounts');
    return response.data;
  },

  getAvailableFund: async (accountId?: string): Promise<AvailableFundResponse> => {
    const params = accountId ? { account_id: accountId } : {};
    const response = await api.get<AvailableFundResponse>('/api/fund/available', { params });
    return response.data;
  },
};