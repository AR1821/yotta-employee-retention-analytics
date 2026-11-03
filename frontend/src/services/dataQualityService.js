import api from "./api";

export const getDataQualitySummary = async () => {
  const response = await api.get("/api/data-quality/summary");
  return response.data;
};
