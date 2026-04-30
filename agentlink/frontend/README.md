# AgentLink Frontend Console

Full-featured web console for AgentLink - Agent-to-Agent State Protocol

## Features

- **Live Dashboard** - Real-time activity feed with WebSocket updates
- **States Browser** - Search and filter agent states
- **Analytics** - Time-series charts and statistics
- **Dark Mode** - Beautiful dark theme
- **Mobile Responsive** - Works on all devices

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Recharts** - Data visualization
- **React Router** - Client-side routing

## Development

```bash
# Install dependencies
npm install

# Start dev server (default: http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Configuration

Copy `.env.example` to `.env` and adjust:

```env
VITE_API_URL=http://YOUR_VM_IP:8000
VITE_WS_URL=ws://YOUR_VM_IP:8000/ws
```

## Deployment

Build artifacts are in `dist/` directory. Serve with any static file server.

Example with nginx:

```nginx
location / {
  root /path/to/agentlink/frontend/dist;
  try_files $uri $uri/ /index.html;
}

location /api/ {
  proxy_pass http://localhost:8000;
}

location /ws {
  proxy_pass http://localhost:8000;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
}
```

## API Endpoints Used

- `GET /api/stats` - Aggregated statistics
- `GET /api/analytics?hours=24` - Time-series data
- `GET /api/agents/active` - Currently connected agents
- `GET /states` - List all states (with filters)
- `GET /states/:id` - Get single state
- `WS /ws` - WebSocket for real-time updates

## Project Structure

```
src/
├── pages/           # Page components
│   ├── Dashboard.tsx
│   ├── StatesBrowser.tsx
│   └── Analytics.tsx
├── lib/             # API clients
│   ├── api.ts       # REST API wrapper
│   └── websocket.ts # WebSocket client
├── types/           # TypeScript types
│   └── api.ts
├── App.tsx          # Main app with routing
└── main.tsx         # Entry point
```

## License

MIT
