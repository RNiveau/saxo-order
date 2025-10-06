import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import './Navigation.css';

export function Navigation() {
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
      setSearchQuery('');
    }
  };

  return (
    <nav className="navigation">
      <div className="nav-container">
        <div className="nav-brand">
          <NavLink to="/">Saxo Order Management</NavLink>
        </div>
        <form className="nav-search" onSubmit={handleSearchSubmit}>
          <input
            type="text"
            placeholder="Search assets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="search-button">
            Search
          </button>
        </form>
        <ul className="nav-menu">
          <li>
            <NavLink
              to="/available-funds"
              className={({ isActive }) => isActive ? 'active' : ''}
            >
              Available Funds
            </NavLink>
          </li>
        </ul>
      </div>
    </nav>
  );
}