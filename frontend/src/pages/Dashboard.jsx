import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import {
  Users,
  AlertTriangle,
  ClipboardCheck,
  Activity,
  RefreshCw,
} from "lucide-react";
import api from "../services/api";
import "./Dashboard.css";

function getErrorMessage(err) {
  // Axios reports "Network Error" when no HTTP response arrives at all.
  if (!err.response) {
    return (
      `Cannot reach the backend at ${api.defaults.baseURL}. ` +
      "Make sure uvicorn is running."
    );
  }

  return err.response.data?.detail || err.message;
}

function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await api.get("/api/dashboard/summary");
      setSummary(response.data);
    } catch (err) {
      setError(getErrorMessage(err) || "Unable to load dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  if (loading) {
    return <div className="dashboard-message">Loading dashboard data...</div>;
  }

  if (error) {
    return (
      <div className="dashboard-message">
        <p>{error}</p>
        <button onClick={loadDashboard}>Try again</button>
      </div>
    );
  }

  const metrics = {
    total: summary.total_assessed,
    high: summary.priority_counts.HIGH ?? 0,
    moderate: summary.priority_counts.MODERATE ?? 0,
    routine: summary.priority_counts.ROUTINE ?? 0,
    averageScore: summary.average_score.toFixed(1),
    pendingReviews: summary.pending_reviews,
  };

  const priorityData = [
    { name: "High", value: metrics.high, color: "#ef4444" },
    { name: "Moderate", value: metrics.moderate, color: "#f59e0b" },
    { name: "Routine", value: metrics.routine, color: "#10b981" },
  ];

  // Components have different maximums (40 / 40 / 20), so show them in the label.
  const componentData = summary.component_averages.map((item) => ({
    name: `${item.component} (max ${item.max})`,
    score: item.average,
  }));

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">WORKFORCE ANALYTICS</p>
          <h1>Dashboard Overview</h1>
          <p className="subtitle">
            Understand workforce support needs through explainable signals.
          </p>
        </div>

        <button className="refresh-button" onClick={loadDashboard}>
          <RefreshCw size={16} />
          Refresh
        </button>
      </header>

      <section className="metrics-grid">
        <MetricCard
          title="Employees Assessed"
          value={metrics.total.toLocaleString()}
          icon={<Users />}
          detail="Employees with available assessment records"
        />

        <MetricCard
          title="High Priority"
          value={metrics.high.toLocaleString()}
          icon={<AlertTriangle />}
          detail="Requires careful human review"
          color="red"
        />

        <MetricCard
          title="Awaiting Review"
          value={metrics.pendingReviews.toLocaleString()}
          icon={<ClipboardCheck />}
          detail={`${summary.reviews_recorded.toLocaleString()} reviews recorded so far`}
          color="orange"
        />

        <MetricCard
          title="Average Support Score"
          value={`${metrics.averageScore}/100`}
          icon={<Activity />}
          detail="Explainable support-priority score"
        />
      </section>

      <section className="charts-grid">
        <div className="chart-card">
          <div className="chart-heading">
            <div>
              <h2>Support Priority Distribution</h2>
              <p>Employees grouped by support priority</p>
            </div>
          </div>

          <div className="chart-area">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={priorityData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={100}
                  paddingAngle={4}
                >
                  {priorityData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-heading">
            <div>
              <h2>Average Component Scores</h2>
              <p>Average contribution from each assessment component</p>
            </div>
          </div>

          <div className="chart-area">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={componentData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" interval={0} tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 40]} />
                <Tooltip />
                <Bar dataKey="score" name="Average score" radius={[6, 6, 0, 0]} fill="#6366f1" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="distribution-grid">
        <PriorityCard title="High Priority" count={metrics.high} color="red" />
        <PriorityCard title="Moderate Priority" count={metrics.moderate} color="orange" />
        <PriorityCard title="Routine Priority" count={metrics.routine} color="green" />
      </section>

      <p className="dashboard-disclaimer">
        These scores identify potential areas where supportive conversations
        may be useful. They are not attrition probabilities or automated
        employment decisions. Human review is required.
      </p>
    </div>
  );
}

function MetricCard({ title, value, icon, detail, color = "blue" }) {
  return (
    <div className="metric-card">
      <div className={`metric-icon ${color}`}>{icon}</div>
      <p className="metric-title">{title}</p>
      <h2>{value}</h2>
      <p className="metric-detail">{detail}</p>
    </div>
  );
}

function PriorityCard({ title, count, color }) {
  return (
    <div className={`priority-card ${color}`}>
      <p>{title}</p>
      <h2>{count.toLocaleString()}</h2>
      <span>Employees</span>
    </div>
  );
}

export default Dashboard;