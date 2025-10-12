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

export interface SearchResultItem {
  symbol: string;
  description: string;
  identifier: number;
  asset_type: string;
}

export interface SearchResponse {
  results: SearchResultItem[];
  total: number;
}

export interface WorkflowIndicatorInfo {
  name: string;
  unit_time: string;
  value?: number;
  zone_value?: number;
}

export interface WorkflowCloseInfo {
  direction: string;
  unit_time: string;
  value?: number;
}

export interface WorkflowConditionInfo {
  indicator: WorkflowIndicatorInfo;
  close: WorkflowCloseInfo;
  element?: string;
}

export interface WorkflowTriggerInfo {
  unit_time: string;
  signal: string;
  location: string;
  order_direction: string;
  quantity: number;
}

export interface WorkflowInfo {
  name: string;
  index: string;
  cfd: string;
  enabled: boolean;
  dry_run: boolean;
  end_date?: string;
  is_us: boolean;
  conditions: WorkflowConditionInfo[];
  trigger: WorkflowTriggerInfo;
}

export interface AssetWorkflowsResponse {
  asset_symbol: string;
  total: number;
  workflows: WorkflowInfo[];
}

export const searchService = {
  search: async (
    keyword: string,
    assetType?: string
  ): Promise<SearchResponse> => {
    const params: Record<string, string> = { keyword };
    if (assetType) {
      params.asset_type = assetType;
    }
    const response = await api.get<SearchResponse>('/api/search', { params });
    return response.data;
  },
};

export const workflowService = {
  getAssetWorkflows: async (
    code: string,
    countryCode: string = 'xpar',
    forceFromDisk: boolean = false
  ): Promise<AssetWorkflowsResponse> => {
    const params: Record<string, string | boolean> = {
      code,
      country_code: countryCode,
      force_from_disk: forceFromDisk,
    };
    const response = await api.get<AssetWorkflowsResponse>(
      '/api/workflow/asset',
      { params }
    );
    return response.data;
  },
};

export interface MovingAverageInfo {
  period: number;
  value: number;
  is_above: boolean;
  unit_time: string;
}

export interface AssetIndicatorsResponse {
  asset_symbol: string;
  description: string;
  current_price: number;
  variation_pct: number;
  unit_time: string;
  moving_averages: MovingAverageInfo[];
}

export const indicatorService = {
  getAssetIndicators: async (
    code: string,
    countryCode: string = 'xpar',
    unitTime: string = 'daily'
  ): Promise<AssetIndicatorsResponse> => {
    const params: Record<string, string> = {
      country_code: countryCode,
      unit_time: unitTime,
    };
    const response = await api.get<AssetIndicatorsResponse>(
      `/api/indicator/asset/${code}`,
      { params }
    );
    return response.data;
  },
};

export interface WatchlistItem {
  id: string;
  asset_symbol: string;
  description: string;
  country_code: string;
  current_price: number;
  variation_pct: number;
  added_at: string;
}

export interface WatchlistResponse {
  items: WatchlistItem[];
  total: number;
}

export interface AddToWatchlistRequest {
  asset_id: string;
  asset_symbol: string;
  description: string;
  country_code: string;
}

export interface AddToWatchlistResponse {
  message: string;
  asset_id: string;
  asset_symbol: string;
}

export const watchlistService = {
  getWatchlist: async (): Promise<WatchlistResponse> => {
    const response = await api.get<WatchlistResponse>('/api/watchlist');
    return response.data;
  },

  addToWatchlist: async (
    request: AddToWatchlistRequest
  ): Promise<AddToWatchlistResponse> => {
    const response = await api.post<AddToWatchlistResponse>(
      '/api/watchlist',
      request
    );
    return response.data;
  },
};