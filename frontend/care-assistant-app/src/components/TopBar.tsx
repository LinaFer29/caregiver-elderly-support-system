import { Bell, User, Menu } from "lucide-react";
import { useAuth } from "../context/useAuth";
import { useNavigate } from "react-router-dom";
import { useSidebar } from "../context/useSidebar";

export function TopBar() {
  const {
    toggleCollapsed,
    toggleMobile,
  } = useSidebar();

  const handleSidebar = () => {
    if (window.innerWidth < 768) {
      toggleMobile();
    } else {
      toggleCollapsed();
    }
  };

  const navigate = useNavigate();
  const { logout } = useAuth();

  return (
    <header className="flex h-16 items-center justify-between border-b border-border-soft bg-white px-4">

      <div className="flex items-center gap-3">
        <button
          onClick={handleSidebar}
          className="h-10 w-10 rounded-xl border border-border-soft flex items-center justify-center hover:bg-hover transition"
        >
          <Menu className="h-5 w-5 text-neutral-dark" />
        </button>

        <div>
          <h2 className="font-semibold text-neutral-dark">
            Dashboard
          </h2>
        </div>
      </div>

      <div className="flex items-center gap-4">

        <button className="relative hover:text-white">
          <Bell className="h-5 w-5 text-neutral-light" />
        </button>

        <div className="flex items-center gap-2 py-4">
          <div className="h-9 w-9 rounded-full bg-blue-light flex items-center justify-center text-blue font-semibold">
            <User></User>
          </div>
          <div className="hidden md:block">
            <p className="text-sm font-semibold text-neutral-dark leading-none">Maria Costa</p>
            <p className="text-xs text-muted-foreground text-neutral-light mt-0.5">Caregiver</p>
          </div>
        </div>
        <button
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Cerrar sesión
        </button>

      </div>
    </header>
  );
}