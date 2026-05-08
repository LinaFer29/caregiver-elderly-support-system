import { createContext } from "react";

type SidebarContextType = {
  collapsed: boolean;
  mobileOpen: boolean;
  toggleCollapsed: () => void;
  toggleMobile: () => void;
  closeMobile: () => void;
};

export const SidebarContext = createContext<SidebarContextType | null>(null);
