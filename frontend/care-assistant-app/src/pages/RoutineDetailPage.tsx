import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CalendarDays, Clock3, Repeat2, Trash2, Pencil } from "lucide-react";
import { toast } from "react-hot-toast";
import { deleteRoutine, getRoutineById } from "../services/routine.services";
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

export default function RoutineDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();

  const [routine, setRoutine] = useState<RoutineByDate | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    async function loadRoutine() {
      if (!id) return;
      try {
        setLoading(true);
        const data = await getRoutineById(decodeURIComponent(id));
        setRoutine(data);
      } catch (error) {
        console.error(error);
        toast.error("No fue posible cargar la rutina");
        navigate("/routines");
      } finally {
        setLoading(false);
      }
    }

    void loadRoutine();
  }, [id, navigate]);

  const generalStatusLabel = useMemo(() => {
    if (!routine) return "";
    if (routine.general_status === "completed") return "Completada";
    if (routine.general_status === "mixed") return "Mixta";
    return "Activa";
  }, [routine]);

  const generalStatusClass = useMemo(() => {
    if (!routine) return "bg-gray-100 text-gray-700";
    if (routine.general_status === "completed") return "bg-green-100 text-green-700";
    if (routine.general_status === "mixed") return "bg-yellow-100 text-yellow-700";
    return "bg-blue-100 text-blue-700";
  }, [routine]);

  const handleDelete = async () => {
    if (!routine) return;
    try {
      setDeleting(true);
      await deleteRoutine(routine.id);
      toast.success("Rutina eliminada correctamente");
      navigate("/routines");
    } catch (error) {
      console.error(error);
      toast.error("No fue posible eliminar la rutina");
    } finally {
      setDeleting(false);
      setConfirmOpen(false);
    }
  };

  if (loading) return <p className="text-neutral-light">Cargando rutina...</p>;
  if (!routine) return null;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <button
        onClick={() => navigate("/routines")}
        className="inline-flex items-center gap-2 text-neutral-light hover:text-neutral-dark"
      >
        <ArrowLeft className="h-4 w-4" />
        Volver a rutinas
      </button>

      <div className="bg-white border border-border-soft rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-neutral-dark">Rutina del {formatDate(routine.date)}</h1>
          <p className="text-neutral-light mt-1">
            Adulto mayor: {routine.elderly.first_name} {routine.elderly.last_name}
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span className="px-2 py-1 rounded-lg bg-blue-50 text-blue">{routine.activities_count} actividades</span>
            <span className={`px-2 py-1 rounded-lg ${generalStatusClass}`}>{generalStatusLabel}</span>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => navigate(`/routines/${encodeURIComponent(routine.id)}/edit`)}
            className="inline-flex items-center gap-2 bg-blue text-white px-4 py-2 rounded-xl hover:opacity-90"
          >
            <Pencil className="h-4 w-4" />
            Editar rutina
          </button>
          <button
            onClick={() => setConfirmOpen(true)}
            className="inline-flex items-center gap-2 bg-red-500 text-white px-4 py-2 rounded-xl hover:opacity-90"
          >
            <Trash2 className="h-4 w-4" />
            Eliminar
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {routine.items.map((item, index) => (
          <article key={`${item.activity_id}-${item.time}-${index}`} className="bg-white border border-border-soft rounded-2xl p-4">
            <div className="flex items-start justify-between gap-2">
              <h2 className="font-semibold text-neutral-dark">{item.title}</h2>
              <span className={`text-xs px-2 py-1 rounded-lg ${item.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                {item.is_active ? "Activa" : "Inactiva"}
              </span>
            </div>

            <p className="text-sm text-neutral-light mt-1">{item.description}</p>

            <div className="mt-3 flex flex-wrap gap-3 text-xs text-neutral-light">
              <span className="inline-flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" /> {item.time.slice(0, 5)}</span>
              <span className="inline-flex items-center gap-1"><Repeat2 className="h-3.5 w-3.5" /> {item.frequency}</span>
              <span className="inline-flex items-center gap-1"><CalendarDays className="h-3.5 w-3.5" /> {routine.date}</span>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              <span
                className="inline-flex text-xs px-2 py-1 rounded-lg"
                style={{ backgroundColor: `${item.category_color}20`, color: item.category_color }}
              >
                {item.category_name}
              </span>

              {item.status && (
                <span className={`inline-flex text-xs px-2 py-1 rounded-lg ${
                  item.status === "completed"
                    ? "bg-green-100 text-green-700"
                    : item.status === "missed"
                      ? "bg-red-100 text-red-600"
                      : "bg-yellow-100 text-yellow-700"
                }`}>
                  {item.status === "completed" ? "Cumplida" : item.status === "missed" ? "Perdida" : "Pendiente"}
                </span>
              )}
            </div>
          </article>
        ))}
      </div>

      {confirmOpen && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center px-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full border border-border-soft">
            <h3 className="text-lg font-semibold text-neutral-dark">Eliminar rutina</h3>
            <p className="text-sm text-neutral-light mt-2">
              Esta accion eliminara las programaciones y asignaciones de esta rutina. ¿Deseas continuar?
            </p>

            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setConfirmOpen(false)}
                className="px-4 py-2 rounded-xl border border-border-soft text-neutral-dark"
                disabled={deleting}
              >
                Cancelar
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 rounded-xl bg-red-500 text-white disabled:opacity-60"
                disabled={deleting}
              >
                {deleting ? "Eliminando..." : "Eliminar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
