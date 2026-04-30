import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { wsClient } from '../lib/websocket';
import type { Stats, WSMessage } from '../types/api';

function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [latestEvents, setLatestEvents] = useState<WSMessage[]>([]);

  useEffect(() => {
    let unsubscribe: (() => void) | null = null;
    let mounted = true;

    // Fetch initial stats
    api
      .getStats()
      .then((data) => {
        if (mounted) setStats(data);
      })
      .catch((err) => {
        if (mounted) setError(err.message);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    // Connect WebSocket and subscribe after successful connection
    wsClient
      .connect('all')
      .then(() => {
        if (!mounted) return;
        
        setWsConnected(true);

        // Subscribe to WebSocket events AFTER connection is established
        unsubscribe = wsClient.on((message) => {
          console.log('WebSocket message:', message);
          setLatestEvents((prev) => [message, ...prev].slice(0, 10));

          // Refresh stats on state changes
          if (message.type === 'state_created' || message.type === 'handoff_received') {
            api.getStats()
              .then((data) => {
                if (mounted) setStats(data);
              })
              .catch((err) => console.error('Failed to refresh stats:', err));
          }
        });
      })
      .catch((err) => console.error('WebSocket connection failed:', err));

    return () => {
      mounted = false;
      if (unsubscribe) {
        unsubscribe();
      }
    };
  }, []);

  if (loading) {
    return <div className="text-center py-12">Loading...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-900 text-red-100 p-4 rounded-md">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold">Live Dashboard</h2>
        <div className="flex items-center space-x-2">
          <div
            className={`w-3 h-3 rounded-full ${
              wsConnected ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-sm">
            {wsConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total States"
            value={stats.total_states}
            icon="📊"
          />
          <StatCard
            title="Unique Agents"
            value={stats.unique_agents}
            icon="🤖"
          />
          <StatCard
            title="Total Handoffs"
            value={stats.total_handoffs}
            icon="🔄"
          />
          <StatCard
            title="Active Connections"
            value={stats.active_ws_connections}
            icon="🔌"
          />
        </div>
      )}

      {/* Latest Events */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-4">Latest Events</h3>
        <div className="space-y-2">
          {latestEvents.length === 0 ? (
            <p className="text-gray-400">No events yet...</p>
          ) : (
            latestEvents.map((event, index) => (
              <div
                key={index}
                className="bg-gray-700 p-3 rounded border-l-4 border-blue-500"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm">{event.type}</span>
                  <span className="text-xs text-gray-400">
                    {'timestamp' in event ? new Date(event.timestamp).toLocaleTimeString() : ''}
                  </span>
                </div>
                <pre className="text-xs text-gray-300 mt-2 overflow-x-auto">
                  {JSON.stringify(event, null, 2)}
                </pre>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
}: {
  title: string;
  value: number;
  icon: string;
}) {
  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm">{title}</p>
          <p className="text-3xl font-bold mt-2">{value}</p>
        </div>
        <div className="text-4xl">{icon}</div>
      </div>
    </div>
  );
}

export default Dashboard;
