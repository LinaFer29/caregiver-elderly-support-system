import { Navigate, Outlet } from "react-router-dom";
import { authService } from "../services/auth.service";


export function PrivateRoute() {
  const isAuth = authService.isAuthenticated();

  if (!isAuth) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}