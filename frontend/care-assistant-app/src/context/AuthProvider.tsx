import { useEffect, useState } from "react";
import { AuthContext } from "./AuthContext";
import { authService } from "../services/auth.service";
import type { LoginData } from "../types/Login";
import { httpClient } from "../services/httpClient";

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem("access");
    
        if (token) {
          httpClient.defaults.headers.Authorization = `Bearer ${token}`;
          setIsAuthenticated(true);
        }
    
        setLoading(false);
      }, []);
  
    const login = async (data: LoginData) => {
      await authService.login(data);
      setIsAuthenticated(true);
    };
  
    const logout = () => {
      authService.logout();
      setIsAuthenticated(false);
    };
  
    return (
      <AuthContext.Provider value={{ isAuthenticated, loading, login, logout }}>
        {children}
      </AuthContext.Provider>
    );
  }