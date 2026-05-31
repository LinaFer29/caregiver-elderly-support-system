import { httpClient } from "./httpClient";

const ACCESS_KEY = "access";
const REFRESH_KEY = "refresh";

export const authService = {

  // LOGIN
  async login(data: { identifier: string; password: string }) {
    const response = await httpClient.post("/login/", {
      identifier: data.identifier,
      password: data.password,
    });

    const { access, refresh } = response.data;

    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);

    // setear token inmediatamente en axios
    httpClient.defaults.headers.Authorization = `Bearer ${access}`;

    return response.data;
  },

  // REGISTER
  async register(data: {
    username: string;
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    role: string;
    caregiver_type: string;
  }) {
    const response = await httpClient.post("/register/", data);
    return response.data;
  },

  // REFRESH TOKEN
  async refreshToken() {
    const refresh = localStorage.getItem(REFRESH_KEY);

    if (!refresh) throw new Error("No refresh token");

    const response = await httpClient.post("/refresh/", {
      refresh,
    });

    localStorage.setItem(ACCESS_KEY, response.data.access);

    return response.data.access;
  },

  // LOGOUT
  logout() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },

  // GET TOKEN
  getAccessToken() {
    return localStorage.getItem(ACCESS_KEY);
  },

  // IS AUTHENTICATED
  isAuthenticated() {
    return !!localStorage.getItem(ACCESS_KEY);
  },

  // CURRENT USER PROFILE
  async me() {
    const response = await httpClient.get("/me/");
    return response.data as {
      id: number;
      username: string;
      email: string;
      role: string;
    };
  },
};
