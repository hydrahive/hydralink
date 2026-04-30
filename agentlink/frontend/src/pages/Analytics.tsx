import { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { api } from '../lib/api';
import type { Analytics as AnalyticsData, Stats } from '../types/api';

function Analytics() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeWindow, setTimeWindow] = useState(24);

  useEffect(() => {
    const loadData = () => {
      setLoading(true);
      Promise.all([api.getAnalytics(timeWindow), api.getStats()])
        .then(([analyticsData, statsData]) => {
          setAnalytics(analyticsData);
          setStats(statsData);
        })
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    };
    
    loadData();
  }, [timeWindow]);

  if (loading) {
    return <div className="text-center py-12">Loading analytics...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-900 text-red-100 p-4 rounded-md">
        Error: {error}
      </div>
    );
  }

  if (!analytics || !stats) {
    return <div className="text-center py-12">No data available</div>;
  }

  // Prepare data for charts
  const statesOverTime = analytics.states_over_time.map((point) => ({
    time: new Date(point.hour).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }),
    count: point.count,
  }));

  const handoffsOverTime = analytics.handoffs_over_time.map((point) => ({
    time: new Date(point.hour).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }),
    count: point.count,
  }));

  const activityByAgent = analytics.activity_by_agent.map((agent) => ({
    agent: agent.agent_id,
    states: agent.count,
  }));

  const taskTypeData = Object.entries(stats.task_types).map(([type, count]) => ({
    type: type.replace('_', ' '),
    count,
  }));

  const statusData = Object.entries(stats.statuses).map(([status, count]) => ({
    status,
    count,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold">Analytics</h2>
        <select
          value={timeWindow}
          onChange={(e) => setTimeWindow(Number(e.target.value))}
          className="bg-gray-700 text-white px-4 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
        >
          <option value={6}>Last 6 hours</option>
          <option value={12}>Last 12 hours</option>
          <option value={24}>Last 24 hours</option>
          <option value={48}>Last 48 hours</option>
          <option value={168}>Last 7 days</option>
        </select>
      </div>

      {/* States Over Time */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-4">States Over Time</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={statesOverTime}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="time" stroke="#9CA3AF" />
            <YAxis stroke="#9CA3AF" />
            <Tooltip
              contentStyle={{ backgroundColor: '#1F2937', border: 'none' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#3B82F6"
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Handoffs Over Time */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-4">Handoffs Over Time</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={handoffsOverTime}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="time" stroke="#9CA3AF" />
            <YAxis stroke="#9CA3AF" />
            <Tooltip
              contentStyle={{ backgroundColor: '#1F2937', border: 'none' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#8B5CF6"
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Activity by Agent */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-4">Activity by Agent</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={activityByAgent}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="agent" stroke="#9CA3AF" />
            <YAxis stroke="#9CA3AF" />
            <Tooltip
              contentStyle={{ backgroundColor: '#1F2937', border: 'none' }}
            />
            <Legend />
            <Bar dataKey="states" fill="#10B981" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Task Types & Statuses */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-4">Task Types</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={taskTypeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="type" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1F2937', border: 'none' }}
              />
              <Bar dataKey="count" fill="#F59E0B" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-4">Status Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={statusData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="status" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1F2937', border: 'none' }}
              />
              <Bar dataKey="count" fill="#EF4444" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

export default Analytics;
