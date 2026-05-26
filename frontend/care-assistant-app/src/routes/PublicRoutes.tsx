import { Navigate, Outlet } from "react-router-dom";
import { isAuthenticated } from "../utils/auth";

export function PublicRoute() {
  return !isAuthenticated() ? <Outlet /> : <Navigate to="/dashboard" replace />;
}
