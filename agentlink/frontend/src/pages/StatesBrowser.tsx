import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { AgentState } from '../types/api';

function StatesBrowser() {
  const [states, setStates] = useState<AgentState[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState({
    agent_id: '',
    status: '',
  });

  useEffect(() => {
    // Debounce API calls to avoid spam
    const timer = setTimeout(() => {
      loadStates();
    }, 300); // 300ms debounce

    return () => clearTimeout(timer);
  }, [filter]);

  const loadStates = () => {
    setLoading(true);
    api
      .getStates({
        agent_id: filter.agent_id || undefined,
        status: filter.status || undefined,
        limit: 100,
      })
      .then(setStates)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  if (loading) {
    return <div className="text-center py-12">Loading states...</div>;
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
      <h2 className="text-3xl font-bold">States Browser</h2>

      {/* Filters */}
      <div className="bg-gray-800 rounded-lg p-4 flex space-x-4">
        <input
          type="text"
          placeholder="Filter by agent ID..."
          value={filter.agent_id}
          onChange={(e) => setFilter({ ...filter, agent_id: e.target.value })}
          className="flex-1 bg-gray-700 text-white px-4 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
        />
        <select
          value={filter.status}
          onChange={(e) => setFilter({ ...filter, status: e.target.value })}
          className="bg-gray-700 text-white px-4 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="blocked">Blocked</option>
          <option value="done">Done</option>
        </select>
        <button
          onClick={loadStates}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded font-medium transition"
        >
          Refresh
        </button>
      </div>

      {/* States List */}
      <div className="space-y-4">
        {states.length === 0 ? (
          <p className="text-gray-400 text-center py-12">No states found</p>
        ) : (
          states.map((state) => (
            <StateCard key={state.id} state={state} />
          ))
        )}
      </div>
    </div>
  );
}

function StateCard({ state }: { state: AgentState }) {
  const [expanded, setExpanded] = useState(false);

  const statusColors = {
    pending: 'bg-yellow-600',
    in_progress: 'bg-blue-600',
    blocked: 'bg-red-600',
    done: 'bg-green-600',
  };

  const typeIcons = {
    bug_fix: '🐛',
    feature: '✨',
    review: '👀',
    research: '🔬',
    refactor: '♻️',
  };

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      <div
        className="p-4 cursor-pointer hover:bg-gray-750 transition"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <span className="text-2xl">{typeIcons[state.task.type]}</span>
            <div>
              <h3 className="font-semibold">{state.task.description}</h3>
              <p className="text-sm text-gray-400">
                Agent: {state.agent_id} • {new Date(state.timestamp).toLocaleString()}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span
              className={`px-3 py-1 rounded-full text-xs font-medium ${
                statusColors[state.task.status]
              }`}
            >
              {state.task.status}
            </span>
            {state.handoff && (
              <span className="px-3 py-1 rounded-full text-xs font-medium bg-purple-600">
                Handoff → {state.handoff.to_agent}
              </span>
            )}
            <span className="text-gray-400">{expanded ? '▼' : '▶'}</span>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-700 p-4 space-y-4">
          {/* Working Memory */}
          {state.working_memory.hypotheses.length > 0 && (
            <div>
              <h4 className="font-semibold text-sm text-gray-400 mb-2">Hypotheses</h4>
              <ul className="list-disc list-inside text-sm space-y-1">
                {state.working_memory.hypotheses.map((h, i) => (
                  <li key={i}>{h}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Files */}
          {state.context.files.length > 0 && (
            <div>
              <h4 className="font-semibold text-sm text-gray-400 mb-2">Files</h4>
              <ul className="font-mono text-xs space-y-1">
                {state.context.files.map((f, i) => (
                  <li key={i} className="text-blue-400">
                    {f.path}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Full JSON */}
          <details className="text-xs">
            <summary className="cursor-pointer text-gray-400 hover:text-white">
              Show Full State (JSON)
            </summary>
            <pre className="mt-2 bg-gray-900 p-3 rounded overflow-x-auto">
              {JSON.stringify(state, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}

export default StatesBrowser;
