import { useEffect, useMemo, useState } from "react";
import {
  Search,
  Eye,
  Users,
  RefreshCw,
  X,
  AlertCircle,
} from "lucide-react";
import {
  getEmployees,
  getEmployeeAssessment,
} from "../services/employeeService";
import "./EmployeeExplorer.css";

const PAGE_SIZE = 1000;
// Rendering all 10,000 rows at once makes the page slow and very tall.
const ROWS_PER_VIEW = 200;

function getRows(data) {
  if (Array.isArray(data)) return data;
  return data?.employees ?? data?.items ?? data?.results ?? [];
}

function getAssessment(employee) {
  return employee.assessment ?? employee;
}

function getPriority(employee) {
  const assessment = getAssessment(employee);
  return assessment.priority_level ?? assessment.reviewed_priority ?? "UNKNOWN";
}

function getScore(employee) {
  const assessment = getAssessment(employee);
  return assessment.support_priority_score ?? assessment.reviewed_score ?? 0;
}

function getReviewStatus(employee) {
  // Saved reviews live in PostgreSQL; the CSV status is never updated.
  if (employee.review_decision) {
    return `REVIEWED · ${employee.review_decision}`;
  }

  const assessment = getAssessment(employee);
  return assessment.assessment_status ??
    (assessment.human_reviewed ? "REVIEWED" : "PENDING_HUMAN_REVIEW");
}

function getReasonCodes(assessment) {
  const value = assessment.reason_codes;
  if (Array.isArray(value)) return value;
  if (typeof value === "string" && value.trim()) {
    return value.split("|").filter(Boolean);
  }
  return [];
}

function getLimitations(assessment) {
  const value = assessment.data_limitations;
  if (Array.isArray(value)) return value;
  if (typeof value === "string" && value.trim()) {
    return value.split("|").filter(Boolean);
  }
  return [];
}

function PriorityBadge({ priority }) {
  return (
    <span className={`priority-badge ${priority.toLowerCase()}`}>
      {priority}
    </span>
  );
}

