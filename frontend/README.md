# Frontend

React + Vite dashboard for the Yotta Employee Retention Analytics API.
See the [main README](../README.md) for full setup.

```bash
cp .env.example .env   # VITE_API_BASE_URL=http://127.0.0.1:8000
npm install
npm run dev            # http://localhost:5173
npm run build          # production build in dist/
```

| Path | Page |
|---|---|
| `src/pages/Dashboard.jsx` | KPIs and charts (`/api/dashboard/summary`) |
| `src/pages/EmployeeExplorer.jsx` | Search, filter and per-employee assessment |
| `src/pages/HumanReviews.jsx` | Review queue and decision form |
| `src/pages/InterventionManagement.jsx` | Create and track interventions |
| `src/pages/DataQuality.jsx` | Validation reports and edge cases |
| `src/services/` | Axios client and API calls |
