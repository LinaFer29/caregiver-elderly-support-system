import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { useSelectedElderly } from "../context/useSelectedElderly";
import { createRoutine, getRoutineCatalog } from "../services/routine.services";
import type { RoutineCatalogActivity } from "../types/Routine";
import { RoutineForm, type RoutineFormValues } from "../components/RoutineForm";

function getInitials(firstName: string, lastName: string) {
  return `${firstName[0] ?? ""}${lastName[0] ?? ""}`.toUpperCase();
}

export default function CreateRoutinePage() {
  const navigate = useNavigate();
  const { selectedElderly } = useSelectedElderly();

  const [activities, setActivities] = useState<RoutineCatalogActivity[]>([]);
  const [loadingActivities, setLoadingActivities] = useState(true);

  useEffect(() => {
    async function loadCatalog() {
      try {
        setLoadingActivities(true);
        const data = await getRoutineCatalog();
        setActivities(data);
      } catch (error) {
        console.error(error);
        toast.error("Error cargando catálogo de actividades");
      } finally {
        setLoadingActivities(false);
      }
    }

    void loadCatalog();
  }, []);

  const onSubmit = async (values: RoutineFormValues) => {
    if (!selectedElderly) {
      toast.error("Debes seleccionar un adulto mayor");
      return;
    }

    try {
      const response = await createRoutine({
        elderly_id: selectedElderly.id,
        start_date: values.start_date,
        end_date: values.end_date || values.start_date,
        activities: values.activities,
      });

      toast.success(
        `Rutina creada correctamente. Se generaron ${response.scheduled_occurrences_count} actividades programadas.`,
        {
          position: "top-center",
          duration: 3000,
          style: {
            background: "#4BB543",
            color: "#fff",
          },
        }
      );

      navigate("/routines");
    } catch (error) {
      console.error(error);
      toast.error("No fue posible crear la rutina", {
        position: "top-center",
        duration: 3000,
        style: {
          background: "#780606",
          color: "#fff",
        },
      });
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-neutral-dark">Crear Rutina</h1>
        <p className="text-neutral-light mt-1">
          Seleccione actividades y configure una rutina diaria para el adulto mayor.
        </p>
      </div>

      {!selectedElderly && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <p className="font-semibold text-yellow-800">No hay adulto mayor seleccionado</p>
            <p className="text-sm text-yellow-700 mt-1">
              Selecciona un perfil para poder crear y asignar una rutina.
            </p>
          </div>

          <button
            onClick={() => navigate("/elderly")}
            className="px-4 py-2 rounded-xl bg-yellow-600 text-white hover:opacity-90 transition"
          >
            Ir a adultos mayores
          </button>
        </div>
      )}

      {selectedElderly && (
        <div className="bg-white border border-border-soft rounded-2xl p-4 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue/10 text-blue font-semibold">
            {getInitials(selectedElderly.first_name, selectedElderly.last_name)}
          </span>
          <div>
            <p className="text-sm text-neutral-light">Rutina para</p>
            <p className="font-semibold text-neutral-dark">
              {selectedElderly.first_name} {selectedElderly.last_name}
            </p>
          </div>
        </div>
      )}

      <RoutineForm
        activities={activities}
        loadingActivities={loadingActivities}
        disabled={!selectedElderly}
        submitLabel="Crear rutina"
        onSubmit={onSubmit}
        onCancel={() => navigate("/routines")}
      />
    </div>
  );
}
