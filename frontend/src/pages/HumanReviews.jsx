import { useEffect, useState } from "react";
import {
  ClipboardCheck,
  Search,
  RefreshCw,
  CheckCircle,
  Clock,
  X,
} from "lucide-react";
import {
  getPendingReviews,
  getEmployeeAssessment,
  createEmployeeReview,
} from "../services/employeeService";
import "./HumanReviews.css";

const PAGE_SIZE = 50;

function getErrorMessage(err, fallback) {
  if (!err.response) {
    return "Cannot reach the backend. Make sure uvicorn is running.";
  }
  return err.response.data?.detail || err.message || fallback;
}

// CSV fields arrive as "A|B|C" strings; empty means no entries.
function splitCodes(value) {
  return String(value ?? "")
    .split("|")
    .map((code) => code.trim())
    .filter(Boolean);
}

function formatCode(code) {
  return code.replaceAll("_", " ").toLowerCase();
}

function HumanReviews() {
  const [employees, setEmployees] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [existingReview, setExistingReview] = useState(null);

  const [decision, setDecision] = useState("SUPPORT_NEEDED");
  const [reviewerRole, setReviewerRole] = useState("HR_PARTNER");
  const [notes, setNotes] = useState("");

  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [panelError, setPanelError] = useState("");
  const [message, setMessage] = useState("");

  const loadEmployees = async (searchTerm = search) => {
    try {
      setLoading(true);
      setError("");

      const data = await getPendingReviews({
        limit: PAGE_SIZE,
        offset: 0,
        search: searchTerm.trim() || undefined,
      });

      setEmployees(data.employees);
      setTotal(data.total);
    } catch (err) {
      setError(getErrorMessage(err, "Unable to load pending reviews."));
    } finally {
      setLoading(false);
    }
  };

  const loadMore = async () => {
    try {
      setLoadingMore(true);

      const data = await getPendingReviews({
        limit: PAGE_SIZE,
        offset: employees.length,
        search: search.trim() || undefined,
      });

      setEmployees((current) => [...current, ...data.employees]);
      setTotal(data.total);
    } catch (err) {
      setError(getErrorMessage(err, "Unable to load more reviews."));
    } finally {
      setLoadingMore(false);
    }
  };

  // Debounce search so typing does not send a request per keystroke.
  useEffect(() => {
    const timer = setTimeout(() => loadEmployees(search), 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const openReview = async (employeeId) => {
    try {
      setDetailLoading(true);
      setPanelError("");
      setMessage("");
      setExistingReview(null);
      setSelected(null);

      // The pending queue only lists unreviewed assessments, so there is no
      // saved review to fetch; a duplicate submit is still rejected with 409.
      const assessmentData = await getEmployeeAssessment(employeeId);

      setSelected(assessmentData);
      setDecision("SUPPORT_NEEDED");
      setReviewerRole("HR_PARTNER");
      setNotes("");
    } catch (err) {
      setPanelError(getErrorMessage(err, "Unable to load assessment."));
    } finally {
      setDetailLoading(false);
    }
  };

  const submitReview = async (event) => {
    event.preventDefault();

    if (!selected) return;

    try {
      setSubmitting(true);
      setPanelError("");
      setMessage("");

      const result = await createEmployeeReview(selected.employee_id, {
        decision,
        reviewed_by_role: reviewerRole,
        review_notes: notes.trim() || null,
      });

      setExistingReview({
        ...result.review,
        review_notes: notes.trim() || null,
      });
      setMessage(`Review saved for ${selected.employee_id}.`);

      await loadEmployees();
    } catch (err) {
      setPanelError(getErrorMessage(err, "Unable to save review."));
    } finally {
      setSubmitting(false);
    }
  };

  const closeReview = () => {
    setSelected(null);
    setExistingReview(null);
    setPanelError("");
    setDetailLoading(false);
  };

  return (
    <div className="reviews-page">
      <header className="reviews-header">
        <div>
          <p className="reviews-eyebrow">ASSESSMENT GOVERNANCE</p>
          <h1>Human Reviews</h1>
          <p>Review support assessments before any intervention is created.</p>
        </div>

        <button className="review-refresh" onClick={() => loadEmployees()}>
          <RefreshCw size={16} />
          Refresh
        </button>
      </header>

      <div className="review-summary">
        <div className="review-summary-icon">
          <ClipboardCheck size={22} />
        </div>
        <div>
          <strong>{total.toLocaleString()}</strong>
          <span>
            {search.trim()
              ? `Pending assessments matching "${search.trim()}"`
              : "Assessments awaiting review"}
          </span>
        </div>
      </div>

      <div className="review-search">
        <Search size={18} />
        <input
          placeholder="Search employee ID..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>

      {error && <div className="review-error">{error}</div>}
      {message && <div className="review-success">{message}</div>}

      {loading ? (
        <p className="review-loading">Loading review records...</p>
      ) : (
        <section className="review-table-card">
          <div className="review-table-heading">
            <h2>Pending Assessments</h2>
            <span>
              Showing {employees.length.toLocaleString()} of{" "}
              {total.toLocaleString()} · highest scores first
            </span>
          </div>

          <div className="review-table-scroll">
            <table className="review-table">
              <thead>
                <tr>
                  <th>Employee ID</th>
                  <th>Support Score</th>
                  <th>Priority</th>
                  <th>Review Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {employees.map(({ employee_id, assessment }) => (
                  <tr key={employee_id}>
                    <td>{employee_id}</td>
                    <td>{assessment.support_priority_score}/100</td>
                    <td>
                      <span
                        className={`review-priority ${assessment.priority_level.toLowerCase()}`}
                      >
                        {assessment.priority_level}
                      </span>
                    </td>
                    <td>
                      <span className="pending-label">
                        <Clock size={13} />
                        Pending
                      </span>
                    </td>
                    <td>
                      <button
                        className="start-review"
                        onClick={() => openReview(employee_id)}
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                ))}

                {employees.length === 0 && (
                  <tr>
                    <td colSpan="5" className="review-empty">
                      No pending assessments found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {employees.length < total && (
            <div className="review-load-more">
              <button onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? "Loading..." : `Load ${PAGE_SIZE} more`}
              </button>
            </div>
          )}
        </section>
      )}

      {(selected || detailLoading || panelError) && (
        <div className="review-overlay" onClick={closeReview}>
          <aside
            className="review-panel"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="review-panel-header">
              <div>
                <p>HUMAN ASSESSMENT REVIEW</p>
                <h2>{selected?.employee_id ?? "Loading..."}</h2>
              </div>

              <button onClick={closeReview} className="review-close">
                <X size={20} />
              </button>
            </div>

            {detailLoading && <p>Loading assessment...</p>}
            {panelError && <div className="review-error panel">{panelError}</div>}

            {selected && (
              <>
                <ReviewAssessmentSummary data={selected} />

                {existingReview ? (
                  <div className="existing-review">
                    <CheckCircle size={20} />
                    <div>
                      <strong>Review recorded</strong>
                      <p>Decision: {existingReview.decision}</p>
                      <p>Reviewer: {existingReview.reviewed_by_role}</p>
                      <p>
                        Notes: {existingReview.review_notes || "No notes"}
                      </p>
                      {existingReview.reviewed_at && (
                        <p>
                          Reviewed:{" "}
                          {new Date(existingReview.reviewed_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <form className="review-form" onSubmit={submitReview}>
                    <h3>Record Your Decision</h3>

                    <label htmlFor="decision">Review decision</label>
                    <select
                      id="decision"
                      value={decision}
                      onChange={(event) => setDecision(event.target.value)}
                    >
                      <option value="SUPPORT_NEEDED">Support Needed</option>
                      <option value="FOLLOW_UP">Follow Up</option>
                      <option value="NO_ACTION">No Action</option>
                    </select>

                    <label htmlFor="reviewerRole">Reviewer role</label>
                    <select
                      id="reviewerRole"
                      value={reviewerRole}
                      onChange={(event) => setReviewerRole(event.target.value)}
                    >
                      <option value="HR_PARTNER">HR Partner</option>
                      <option value="MANAGER">Manager</option>
                      <option value="PEOPLE_PARTNER">People Partner</option>
                    </select>

                    <label htmlFor="reviewNotes">Review notes</label>
                    <textarea
                      id="reviewNotes"
                      value={notes}
                      onChange={(event) => setNotes(event.target.value)}
                      placeholder="Explain the reasoning behind your decision..."
                      rows={4}
                      maxLength={2000}
                    />

                    <p className="review-decision-hint">
                      {decision === "NO_ACTION"
                        ? "NO_ACTION blocks intervention creation for this assessment version."
                        : "This decision allows an intervention to be created next."}
                    </p>

                    <button
                      type="submit"
                      disabled={submitting}
                      className="submit-review"
                    >
                      {submitting ? "Saving..." : "Save Human Review"}
                    </button>
                  </form>
                )}
              </>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}

function ReviewAssessmentSummary({ data }) {
  const assessment = data.assessment;
  const reasons = splitCodes(assessment.reason_codes);
  const limitations = splitCodes(assessment.data_limitations);
  const assignment = data.current_assignment;

  const components = [
    { label: "Engagement", value: assessment.engagement_component_score, max: 40 },
    { label: "Workload", value: assessment.workload_component_score, max: 40 },
    { label: "Career", value: assessment.career_component_score, max: 20 },
  ];

  return (
    <section className="review-assessment-summary">
      <h3>Assessment Summary</h3>

      <div className="review-score">
        <strong>{assessment.support_priority_score}</strong>
        <span>/ 100</span>
        <span
          className={`review-priority ${assessment.priority_level.toLowerCase()}`}
        >
          {assessment.priority_level}
        </span>
      </div>

      {assignment && (
        <p>
          {assignment.role_title} · {assignment.team_name} ·{" "}
          {assignment.department}
        </p>
      )}

      <div className="review-components">
        {components.map((item) => (
          <div key={item.label} className="review-component">
            <div className="review-component-label">
              <span>{item.label}</span>
              <span>
                {item.value} / {item.max}
              </span>
            </div>
            <div className="review-component-track">
              <div
                className="review-component-fill"
                style={{ width: `${(Number(item.value) / item.max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <h4>Reason codes</h4>
      {reasons.length ? (
        <ul className="review-codes">
          {reasons.map((code) => (
            <li key={code}>{formatCode(code)}</li>
          ))}
        </ul>
      ) : (
        <p>No reason codes triggered.</p>
      )}

      <h4>Data limitations</h4>
      {limitations.length ? (
        <ul className="review-codes limitation">
          {limitations.map((code) => (
            <li key={code}>{formatCode(code)}</li>
          ))}
        </ul>
      ) : (
        <p>No data limitations recorded.</p>
      )}

      <p>
        Rule version {assessment.rule_version} · Feature cutoff{" "}
        {assessment.feature_cutoff_date}
      </p>

      <p className="review-human-note">
        Review the available evidence and limitations before recording a
        decision. A score alone is not sufficient justification.
      </p>
    </section>
  );
}

export default HumanReviews;
