# Saxo Order UI

Simple frontend interface for the Saxo Order Management system.

## Features

- View available funds across Saxo accounts
- No authentication required (local use only)
- Real-time fund calculations including open buy orders

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
