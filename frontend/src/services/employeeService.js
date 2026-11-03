import api from "./api";

export const getEmployees = async (params = {}) => {
  const response = await api.get("/api/employees", { params });
  return response.data;
};

export const getEmployeeAssessment = async (employeeId) => {
  const response = await api.get(
    `/api/employees/${employeeId}/assessment`
  );
  return response.data;
};

export const getEmployeeReview = async (employeeId) => {
  const response = await api.get(
    `/api/employees/${employeeId}/review`
  );
  return response.data;
};

export const getPendingReviews = async (params = {}) => {
  const response = await api.get("/api/reviews/pending", { params });
  return response.data;
};

export const createEmployeeReview = async (employeeId, reviewData) => {
  const response = await api.post(
    `/api/employees/${employeeId}/review`,
    reviewData
  );
  return response.data;
};