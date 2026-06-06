import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "react-hot-toast";
import { useSelectedElderly } from "../context/useSelectedElderly";
import { getRoutineCatalog, getRoutineById, updateRoutine } from "../services/routine.services";
import type { RoutineByDate, RoutineCatalogActivity } from "../types/Routine";
import { RoutineForm, type RoutineFormValues } from "../components/RoutineForm";

function getInitials(firstName: string, lastName: string) {
  return `${firstName[0] ?? ""}${lastName[0] ?? ""}`.toUpperCase();
}

export default function EditRoutinePage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const { selectedElderly } = useSelectedElderly();

  const [activities, setActivities] = useState<RoutineCatalogActivity[]>([]);
  const [loadingActivities, setLoadingActivities] = useState(true);
  const [routine, setRoutine] = useState<RoutineByDate | null>(null);
  const [loadingRoutine, setLoadingRoutine] = useState(true);

  useEffect(() => {
    async function loadData() {
      if (!id) return;
      try {
        setLoadingActivities(true);
        setLoadingRoutine(true);

        const [catalog, routineData] = await Promise.all([
          getRoutineCatalog(),
          getRoutineById(decodeURIComponent(id)),
        ]);

        setActivities(catalog);
        setRoutine(routineData);
      } catch (error) {
        console.error(error);
        toast.error("No fue posible cargar la rutina");
        navigate("/routines");
      } finally {
        setLoadingActivities(false);
        setLoadingRoutine(false);
      }
    }

    void loadData();
  }, [id, navigate]);

  const onSubmit = async (values: RoutineFormValues) => {
    if (!selectedElderly || !routine) {
      toast.error("Debes seleccionar un adulto mayor");
      return;
    }

    try {
      const updatedRoutine = await updateRoutine(routine.id, {
        elderly_id: selectedElderly.id,
        start_date: values.start_date,
        end_date: values.end_date || values.start_date,
        activities: values.activities,
      });

      toast.success("Rutina actualizada correctamente", {
        position: "top-center",
        duration: 3000,
        style: {
          background: "#4BB543",
          color: "#fff",
        },
      });

      navigate(`/routines/${encodeURIComponent(updatedRoutine.id)}`);
    } catch (error) {
      console.error(error);
      toast.error("No fue posible actualizar la rutina", {
        position: "top-center",
        duration: 3000,
        style: {
          background: "#780606",
          color: "#fff",
        },
      });
    }
  };

  if (loadingRoutine) {
    return <p className="text-neutral-light">Cargando rutina...</p>;
  }

  if (!routine) return null;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-neutral-dark">Editar Rutina</h1>
        <p className="text-neutral-light mt-1">
          Actualiza actividades, horarios y configuraciones de la rutina.
        </p>
      </div>

      {!selectedElderly && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-2xl p-5">
          <p className="font-semibold text-yellow-800">No hay adulto mayor seleccionado</p>
          <p className="text-sm text-yellow-700 mt-1">Selecciona un perfil para editar rutinas.</p>
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
        submitLabel="Guardar cambios"
        initialStartDate={routine.date}
        initialEndDate={routine.date}
        initialActivities={routine.items.map((item) => ({
          activity_id: item.activity_id,
          time: item.time.slice(0, 5),
          frequency: item.frequency,
          is_active: item.is_active,
          additional_instructions: item.additional_instructions ?? "",
        }))}
        dateRangeMode="single"
        onSubmit={onSubmit}
        onCancel={() => navigate(`/routines/${encodeURIComponent(routine.id)}`)}
      />
    </div>
  );
}
