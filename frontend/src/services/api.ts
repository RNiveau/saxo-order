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
  account_key: string;
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
  identifier: number | null;
  asset_type: string;
  exchange: string;
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
  currency: string;
  unit_time: string;
  moving_averages: MovingAverageInfo[];
  tradingview_url?: string;
}

export const indicatorService = {
  getAssetIndicators: async (
    code: string,
    countryCode: string = 'xpar',
    unitTime: string = 'daily',
    exchange: string = 'saxo'
  ): Promise<AssetIndicatorsResponse> => {
    const params: Record<string, string> = {
      country_code: countryCode,
      unit_time: unitTime,
      exchange: exchange,
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
  currency: string;
  added_at: string;
  labels: string[];
  tradingview_url?: string;
  exchange: string;
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
  labels?: string[];
  exchange?: string;
}

export interface AddToWatchlistResponse {
  message: string;
  asset_id: string;
  asset_symbol: string;
}

export interface RemoveFromWatchlistResponse {
  message: string;
  asset_id: string;
}

export interface CheckWatchlistResponse {
  in_watchlist: boolean;
  asset_id: string;
  labels: string[];
}

export interface UpdateLabelsRequest {
  labels: string[];
}

export interface UpdateLabelsResponse {
  message: string;
  asset_id: string;
  labels: string[];
}

export const watchlistService = {
  getWatchlist: async (): Promise<WatchlistResponse> => {
    const response = await api.get<WatchlistResponse>('/api/watchlist');
    return response.data;
  },

  getAllWatchlist: async (): Promise<WatchlistResponse> => {
    const response = await api.get<WatchlistResponse>('/api/watchlist/all');
    return response.data;
  },

  getLongTermPositions: async (): Promise<WatchlistResponse> => {
    const response = await api.get<WatchlistResponse>('/api/watchlist/long-term');
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

  removeFromWatchlist: async (
    assetId: string
  ): Promise<RemoveFromWatchlistResponse> => {
    const response = await api.delete<RemoveFromWatchlistResponse>(
      `/api/watchlist/${assetId}`
    );
    return response.data;
  },

  checkWatchlist: async (assetId: string): Promise<CheckWatchlistResponse> => {
    const response = await api.get<CheckWatchlistResponse>(
      `/api/watchlist/check/${assetId}`
    );
    return response.data;
  },

  updateLabels: async (
    assetId: string,
    labels: string[]
  ): Promise<UpdateLabelsResponse> => {
    const response = await api.patch<UpdateLabelsResponse>(
      `/api/watchlist/${assetId}/labels`,
      { labels }
    );
    return response.data;
  },
};

export const indexesService = {
  getIndexes: async (): Promise<WatchlistResponse> => {
    const response = await api.get<WatchlistResponse>('/api/indexes');
    return response.data;
  },
};

export interface ReportOrder {
  code: string;
  name: string;
  date: string;
  direction: string;
  quantity: number;
  price: number;
  price_eur: number | null;
  total: number;
  total_eur: number;
  currency: string;
  asset_type: string;
  underlying_price: number | null;
}

export interface ReportListResponse {
  orders: ReportOrder[];
  total_count: number;
  from_date: string;
  to_date: string | null;
}

export interface ReportSummary {
  total_orders: number;
  total_volume_eur: number;
  total_fees_eur: number;
  buy_orders: number;
  buy_volume_eur: number;
  sell_orders: number;
  sell_volume_eur: number;
}

export interface CreateGSheetOrderRequest {
  account_id: string;
  from_date: string;
  order_index: number;
  stop?: number;
  objective?: number;
  strategy?: string;
  signal?: string;
  comment?: string;
}

export interface UpdateGSheetOrderRequest {
  account_id: string;
  from_date: string;
  order_index: number;
  line_number: number;
  close: boolean;
  stopped: boolean;
  be_stopped: boolean;
  stop?: number;
  objective?: number;
  strategy?: string;
  signal?: string;
  comment?: string;
}

export const reportService = {
  getOrders: async (
    accountId: string,
    fromDate: string,
    toDate?: string
  ): Promise<ReportListResponse> => {
    const params: Record<string, string> = {
      account_id: accountId,
      from_date: fromDate,
    };
    if (toDate) {
      params.to_date = toDate;
    }
    const response = await api.get<ReportListResponse>('/api/report/orders', { params });
    return response.data;
  },

  getSummary: async (
    accountId: string,
    fromDate: string,
    toDate?: string
  ): Promise<ReportSummary> => {
    const params: Record<string, string> = {
      account_id: accountId,
      from_date: fromDate,
    };
    if (toDate) {
      params.to_date = toDate;
    }
    const response = await api.get<ReportSummary>('/api/report/summary', { params });
    return response.data;
  },

  createGSheetOrder: async (
    request: CreateGSheetOrderRequest
  ): Promise<{ status: string; message: string }> => {
    const response = await api.post('/api/report/gsheet/create', request);
    return response.data;
  },

  updateGSheetOrder: async (
    request: UpdateGSheetOrderRequest
  ): Promise<{ status: string; message: string }> => {
    const response = await api.post('/api/report/gsheet/update', request);
    return response.data;
  },
};

export interface EnumOption {
  value: string;
  label: string;
}

export interface ReportConfig {
  strategies: EnumOption[];
  signals: EnumOption[];
}

export const reportConfigService = {
  getConfig: async (): Promise<ReportConfig> => {
    const response = await api.get<ReportConfig>('/api/report/config');
    return response.data;
  },
};

export interface SetTradingViewLinkResponse {
  message: string;
  asset_id: string;
  tradingview_url: string;
}

export const tradingViewService = {
  setTradingViewLink: async (
    assetId: string,
    tradingviewUrl: string
  ): Promise<SetTradingViewLinkResponse> => {
    const response = await api.put<SetTradingViewLinkResponse>(
      `/api/asset-details/${assetId}/tradingview`,
      { tradingview_url: tradingviewUrl }
    );
    return response.data;
  },
};

export interface OrderRequest {
  code: string;
  price: number;
  quantity: number;
  order_type: string;
  direction: string;
  country_code?: string;
  stop?: number;
  objective?: number;
  strategy?: string;
  signal?: string;
  comment?: string;
  account_key?: string;
}

export interface OcoOrderRequest {
  code: string;
  quantity: number;
  limit_price: number;
  limit_direction: string;
  stop_price: number;
  stop_direction: string;
  country_code?: string;
  stop?: number;
  objective?: number;
  strategy?: string;
  signal?: string;
  comment?: string;
  account_key?: string;
}

export interface StopLimitOrderRequest {
  code: string;
  quantity: number;
  limit_price: number;
  stop_price: number;
  country_code?: string;
  stop?: number;
  objective?: number;
  strategy?: string;
  signal?: string;
  comment?: string;
  account_key?: string;
}

export interface OrderResponse {
  success: boolean;
  message: string;
  order_id?: string;
  details?: Record<string, unknown>;
}

export const orderService = {
  createOrder: async (request: OrderRequest): Promise<OrderResponse> => {
    const response = await api.post<OrderResponse>('/api/orders', request);
    return response.data;
  },

  createOcoOrder: async (request: OcoOrderRequest): Promise<OrderResponse> => {
    const response = await api.post<OrderResponse>('/api/orders/oco', request);
    return response.data;
  },

  createStopLimitOrder: async (
    request: StopLimitOrderRequest
  ): Promise<OrderResponse> => {
    const response = await api.post<OrderResponse>(
      '/api/orders/stop-limit',
      request
    );
    return response.data;
  },
};

export interface HomepageItem {
  id: string;
  asset_symbol: string;
  description: string;
  current_price: number;
  variation_pct: number;
  currency: string;
  tradingview_url?: string;
  exchange: string;
  ma50_value: number;
  is_above_ma50: boolean;
}

export interface HomepageResponse {
  items: HomepageItem[];
  total: number;
}

export const homepageService = {
  getHomepageAssets: async (): Promise<HomepageResponse> => {
    const response = await api.get<HomepageResponse>('/api/homepage');
    return response.data;
  },
};

export interface AlertItem {
  id: string;
  alert_type: string;
  asset_code: string;
  asset_description: string;
  exchange: string;
  country_code: string | null;
  date: string;
  data: Record<string, any>;
  age_hours: number;
  tradingview_url?: string;
}

export interface AlertsResponse {
  alerts: AlertItem[];
  total_count: number;
  available_filters: {
    asset_codes: string[];
    alert_types: string[];
    country_codes: string[];
  };
}

export interface RunAlertsResponse {
  status: 'success' | 'no_alerts' | 'error';
  alerts_detected: number;
  alerts: AlertItem[];
  execution_time_ms: number;
  message: string;
  next_allowed_at: string;
}

export const alertService = {
  getAll: async (params?: {
    asset_code?: string;
    alert_type?: string;
    country_code?: string;
  }): Promise<AlertsResponse> => {
    const response = await api.get<AlertsResponse>('/api/alerts', { params });
    return response.data;
  },

  run: async (params: {
    asset_code: string;
    country_code: string | null;
    exchange: string;
  }): Promise<RunAlertsResponse> => {
    const response = await api.post<RunAlertsResponse>(
      '/api/alerts/run',
      params,
      { timeout: 60000 }
    );
    return response.data;
  },
};

export interface AssetDetailResponse {
  asset_id: string;
  tradingview_url?: string;
  updated_at?: string;
  is_excluded?: boolean;
}

export interface AssetListResponse {
  assets: AssetDetailResponse[];
  count: number;
  excluded_count?: number;
  active_count?: number;
}

export const assetDetailsService = {
  getAllAssets: async (): Promise<AssetListResponse> => {
    const response = await api.get<AssetListResponse>('/api/asset-details');
    return response.data;
  },

  getExcludedAssets: async (): Promise<AssetListResponse> => {
    const response = await api.get<AssetListResponse>('/api/asset-details/excluded/list');
    return response.data;
  },

  updateExclusion: async (
    assetId: string,
    isExcluded: boolean
  ): Promise<AssetDetailResponse> => {
    const response = await api.put<AssetDetailResponse>(
      `/api/asset-details/${assetId}/exclusion`,
      { is_excluded: isExcluded }
    );
    return response.data;
  },

  getAssetDetails: async (assetId: string): Promise<AssetDetailResponse> => {
    const response = await api.get<AssetDetailResponse>(`/api/asset-details/${assetId}`);
    return response.data;
  },
};

// Workflow Management Interfaces
export interface WorkflowListItem {
  id: string;
  name: string;
  index: string;
  cfd: string;
  enable: boolean;
  dry_run: boolean;
  is_us: boolean;
  end_date: string | null;
  primary_indicator: string | null;
  primary_unit_time: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowListResponse {
  workflows: WorkflowListItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface IndicatorDetail {
  name: string;
  ut: string;
  value: number | null;
  zone_value: number | null;
}

export interface CloseDetail {
  direction: string;
  ut: string;
  spread: number;
}

export interface ConditionDetail {
  indicator: IndicatorDetail;
  close: CloseDetail;
  element: string | null;
}

export interface TriggerDetail {
  ut: string;
  signal: string;
  location: string;
  order_direction: string;
  quantity: number;
}

export interface WorkflowDetail {
  id: string;
  name: string;
  index: string;
  cfd: string;
  enable: boolean;
  dry_run: boolean;
  is_us: boolean;
  end_date: string | null;
  conditions: ConditionDetail[];
  trigger: TriggerDetail;
  created_at: string;
  updated_at: string;
}

export interface WorkflowListParams {
  page?: number;
  per_page?: number;
  enabled?: boolean;
  index?: string;
  indicator_type?: string;
  dry_run?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export const workflowService = {
  listWorkflows: async (params?: WorkflowListParams): Promise<WorkflowListResponse> => {
    const response = await api.get<WorkflowListResponse>('/api/workflow/workflows', {
      params,
    });
    return response.data;
  },

  getWorkflowDetail: async (id: string): Promise<WorkflowDetail> => {
    const response = await api.get<WorkflowDetail>(`/api/workflow/workflows/${id}`);
    return response.data;
  },
};