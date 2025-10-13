export function getTradingViewUrl(assetSymbol: string): string {
  // Parse asset_symbol to get code and country_code
  const [code, countryCode = 'xpar'] = assetSymbol.split(':');

  // Map country codes to TradingView exchanges
  const exchangeMap: Record<string, string> = {
    'xpar': 'EURONEXT',
    'xnas': 'NASDAQ',
    'xnys': 'NYSE',
    'xlon': 'LSE',
    'xfra': 'FWB',
    'xetr': 'XETR',
  };

  const exchange = exchangeMap[countryCode.toLowerCase()] || 'EURONEXT';
  const symbol = code.toUpperCase();

  return `https://www.tradingview.com/chart/?symbol=${exchange}:${symbol}`;
}
