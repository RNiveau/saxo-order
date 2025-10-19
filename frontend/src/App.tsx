import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './App.css';
import { Navigation } from './components/Navigation';
import { Sidebar } from './components/Sidebar';
import { Home } from './components/Home';
import { AvailableFunds } from './components/AvailableFunds';
import { SearchResults } from './pages/SearchResults';
import { AssetDetail } from './pages/AssetDetail';
import { Watchlist } from './pages/Watchlist';
import { Report } from './pages/Report';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Navigation />
        <div className="app-container">
          <Sidebar />
          <main className="app-main">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/available-funds" element={<AvailableFunds />} />
              <Route path="/watchlist" element={<Watchlist />} />
              <Route path="/report" element={<Report />} />
              <Route path="/search" element={<SearchResults />} />
              <Route path="/asset/:symbol" element={<AssetDetail />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}

export default App
