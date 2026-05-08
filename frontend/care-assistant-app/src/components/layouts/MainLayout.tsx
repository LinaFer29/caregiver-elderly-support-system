import { Sidebar } from "../Sidebar";
import { Outlet } from "react-router-dom";
import { TopBar } from "../TopBar";
import { SidebarProvider } from "../../context/SidebarProvider";
import { useSidebar } from "../../context/useSidebar";



function LayoutContent() {
    const { collapsed } = useSidebar();

    return (
        <div className="min-h-screen bg-app-background">

            <Sidebar />

            <div
                className={`
                    flex flex-col min-h-screen transition-all duration-300
                    ${collapsed ? "md:ml-20" : "md:ml-64"}
              `}
            >
                <TopBar />

                <main className="flex-1 p-6 bg-app-background overflow-y-auto">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}

export function MainLayout() {
    return (
        <SidebarProvider>
            <LayoutContent />
        </SidebarProvider>
    );
}