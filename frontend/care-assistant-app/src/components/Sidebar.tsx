import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  CalendarCheck,
  ListChecks,
  Heart,
  Users,
} from "lucide-react";

import { useSidebar } from "../context/useSidebar";

const navItems = [
  { title: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
  { title: "Routines", path: "/routines", icon: CalendarCheck },
  { title: "Activity Catalog", path: "/activities-catalog", icon: ListChecks },
  { title: "Elderly", path: "/elderly", icon: Users },
];

export function Sidebar() {
  const {
    collapsed,
    mobileOpen,
    closeMobile,
  } = useSidebar();

  return (
    <>
      {/* BACKDROP MOBILE */}
      {mobileOpen && (
        <div
          onClick={closeMobile}
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
        />
      )}

      <aside
        className={`
          fixed top-0 left-0 h-screen bg-white border-r border-border-soft
          flex flex-col z-50 transition-all duration-300

          ${collapsed ? "w-20" : "w-64"}

          ${mobileOpen ? "translate-x-0" : "-translate-x-full"}
          md:translate-x-0
        `}
      >

        {/* HEADER */}
        <div
          className={`
            p-4 flex items-center
            ${collapsed ? "justify-center" : "gap-3"}
          `}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue shrink-0">
            <Heart className="h-5 w-5 text-white" />
          </div>

          {!collapsed && (
            <div>
              <h1 className="text-lg font-bold text-neutral-dark">
                CareFlow
              </h1>

              <p className="text-xs text-neutral-light">
                Caregiver Assistant
              </p>
            </div>
          )}
        </div>

        {/* NAVIGATION */}
        <nav className="flex-1 px-2 py-4 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.title}
              to={item.path}
              onClick={closeMobile}
              className={({ isActive }) =>
                `
                flex items-center rounded-xl text-sm mb-1 transition-all duration-200

                ${collapsed ? "justify-center px-2 py-3" : "gap-3 px-3 py-2"}

                ${
                  isActive
                    ? "bg-blue-light text-blue-main font-semibold"
                    : "text-zinc-500 hover:bg-hover"
                }
              `
              }
            >
              <item.icon className="h-5 w-5 shrink-0" />

              {!collapsed && <span>{item.title}</span>}
            </NavLink>
          ))}
        </nav>

        {/* FOOTER */}
        {!collapsed && (
          <div className="p-4 text-xs text-neutral-light text-center">
            Made with Love for caregivers
          </div>
        )}
      </aside>
    </>
  );
}
