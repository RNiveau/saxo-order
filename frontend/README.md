# Saxo Order UI

Simple frontend interface for the Saxo Order Management system.

## Features

- View available funds across Saxo accounts
- Search and view asset details with technical indicators
- Manage watchlist with live price updates
- View and manage automated trading workflows
  - Filter workflows by status, index, indicator, and mode
  - Sort by name, index, or end date
  - View detailed workflow configuration including conditions and triggers
- View long-term positions and alerts
- Manage asset exclusions for trading automation
- Trading reports and performance analytics
- No authentication required (local use only)
- Real-time data updates with automatic refresh

## Development

### Prerequisites
- Node.js 20+
- Backend API running on port 8000

### Local Setup

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

The UI will be available at http://localhost:5173

### Docker Setup

From the project root directory:

```bash
# Start both backend and frontend
docker-compose up

# Or build and start
docker-compose up --build
```

After changing `package.json` or `package-lock.json`, rebuild the image so the container's `node_modules` matches the lockfile:

```bash
docker-compose build --no-cache frontend
```

A stale image will surface as an esbuild host/binary version mismatch (e.g. `Host version "0.25.10" does not match binary version "0.27.7"`) because the platform-specific `@esbuild/*` packages are reinstalled at runtime while the cached top-level `esbuild` lib is not.

The services will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000

## Environment Variables

- `VITE_API_URL`: Backend API URL (default: http://localhost:8000)

## Tech Stack

- React with TypeScript
- Vite for build tooling
- Axios for API calls
- CSS for styling
