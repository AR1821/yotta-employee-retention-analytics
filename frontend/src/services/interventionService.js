import api from "./api";

export const getInterventions = async (params = {}) => {
  const response = await api.get("/api/interventions", { params });
  return response.data;
};

export const getIntervention = async (interventionId) => {
  const response = await api.get(
    `/api/interventions/${interventionId}`
  );
  return response.data;
};

export const getEligibleReviews = async () => {
  const response = await api.get("/api/reviews/eligible");
  return response.data;
};

export const createIntervention = async (interventionData) => {
  const response = await api.post(
    "/api/interventions",
    interventionData
  );
  return response.data;
};

export const updateInterventionStatus = async (
  interventionId,
  statusData
) => {
  const response = await api.patch(
    `/api/interventions/${interventionId}/status`,
    statusData
  );
  return response.data;
};