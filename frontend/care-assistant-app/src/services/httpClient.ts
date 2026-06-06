import axios from 'axios';
import { API_BASE_URL } from '../config/env';

export const httpClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

httpClient.interceptors.request.use((config) => {
  const requestUrl = String(config.url || "");
  const isAuthRoute =
    requestUrl.includes("/login/") ||
    requestUrl.includes("/register/") ||
    requestUrl.includes("/refresh/");
  const token = localStorage.getItem("access");

  if (token && !isAuthRoute) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});


httpClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const requestUrl = String(originalRequest?.url || "");
    const isAuthRoute =
      requestUrl.includes("/login/") ||
      requestUrl.includes("/register/") ||
      requestUrl.includes("/refresh/");

    // No intentar refresh ni redirigir en errores de autenticación inicial
    if (isAuthRoute) {
      return Promise.reject(error);
    }

    // Si es 401 y no se ha reintentado
    if (error.response?.status === 401 && !originalRequest?._retry) {
      originalRequest._retry = true;

      try {
        const refresh = localStorage.getItem("refresh");

        // si no hay refresh → logout directo
        if (!refresh) {
          localStorage.clear();
          window.location.href = "/login";
          return Promise.reject(error);
        }

        // pedir nuevo access token
        const res = await axios.post(`${API_BASE_URL}/refresh/`, {
          refresh,
        });

        const newAccess = res.data.access;

        // guardar nuevo token
        localStorage.setItem("access", newAccess);

        // actualizar header global
        httpClient.defaults.headers.Authorization = `Bearer ${newAccess}`;

        // actualizar request original
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;

        return httpClient(originalRequest);

      } catch (err) {
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(err);
      }
    }

    return Promise.reject(error);
  }
);
