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
        const symbol = data.results[0].symbol;
        navigate(`/asset/${encodeURIComponent(symbol)}`);
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

  const handleAssetClick = (symbol: string) => {
    navigate(`/asset/${encodeURIComponent(symbol)}`);
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
                  <th>Identifier</th>
                </tr>
              </thead>
              <tbody>
                {results.map((result) => (
                  <tr
                    key={result.identifier}
                    onClick={() => handleAssetClick(result.symbol)}
                    className="result-row"
                  >
                    <td className="symbol">{result.symbol}</td>
                    <td className="description">{result.description}</td>
                    <td className="asset-type">{result.asset_type}</td>
                    <td className="identifier">{result.identifier}</td>
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
