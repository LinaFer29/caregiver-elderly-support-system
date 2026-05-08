import { createContext } from "react";
import type { LoginData } from "../types/Login";

export type AuthContextType = {
  isAuthenticated: boolean;
  loading: boolean;
  login: (data: LoginData) => Promise<void>;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextType | null>(null);