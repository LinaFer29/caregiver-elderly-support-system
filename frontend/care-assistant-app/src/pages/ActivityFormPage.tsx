import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "react-hot-toast";
import { ActivityForm } from "../components/ActivityForm";
import type { Category, CategoryCreate } from "../types/Category";
import type { ActivityWithProgramData } from "../types/Activity";
import { getActivityById } from "../services/activities.services";
import { createCategory, getAllCategories } from "../services/categories.services";
import { createActivityWithProgram, getProgramById, updateActivityWithProgram } from "../services/programs.services";
import { useSelectedElderly } from "../context/useSelectedElderly";

export function ActivityFormPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [activityData, setActivityData] = useState<ActivityWithProgramData | undefined>();
  const navigate = useNavigate();
  const params = useParams();
  const { selectedElderly } = useSelectedElderly();

  useEffect(() => {
    async function loadCategories() {
      try {
        const data = await getAllCategories();
        setCategories(data);
      } catch (error) {
        console.error(error);
      }
    }
    loadCategories();
  }, []);

  useEffect(() => {
    async function loadActivity() {
      if (params.id) {
        try {
          const activityResponse = await getActivityById(Number(params.id));
          const programResponse = await getProgramById(Number(params.id));


          setActivityData({
            title: activityResponse.title,
            description: activityResponse.description,
            category: activityResponse.category,
            date: programResponse.date,
            time: programResponse.time,
            frequency: programResponse.frequency,
            is_active: programResponse.is_active,
          });
        } catch (error) {
          console.error("Error cargando actividad:", error);
        }
      }
    }
    loadActivity();
  }, [params.id]);

  const onSubmit = async (data: ActivityWithProgramData) => {
    console.log("Datos del formulario:", data);
    console.log("Is active:", data.is_active);

    if (!selectedElderly) {
      toast.error("Debes seleccionar un adulto mayor");
      return;
    }
    try {
      if (params.id) {
        // Update Activity with Program in one step
        await updateActivityWithProgram(Number(params.id), data);
        toast.success("Actividad actualizada exitosamente", {
          position: "top-center",
          duration: 3000,
          style: {
            background: "#4BB543",
            color: "#fff",
          }
        });
        navigate(`/activities/${params.id}`);
      } else {
        // Create new Activity with Program in one step
        const payload = {
          ...data,
          elderly_id: selectedElderly.id,
        }

        const newActivityProgram = await createActivityWithProgram(payload);
        const activityId = newActivityProgram.activity_id;;
        toast.success("Actividad creada exitosamente", {
          position: "top-center",
          duration: 3000,
          style: {
            background: "#4BB543",
            color: "#fff",
          }
        });
        navigate(`/activities/${activityId}`);
      }
    } catch (error) {
      console.error("Error al guardar actividad:", error);
      toast.error("Hubo un error al guardar la actividad", {
        position: "top-center",
        duration: 3000,
        style: {
          background: "#780606",
          color: "#fff",
        }
      });
    };
  }

  const handleCreateCategory = async (data: CategoryCreate): Promise<number> => {
    try {
      const newCategory = await createCategory(data);
      const updatedCategories = await getAllCategories();
      setCategories(updatedCategories);

      return newCategory.id;
    } catch (error) {
      console.error(error);
      throw new Error("Error al crear categoría");
    }
  };

  const handleCancel = () => {
    if (params.id) {
      navigate(`/activities/${params.id}`); // vuelve al detail
    } else {
      navigate("/activities"); // vuelve a lista
    }
  };

  return (

    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-dark">
          {params.id ? "Editar Actividad" : "Crear Actividad"}
        </h1>
        <p className="text-slate-light mt-1">
          {params.id ? "Edita la" : "Crea una nueva"} actividad para las rutinas diarias
        </p>
      </div>

      <div className="max-w-6xl mx-auto bg-white p-6 rounded-2xl border border-border-soft">
        {/* Form */}
        <ActivityForm
          categories={categories}
          onSubmit={onSubmit}
          onCreateCategory={handleCreateCategory}
          onCancel={handleCancel}
          defaultValues={activityData}
        />
      </div>
    </div>
  )
}

export default ActivityFormPage