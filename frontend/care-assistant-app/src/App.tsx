import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom"
import { ActivitiesPage } from "./pages/ActivitiesPage"
import { ActivityFormPage } from "./pages/ActivityFormPage"
import { Toaster } from "react-hot-toast"
import { MainLayout } from "./components/layouts/MainLayout"
import CategoriesPage from "./pages/CategoriesPage"
import ActivityDetailPage from "./pages/ActivityDetailPage"
import RegisterPage from "./pages/RegisterPage"
import LoginPage from "./pages/LoginPage"
import { PublicRoute } from "./routes/PublicRoutes"
import { PrivateRoute } from "./routes/PrivateRoutes"
import RegisterElderlyPage from "./pages/RegisterElderlyPage"
import ElderlyPage from "./pages/ElderlyPage"

function App() {
  return (
    <BrowserRouter>
      <div className="w-full">
        <Routes>
          {/* PUBLIC ROUTES (sin layout) */}
          <Route element={<PublicRoute />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<RegisterPage />} />
          </Route>

          {/* PRIVATE ROUTES (con layout) */}
          <Route element={<PrivateRoute />}>
            <Route element={<MainLayout />}>
              <Route path="/" element={<Navigate to="/activities" />} />
              <Route path="/activities" element={<ActivitiesPage />} />
              <Route path="/activities/:id" element={<ActivityDetailPage />} />
              <Route path="/activity-create" element={<ActivityFormPage />} />
              <Route path="/activity/:id" element={<ActivityFormPage />} />
              <Route path="/categories" element={<CategoriesPage />} />
              <Route path="/elderly" element={<ElderlyPage />} />
              <Route path="/elderly-create" element={<RegisterElderlyPage />} />
              <Route path="/elderly/:id" element={<RegisterElderlyPage />} />
            </Route>
          </Route>
        </Routes>
        <Toaster />
      </div>
    </BrowserRouter>
  );
}

export default App;