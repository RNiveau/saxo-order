import { NavLink } from 'react-router-dom';
import './Navigation.css';

export function Navigation() {
  return (
    <nav className="navigation">
      <div className="nav-container">
        <div className="nav-brand">
          <NavLink to="/">Saxo Order Management</NavLink>
        </div>
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