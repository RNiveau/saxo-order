import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { searchService, type SearchResultItem } from '../services/api';
import './SearchResults.css';

export function SearchResults() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const query = searchParams.get('q') || '';

  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (query) {
      performSearch(query);
    }
  }, [query]);

  const performSearch = async (keyword: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await searchService.search(keyword);

      // Auto-redirect if only one result
      if (data.results.length === 1) {
        const result = data.results[0];
        navigate(`/asset/${encodeURIComponent(result.symbol)}?exchange=${result.exchange}`, {
          state: { description: result.description }
        });
        return;
      }

      setResults(data.results);
    } catch (err) {
      setError('Failed to perform search');
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAssetClick = (symbol: string, description: string, exchange: string) => {
    navigate(`/asset/${encodeURIComponent(symbol)}?exchange=${exchange}`, { state: { description } });
  };

  return (
    <div className="search-results-container">
      <h2>Search Results for "{query}"</h2>

      {loading && <div className="loading">Searching...</div>}

      {error && <div className="error">{error}</div>}

      {!loading && !error && results.length === 0 && query && (
        <div className="no-results">
          No assets found for "{query}"
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="results-list">
          <div className="results-header">
            Found {results.length} asset{results.length !== 1 ? 's' : ''}
          </div>
          <div className="results-table">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Description</th>
                  <th>Type</th>
                  <th>Exchange</th>
                </tr>
              </thead>
              <tbody>
                {results.map((result, index) => (
                  <tr
                    key={`${result.exchange}-${result.symbol}-${index}`}
                    onClick={() => handleAssetClick(result.symbol, result.description, result.exchange)}
                    className="result-row"
                  >
                    <td className="symbol">{result.symbol}</td>
                    <td className="description">{result.description}</td>
                    <td className="asset-type">{result.asset_type}</td>
                    <td className="exchange">
                      <span className={`exchange-badge ${result.exchange}`}>
                        {result.exchange}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
