import { Fragment, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import {
  getInterventions,
  getIntervention,
  getEligibleReviews,
  createIntervention,
  updateInterventionStatus,
} from "../services/interventionService";
import "./InterventionManagement.css";

const ROLES = [
  { value: "HR_PARTNER", label: "HR Partner" },
  { value: "MANAGER", label: "Manager" },
  { value: "PEOPLE_PARTNER", label: "People Partner" },
];

const TYPES = [
  { value: "ENGAGEMENT_CHECK_IN", label: "Engagement Check-in" },
  { value: "WORKLOAD_SUPPORT", label: "Workload Support" },
  { value: "CAREER_DEVELOPMENT", label: "Career Development" },
  { value: "MANAGER_CONVERSATION", label: "Manager Conversation" },
];

// Mirrors the allowed transitions enforced by the backend.
const NEXT_STATUSES = {
  OPEN: [
    { status: "IN_PROGRESS", label: "Start", className: "status-btn" },
    { status: "CANCELLED", label: "Cancel", className: "cancel-btn" },
  ],
  IN_PROGRESS: [
    { status: "COMPLETED", label: "Complete", className: "status-btn" },
    { status: "CANCELLED", label: "Cancel", className: "cancel-btn" },
  ],
  COMPLETED: [],
  CANCELLED: [],
};

const initialForm = {
  employee_id: "",
  intervention_type: "ENGAGEMENT_CHECK_IN",
  assigned_to_role: "HR_PARTNER",
  recommended_action: "",
  actor_role: "HR_PARTNER",
  notes: "",
};

function getErrorMessage(err, fallback) {
  if (!err.response) {
    return "Cannot reach the backend. Make sure uvicorn is running.";
  }
  return err.response.data?.detail || err.message || fallback;
}

function formatLabel(value) {
  return String(value ?? "").replaceAll("_", " ").toLowerCase();
}

function InterventionManagement() {
  const [interventions, setInterventions] = useState([]);
  const [totalInterventions, setTotalInterventions] = useState(0);
  const [eligible, setEligible] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [form, setForm] = useState(initialForm);
  const [actorRole, setActorRole] = useState("HR_PARTNER");
  const [expandedId, setExpandedId] = useState(null);
  const [events, setEvents] = useState({});

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadData = async (status = statusFilter) => {
    try {
      setLoading(true);
      setError("");

      const [interventionData, eligibleData] = await Promise.all([
        getInterventions({ limit: 100, offset: 0, status: status || undefined }),
        getEligibleReviews(),
      ]);

      setInterventions(interventionData.interventions);
      setTotalInterventions(interventionData.total);
      setEligible(eligibleData.reviews);
      setEvents({});
      setExpandedId(null);
    } catch (err) {
      setError(getErrorMessage(err, "Unable to load intervention data."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(statusFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const handleChange = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
  };

  const selectedReview = eligible.find(
    (review) => review.employee_id === form.employee_id
  );

  const handleCreate = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!form.employee_id || form.recommended_action.trim().length < 10) {
      setError(
        "Select a reviewed employee and enter an action of at least 10 characters."
      );
      return;
    }

    try {
      setSubmitting(true);

      const result = await createIntervention({
        ...form,
        recommended_action: form.recommended_action.trim(),
        notes: form.notes.trim() || null,
      });

      setSuccess(
        `Intervention ${result.intervention.intervention_id} created for ${form.employee_id}.`
      );
      setForm(initialForm);
      await loadData();
    } catch (err) {
      setError(getErrorMessage(err, "Could not create the intervention."));
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (id, status) => {
    setError("");
    setSuccess("");

    try {
      setUpdatingId(id);

      await updateInterventionStatus(id, {
        status,
        actor_role: actorRole,
        notes: "Updated from Intervention Management.",
      });

      setSuccess(`${id} moved to ${status}.`);
      await loadData();
    } catch (err) {
      setError(getErrorMessage(err, "Unable to update intervention status."));
    } finally {
      setUpdatingId(null);
    }
  };

  const toggleHistory = async (id) => {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }

    setExpandedId(id);

    if (events[id]) return;

    try {
      const detail = await getIntervention(id);
      setEvents((current) => ({ ...current, [id]: detail.events }));
    } catch (err) {
      setError(getErrorMessage(err, "Unable to load event history."));
    }
  };

  return (
    <div className="intervention-page">
      <div className="intervention-header">
        <div>
          <p className="intervention-eyebrow">SUPPORT ACTIONS</p>
          <h1>Intervention Management</h1>
          <p>Create and track human-reviewed employee support actions.</p>
        </div>

        <button className="refresh-btn" onClick={() => loadData()}>
          <RefreshCw size={15} />
          Refresh
        </button>
      </div>

      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}

      <section className="intervention-form-card">
        <h2>Create an Intervention</h2>
        <p className="form-note">
          Only employees with a saved SUPPORT_NEEDED or FOLLOW_UP review are
          listed. Record reviews on the Human Reviews page first.
        </p>

        <form onSubmit={handleCreate}>
          <div className="form-grid">
            <label>
              Reviewed employee
              <select
                name="employee_id"
                value={form.employee_id}
                onChange={handleChange}
                required
              >
                <option value="">
                  {eligible.length
                    ? `Select employee (${eligible.length} eligible)`
                    : "No reviewed employees yet"}
                </option>
                {eligible.map((review) => (
                  <option key={review.employee_id} value={review.employee_id}>
                    {review.employee_id} · {formatLabel(review.decision)} ·{" "}
                    score {review.reviewed_score}
                    {review.has_active_intervention ? " · has active intervention" : ""}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Intervention type
              <select
                name="intervention_type"
                value={form.intervention_type}
                onChange={handleChange}
              >
                {TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Assigned to
              <select
                name="assigned_to_role"
                value={form.assigned_to_role}
                onChange={handleChange}
              >
                {ROLES.map((role) => (
                  <option key={role.value} value={role.value}>
                    {role.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Created by
              <select
                name="actor_role"
                value={form.actor_role}
                onChange={handleChange}
              >
                {ROLES.map((role) => (
                  <option key={role.value} value={role.value}>
                    {role.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {selectedReview && (
            <div className="review-context">
              <strong>Review on record:</strong>{" "}
              {formatLabel(selectedReview.decision)} by{" "}
              {formatLabel(selectedReview.reviewed_by_role)} ·{" "}
              {selectedReview.reviewed_priority} priority · reasons:{" "}
              {selectedReview.reason_codes
                ? formatLabel(selectedReview.reason_codes.replaceAll("|", ", "))
                : "none"}
              {selectedReview.has_active_intervention && (
                <span className="review-context-warning">
                  {" "}This employee already has an open or in-progress intervention.
                </span>
              )}
            </div>
          )}

          <label className="action-label">
            Recommended support action
            <textarea
              name="recommended_action"
              value={form.recommended_action}
              onChange={handleChange}
              placeholder="Example: Arrange a supportive workload discussion and review current task allocation."
              rows={4}
              minLength={10}
              maxLength={2000}
              required
            />
          </label>

          <label className="action-label">
            Notes (optional)
            <textarea
              name="notes"
              value={form.notes}
              onChange={handleChange}
              rows={2}
              maxLength={2000}
            />
          </label>

          <button
            className="create-btn"
            type="submit"
            disabled={submitting || !eligible.length}
          >
            {submitting ? "Creating..." : "Create Intervention"}
          </button>
        </form>
      </section>

      <section className="intervention-list-card">
        <div className="list-heading">
          <div>
            <h2>Intervention Records</h2>
            <span>
              {interventions.length} of {totalInterventions} shown
            </span>
          </div>

          <div className="list-controls">
            <label>
              Status
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                <option value="">All</option>
                <option value="OPEN">Open</option>
                <option value="IN_PROGRESS">In progress</option>
                <option value="COMPLETED">Completed</option>
                <option value="CANCELLED">Cancelled</option>
              </select>
            </label>

            <label>
              Acting as
              <select
                value={actorRole}
                onChange={(event) => setActorRole(event.target.value)}
              >
                {ROLES.map((role) => (
                  <option key={role.value} value={role.value}>
                    {role.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        {loading ? (
          <p className="empty-state">Loading interventions...</p>
        ) : interventions.length === 0 ? (
          <p className="empty-state">No interventions found.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Intervention ID</th>
                  <th>Employee</th>
                  <th>Type</th>
                  <th>Assigned To</th>
                  <th>Created</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {interventions.map((item) => {
                  const id = item.intervention_id;
                  const next = NEXT_STATUSES[item.status] ?? [];

                  return (
                    <Fragment key={id}>
                      <tr>
                        <td className="mono">{id}</td>
                        <td>{item.employee_id}</td>
                        <td>{formatLabel(item.intervention_type)}</td>
                        <td>{formatLabel(item.assigned_to_role)}</td>
                        <td>
                          {item.created_at
                            ? new Date(item.created_at).toLocaleString()
                            : "—"}
                        </td>
                        <td>
                          <span className={`status-pill ${item.status.toLowerCase()}`}>
                            {item.status}
                          </span>
                        </td>
                        <td className="row-actions">
                          {next.map((option) => (
                            <button
                              key={option.status}
                              className={option.className}
                              disabled={updatingId === id}
                              onClick={() => handleStatusChange(id, option.status)}
                            >
                              {option.label}
                            </button>
                          ))}
                          <button
                            className="history-btn"
                            onClick={() => toggleHistory(id)}
                          >
                            {expandedId === id ? "Hide history" : "History"}
                          </button>
                        </td>
                      </tr>

                      {expandedId === id && (
                        <tr className="history-row">
                          <td colSpan="7">
                            {!events[id] ? (
                              "Loading history..."
                            ) : (
                              <ol className="event-list">
                                {events[id].map((event) => (
                                  <li key={event.event_id}>
                                    <strong>{formatLabel(event.event_type)}</strong>{" "}
                                    by {formatLabel(event.actor_role)} ·{" "}
                                    {new Date(event.event_at).toLocaleString()}
                                    {event.notes && <span> · {event.notes}</span>}
                                  </li>
                                ))}
                              </ol>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default InterventionManagement;