function EmployeeExplorer() {
  const [employees, setEmployees] = useState([]);
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("ALL");
  const [visibleCount, setVisibleCount] = useState(ROWS_PER_VIEW);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");

  const loadEmployees = async () => {
    try {
      setLoading(true);
      setError("");

      let allEmployees = [];
      let offset = 0;

      while (true) {
        const response = await getEmployees({
          limit: PAGE_SIZE,
          offset,
        });

        const rows = getRows(response);
        allEmployees = [...allEmployees, ...rows];

        if (rows.length < PAGE_SIZE) break;
        offset += PAGE_SIZE;
      }

      setEmployees(allEmployees);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.message ||
        "Unable to load employees."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEmployees();
  }, []);

  const filteredEmployees = useMemo(() => {
    const query = search.trim().toLowerCase();

    return employees.filter((employee) => {
      const matchesSearch =
        !query ||
        String(employee.employee_id ?? "").toLowerCase().includes(query) ||
        String(employee.department ?? "").toLowerCase().includes(query) ||
        String(employee.role_title ?? employee.role ?? "").toLowerCase().includes(query) ||
        String(employee.team_name ?? employee.team ?? "").toLowerCase().includes(query);

      const matchesPriority =
        priority === "ALL" || getPriority(employee) === priority;

      return matchesSearch && matchesPriority;
    });
  }, [employees, search, priority]);

  const openEmployee = async (employeeId) => {
    try {
      setDetailLoading(true);
      setDetailError("");
      setSelectedEmployee(null);

      const data = await getEmployeeAssessment(employeeId);
      setSelectedEmployee(data);
    } catch (err) {
      setDetailError(
        err.response?.data?.detail ||
        err.message ||
        "Unable to load employee details."
      );
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetails = () => {
    setSelectedEmployee(null);
    setDetailError("");
  };

  return (
    <div className="employee-page">
      <header className="employee-header">
        <div>
          <p className="employee-eyebrow">WORKFORCE MANAGEMENT</p>
          <h1>Employee Explorer</h1>
          <p>Explore employee records and explainable support assessments.</p>
        </div>

        <button className="employee-refresh" onClick={loadEmployees}>
          <RefreshCw size={16} />
          Refresh
        </button>
      </header>

      <section className="employee-summary">
        <div className="employee-summary-icon">
          <Users size={22} />
        </div>
        <div>
          <strong>{employees.length.toLocaleString()}</strong>
          <span>Employees loaded</span>
        </div>
      </section>

      <section className="employee-toolbar">
        <div className="employee-search">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search employee ID, department, role or team..."
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setVisibleCount(ROWS_PER_VIEW);
            }}
          />
        </div>

        <select
          value={priority}
          onChange={(event) => {
            setPriority(event.target.value);
            setVisibleCount(ROWS_PER_VIEW);
          }}
        >
          <option value="ALL">All priorities</option>
          <option value="HIGH">High priority</option>
          <option value="MODERATE">Moderate priority</option>
          <option value="ROUTINE">Routine priority</option>
        </select>
      </section>

      {loading && (
        <div className="employee-message">Loading employee records...</div>
      )}

      {error && (
        <div className="employee-error">
          <AlertCircle size={18} />
          {error}
          <button onClick={loadEmployees}>Retry</button>
        </div>
      )}

      {!loading && !error && (
        <section className="employee-table-card">
          <div className="employee-table-heading">
            <h2>Employee Records</h2>
            <span>
              Showing {Math.min(visibleCount, filteredEmployees.length).toLocaleString()} of{" "}
              {filteredEmployees.length.toLocaleString()} results
            </span>
          </div>

          <div className="employee-table-scroll">
            <table className="employee-table">
              <thead>
                <tr>
                  <th>Employee ID</th>
                  <th>Department</th>
                  <th>Role</th>
                  <th>Team</th>
                  <th>Support Score</th>
                  <th>Priority</th>
                  <th>Review Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {filteredEmployees.slice(0, visibleCount).map((employee) => (
                  <tr key={employee.employee_id}>
                    <td className="employee-id">
                      {employee.employee_id}
                    </td>
                    <td>{employee.department ?? "—"}</td>
                    <td>{employee.role_title ?? employee.role ?? "—"}</td>
                    <td>{employee.team_name ?? employee.team ?? "—"}</td>
                    <td>{getScore(employee)}/100</td>
                    <td>
                      <PriorityBadge priority={getPriority(employee)} />
                    </td>
                    <td>
                      <span className="review-status">
                        {getReviewStatus(employee)}
                      </span>
                    </td>
                    <td>
                      <button
                        className="view-employee"
                        onClick={() => openEmployee(employee.employee_id)}
                      >
                        <Eye size={15} />
                        View
                      </button>
                    </td>
                  </tr>
                ))}

                {filteredEmployees.length === 0 && (
                  <tr>
                    <td colSpan="8" className="empty-table">
                      No matching employee records found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {visibleCount < filteredEmployees.length && (
            <div className="employee-show-more">
              <button
                onClick={() => setVisibleCount((count) => count + ROWS_PER_VIEW)}
              >
                Show {ROWS_PER_VIEW} more
              </button>
            </div>
          )}
        </section>
      )}

      {(detailLoading || selectedEmployee || detailError) && (
        <div className="employee-overlay" onClick={closeDetails}>
          <aside
            className="employee-detail-panel"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="detail-header">
              <div>
                <p>EMPLOYEE DETAILS</p>
                <h2>
                  {selectedEmployee?.employee_id ?? "Loading..."}
                </h2>
              </div>
              <button className="close-detail" onClick={closeDetails}>
                <X size={20} />
              </button>
            </div>

            {detailLoading && (
              <p className="employee-message">Loading assessment...</p>
            )}

            {detailError && (
              <div className="employee-error">{detailError}</div>
            )}

            {selectedEmployee && (
              <EmployeeDetails data={selectedEmployee} />
            )}
          </aside>
        </div>
      )}
    </div>
  );
}

function EmployeeDetails({ data }) {
  const assessment = data.assessment ?? data;
  const reasons = getReasonCodes(assessment);
  const limitations = getLimitations(assessment);
  const assignment = data.current_assignment ?? data;

  const components = [
    {
      name: "Engagement",
      value: assessment.engagement_component_score ?? 0,
      max: 40,
    },
    {
      name: "Workload",
      value: assessment.workload_component_score ?? 0,
      max: 40,
    },
    {
      name: "Career progression",
      value: assessment.career_component_score ?? 0,
      max: 20,
    },
  ];

  return (
    <div className="employee-details">
      <section className="detail-section">
        <h3>Employee Information</h3>
        <DetailRow label="Employee ID" value={data.employee_id} />
        <DetailRow label="Department" value={assignment.department} />
        <DetailRow label="Role" value={assignment.role_title} />
        <DetailRow label="Job level" value={assignment.job_level} />
        <DetailRow label="Team" value={assignment.team_name} />
        <DetailRow label="Hire date" value={data.hire_date} />
      </section>

      <section className="detail-section">
        <h3>Support Assessment</h3>

        <div className="detail-score">
          <strong>
            {assessment.support_priority_score ??
              assessment.reviewed_score ??
              0}
          </strong>
          <span>/ 100</span>
        </div>

        <PriorityBadge
          priority={
            assessment.priority_level ??
            assessment.reviewed_priority ??
            "UNKNOWN"
          }
        />

        <p className="detail-muted">
          Rule version: {assessment.rule_version ?? "—"}
        </p>
        <p className="detail-muted">
          Feature cutoff: {assessment.feature_cutoff_date ?? "—"}
        </p>

        {components.map((component) => (
          <div className="component-score" key={component.name}>
            <div>
              <span>{component.name}</span>
              <strong>
                {component.value} / {component.max}
              </strong>
            </div>
            <div className="component-track">
              <div
                className="component-fill"
                style={{
                  width: `${Math.min(
                    100,
                    (Number(component.value) / component.max) * 100
                  )}%`,
                }}
              />
            </div>
          </div>
        ))}
      </section>

      <section className="detail-section">
        <h3>Reason Codes</h3>
        {reasons.length ? (
          <ul className="detail-list">
            {reasons.map((reason) => (
              <li key={reason}>{reason.replaceAll("_", " ")}</li>
            ))}
          </ul>
        ) : (
          <p className="detail-muted">No reason codes recorded.</p>
        )}
      </section>

      <section className="detail-section">
        <h3>Data Limitations</h3>
        {limitations.length ? (
          <ul className="detail-list limitations">
            {limitations.map((item) => (
              <li key={item}>{item.replaceAll("_", " ")}</li>
            ))}
          </ul>
        ) : (
          <p className="detail-muted">No limitations recorded.</p>
        )}
      </section>

      <section className="detail-section">
        <h3>Human Review</h3>
        <DetailRow
          label="Status"
          value={assessment.assessment_status ?? "Not provided"}
        />
        <DetailRow
          label="Review required"
          value={
            assessment.human_review_required === undefined
              ? "Not provided"
              : assessment.human_review_required
                ? "Yes"
                : "No"
          }
        />
        <DetailRow
          label="Reviewed"
          value={
            assessment.human_reviewed === undefined
              ? "Not provided"
              : assessment.human_reviewed
                ? "Yes"
                : "No"
          }
        />
      </section>

      <p className="detail-disclaimer">
        This assessment is a supportive signal, not an attrition probability
        or an automated employment decision.
      </p>
    </div>
  );
}

function DetailRow({ label, value }) {
  return (
    <div className="detail-row">
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
    </div>
  );
}

export default EmployeeExplorer;