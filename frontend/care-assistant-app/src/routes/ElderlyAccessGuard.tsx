import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useHasElderlyProfiles } from "../hooks/useHasElderlyProfiles";

function canAccessWithoutElderly(pathname: string) {
  return (
    pathname === "/elderly" ||
    pathname.startsWith("/elderly/") ||
    pathname === "/elderly-create" ||
    pathname === "/elderly-required"
  );
}

export function ElderlyAccessGuard() {
  const location = useLocation();
  const { hasElderlyProfiles, loading } = useHasElderlyProfiles(location.pathname);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-app-background text-neutral-light">
        Cargando perfiles...
      </div>
    );
  }

  if (!hasElderlyProfiles && !canAccessWithoutElderly(location.pathname)) {
    return <Navigate to="/elderly-required" replace />;
  }

  return <Outlet />;
}
