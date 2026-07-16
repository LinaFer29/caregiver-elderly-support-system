import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CalendarDays, Clock3, Repeat2, PlusCircle } from "lucide-react";
import { useSelectedElderly } from "../context/useSelectedElderly";
import { getRoutinesByElderly } from "../services/routine.services";
import type { RoutineByDate } from "../types/Routine";

function formatDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  return date.toLocaleDateString("es-CO", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatFrequency(value: string) {
  const labels: Record<string, string> = {
    once: "Una vez",
    daily: "Diaria",
    weekly: "Semanal",
    monthly: "Mensual",
  };

  return labels[value] ?? value;
}

export default function RoutinesPage() {
  const navigate = useNavigate();
  const { selectedElderly } = useSelectedElderly();

  const [routines, setRoutines] = useState<RoutineByDate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadRoutines() {
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

    void loadRoutines();
  }, [selectedElderly]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-neutral-dark">Rutinas</h1>
          <p className="text-neutral-light mt-1">Rutinas creadas para el adulto mayor seleccionado.</p>
        </div>

        <button
          onClick={() => navigate("/routines/new")}
          className="inline-flex items-center justify-center gap-2 bg-blue text-white px-5 py-2.5 rounded-xl hover:opacity-90 transition"
        >
          <PlusCircle className="h-4 w-4" />
          Crear rutina
        </button>
      </div>

      {!selectedElderly && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-2xl p-5">
          <p className="font-semibold text-yellow-800">No hay adulto mayor seleccionado</p>
          <p className="text-sm text-yellow-700 mt-1">
            Selecciona un adulto mayor para visualizar sus rutinas.
          </p>
        </div>
      )}

      {loading && selectedElderly && <p className="text-neutral-light">Cargando rutinas...</p>}

      {!loading && selectedElderly && routines.length === 0 && (
        <div className="bg-white border border-dashed border-border-soft rounded-2xl p-10 text-center">
          <p className="text-lg font-semibold text-neutral-dark">Aún no hay rutinas creadas.</p>
          <p className="text-sm text-neutral-light mt-1">
            Crea una rutina seleccionando actividades del catálogo del sistema.
          </p>
          <button
            onClick={() => navigate("/routines/new")}
            className="mt-5 inline-flex items-center justify-center gap-2 bg-blue text-white px-5 py-2.5 rounded-xl hover:opacity-90"
          >
            <PlusCircle className="h-4 w-4" />
            Crear primera rutina
          </button>
        </div>
      )}

      {!loading && selectedElderly && routines.length > 0 && (
        <div className="space-y-4">
          {routines.map((routine) => (
            <section key={routine.id} className="bg-white border border-border-soft rounded-2xl p-5">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h2 className="text-lg font-semibold text-neutral-dark capitalize">
                  {formatDate(routine.date)}
                </h2>
                <div className="flex gap-2 items-center">
                  <span className="text-xs px-3 py-1 rounded-lg bg-blue-50 text-blue">
                    {routine.elderly.first_name} {routine.elderly.last_name}
                  </span>
                  <button
                    onClick={() => navigate(`/routines/${encodeURIComponent(routine.id)}`)}
                    className="text-xs px-3 py-1 rounded-lg border border-border-soft text-neutral-dark hover:bg-hover"
                  >
                    Ver detalle
                  </button>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                {routine.items.map((item) => (
                  <article key={`${routine.date}-${item.activity_id}-${item.time}`} className="border border-border-soft rounded-xl p-4">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-neutral-dark">{item.title}</h3>
                      <span
                        className={`text-xs px-2 py-1 rounded-lg ${
                          item.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"
                        }`}
                      >
                        {item.is_active ? "Activa" : "Inactiva"}
                      </span>
                    </div>
                    <p className="text-sm text-neutral-light mt-1 line-clamp-2">{item.description}</p>

                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-neutral-light">
                      <span className="inline-flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" /> {item.time.slice(0, 5)}</span>
                      <span className="inline-flex items-center gap-1"><Repeat2 className="h-3.5 w-3.5" /> {formatFrequency(item.frequency)}</span>
                      <span className="inline-flex items-center gap-1"><CalendarDays className="h-3.5 w-3.5" /> {routine.date}</span>
                    </div>

                    <span
                      className="inline-flex mt-3 text-xs px-2 py-1 rounded-lg"
                      style={{
                        backgroundColor: `${item.category_color}20`,
                        color: item.category_color,
                      }}
                    >
                      {item.category_name}
                    </span>

                    {item.additional_instructions?.trim() && (
                      <div className="mt-3 rounded-xl border border-border-soft bg-app-background p-3">
                        <p className="text-xs font-semibold text-neutral-dark">
                          Instrucciones para el adulto mayor
                        </p>
                        <p className="text-sm text-neutral-light mt-1 line-clamp-3 whitespace-pre-wrap">
                          {item.additional_instructions}
                        </p>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
