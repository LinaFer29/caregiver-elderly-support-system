import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CalendarDays, Clock3, Activity, ListChecks, PlusCircle } from "lucide-react";
import { useSelectedElderly } from "../context/useSelectedElderly";
import { getRoutinesByElderly } from "../services/routine.services";
import type { RoutineByDate } from "../types/Routine";

function todayISO() {
  const d = new Date();
  const m = `${d.getMonth() + 1}`.padStart(2, "0");
  const day = `${d.getDate()}`.padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { selectedElderly } = useSelectedElderly();

  const [routines, setRoutines] = useState<RoutineByDate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      if (!selectedElderly) {
        setRoutines([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const data = await getRoutinesByElderly(selectedElderly.id);
        setRoutines(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }

    void loadData();
  }, [selectedElderly]);

  const summary = useMemo(() => {
    const activeRoutines = routines.filter((routine) =>
      routine.items.some((item) => item.is_active)
    ).length;

    const todayItems = routines.find((routine) => routine.date === todayISO())?.items ?? [];

    const upcoming = routines
      .flatMap((routine) =>
        routine.items.map((item) => ({
          ...item,
          date: routine.date,
        }))
      )
      .sort((a, b) => `${a.date} ${a.time}`.localeCompare(`${b.date} ${b.time}`))
      .slice(0, 5);

    return {
      activeRoutines,
      todayCount: todayItems.length,
      upcoming,
    };
  }, [routines]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-neutral-dark">Dashboard</h1>
        <p className="text-neutral-light mt-1">Resumen del adulto mayor seleccionado.</p>
      </div>

      {!selectedElderly && (
        <div className="bg-white border border-dashed border-border-soft rounded-2xl p-10 text-center">
          <p className="text-lg font-semibold text-neutral-dark">No hay adulto mayor seleccionado.</p>
          <p className="text-sm text-neutral-light mt-1">Selecciona un perfil desde la barra superior para ver su dashboard.</p>
          <button
            onClick={() => navigate("/elderly")}
            className="mt-5 px-5 py-2.5 rounded-xl bg-blue text-white hover:opacity-90"
          >
            Ir a adultos mayores
          </button>
        </div>
      )}

      {selectedElderly && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white border border-border-soft rounded-2xl p-4">
              <p className="text-xs text-neutral-light">Adulto mayor</p>
              <p className="font-semibold text-neutral-dark mt-1">{selectedElderly.first_name} {selectedElderly.last_name}</p>
            </div>
            <div className="bg-white border border-border-soft rounded-2xl p-4">
              <p className="text-xs text-neutral-light">Nivel dependencia</p>
              <p className="font-semibold text-neutral-dark mt-1 capitalize">{selectedElderly.dependency_level}</p>
            </div>
            <div className="bg-white border border-border-soft rounded-2xl p-4">
              <p className="text-xs text-neutral-light">Rutinas activas</p>
              <p className="font-semibold text-neutral-dark mt-1">{loading ? "..." : summary.activeRoutines}</p>
            </div>
            <div className="bg-white border border-border-soft rounded-2xl p-4">
              <p className="text-xs text-neutral-light">Actividades de hoy</p>
              <p className="font-semibold text-neutral-dark mt-1">{loading ? "..." : summary.todayCount}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <section className="bg-white border border-border-soft rounded-2xl p-5">
              <h2 className="text-lg font-semibold text-neutral-dark">Próximas actividades</h2>
              {loading ? (
                <p className="text-neutral-light mt-3">Cargando...</p>
              ) : summary.upcoming.length === 0 ? (
                <p className="text-neutral-light mt-3">No hay actividades programadas.</p>
              ) : (
                <div className="mt-3 space-y-2">
                  {summary.upcoming.map((item, idx) => (
                    <div key={`${item.activity_id}-${item.date}-${item.time}-${idx}`} className="border border-border-soft rounded-xl p-3 flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium text-neutral-dark">{item.title}</p>
                        <p className="text-xs text-neutral-light">{item.category_name}</p>
                      </div>
                      <div className="text-xs text-neutral-light text-right">
                        <p className="inline-flex items-center gap-1 justify-end"><Clock3 className="h-3.5 w-3.5" /> {item.time.slice(0,5)}</p>
                        <p className="inline-flex items-center gap-1 justify-end"><CalendarDays className="h-3.5 w-3.5" /> {item.date}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="bg-white border border-border-soft rounded-2xl p-5">
              <h2 className="text-lg font-semibold text-neutral-dark">Rutinas activas</h2>
              {loading ? (
                <p className="text-neutral-light mt-3">Cargando...</p>
              ) : routines.length === 0 ? (
                <p className="text-neutral-light mt-3">No hay rutinas registradas.</p>
              ) : (
                <div className="mt-3 space-y-2">
                  {routines.slice(0, 5).map((routine) => (
                    <button
                      key={routine.id}
                      onClick={() => navigate(`/routines/${encodeURIComponent(routine.id)}`)}
                      className="w-full text-left border border-border-soft rounded-xl p-3 hover:bg-hover transition"
                    >
                      <p className="font-medium text-neutral-dark">{routine.date}</p>
                      <p className="text-xs text-neutral-light">{routine.activities_count} actividades</p>
                    </button>
                  ))}
                </div>
              )}
            </section>
          </div>

          <section className="bg-white border border-border-soft rounded-2xl p-5">
            <h2 className="text-lg font-semibold text-neutral-dark">Accesos rápidos</h2>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button onClick={() => navigate("/routines/new")} className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-blue text-white hover:opacity-90">
                <PlusCircle className="h-4 w-4" /> Crear rutina
              </button>
              <button onClick={() => navigate("/activities-catalog")} className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-border-soft text-neutral-dark hover:bg-hover">
                <ListChecks className="h-4 w-4" /> Ver catálogo
              </button>
              <button onClick={() => navigate("/routines")} className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-border-soft text-neutral-dark hover:bg-hover">
                <Activity className="h-4 w-4" /> Ver rutinas
              </button>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
