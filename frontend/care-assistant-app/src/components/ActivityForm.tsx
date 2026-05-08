import { useForm } from "react-hook-form";
import { useState, useEffect } from "react";
import type { Category, CategoryCreate } from "../types/Category";
import type { ActivityWithProgramData } from "../types/Activity";
import { CategoryInlineForm } from "./CategoryInlineForm";


type Props = {
  categories: Category[];
  onSubmit: (data: ActivityWithProgramData) => void;
  onCreateCategory: (data: CategoryCreate) => Promise<number>;
  onCancel: () => void;
  defaultValues?: ActivityWithProgramData;
};

export function ActivityForm({
  categories,
  onSubmit,
  onCreateCategory,
  onCancel,
  defaultValues,
}: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<ActivityWithProgramData>({
    defaultValues: {
      is_active: true,
      frequency: "daily",
      ...defaultValues,
    },
  });

  const isActive = watch("is_active");
  const [showCategoryForm, setShowCategoryForm] = useState(false);

  useEffect(() => {
    if (defaultValues) {
      reset({
        is_active: true,
        frequency: "daily",
        ...defaultValues,
      });
    }
  }, [defaultValues, reset]);

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

        {/* COLUMNA IZQUIERDA */}
        <div className="space-y-5">

          {/* TÍTULO */}
          <div>
            <label className="block text-sm font-medium text-slate-dark mb-1">
              Título
            </label>
            <input
              {...register("title", { required: true })}
              placeholder="Ej. Medicación Matutina"
              className="w-full border border-border-soft rounded-xl p-3"
            />
            {errors.title && <span className="text-red-500 text-xs">El título es requerido</span>}
          </div>

          {/* DESCRIPCIÓN */}
          <div>
            <label className="block text-sm font-medium text-slate-dark mb-1">
              Descripción
            </label>
            <textarea
              {...register("description", { required: true })}
              placeholder="Agregar detalles..."
              className="w-full border border-border-soft rounded-xl p-3"
            />
            {errors.description && <span className="text-red-500 text-xs">La descripción es requerida</span>}
          </div>

          {/* CATEGORÍA */}
          <div>
            <label className="block text-sm font-medium text-slate-dark mb-1">
              Categoría
            </label>

            <div className="flex gap-2">
              <select
                {...register("category", { required: true, valueAsNumber: true })}
                className="flex-1 border border-border-soft rounded-xl p-3"
              >
                <option value="">Seleccione</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>

              <button
                type="button"
                onClick={() => setShowCategoryForm(!showCategoryForm)}
                className="bg-white text-neutral-light px-4 rounded-xl border-border-soft border"
              >
                +
              </button>
            </div>

            {errors.category && (
              <span className="text-red-500 text-xs">La categoría es requerida</span>
            )}

            {/* Inline */}
            {showCategoryForm && (
              <CategoryInlineForm
                onCreate={async (data) => {
                  const newId = await onCreateCategory(data);
                  setValue("category", newId);
                  setShowCategoryForm(false);
                }}
                onCancel={() => setShowCategoryForm(false)}
              />
            )}
          </div>
        </div>

        {/* COLUMNA DERECHA */}
        <div className="space-y-5">

          {/* FECHA + HORA */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-dark mb-1">
                Fecha
              </label>
              <input
                type="date"
                {...register("date")}
                className="w-full border border-border-soft rounded-xl p-3"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-dark mb-1">
                Hora
              </label>
              <input
                type="time"
                {...register("time")}
                className="w-full border border-border-soft rounded-xl p-3"
              />
            </div>
          </div>

          {/* FRECUENCIA */}
          <div>
            <label className="block text-sm font-medium text-slate-dark mb-1">
              Frecuencia
            </label>
            <select
              {...register("frequency")}
              className="w-full border border-border-soft rounded-xl p-3"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
          </div>

          {/* SWITCH */}
          <div className="bg-app-background border border-border-soft rounded-xl p-4 flex items-center justify-between">
            <span className="text-sm text-slate-dark">
              Activar actividad
            </span>

            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setValue("is_active", e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:bg-blue transition"></div>
            </label>
          </div>

        </div>

      </div>


      {/* BOTONES */}
      <div className="flex justify-end gap-3 pt-4">
        <button
          type="button"
          className="px-4 py-2 border border-border-soft rounded-xl"
          onClick={onCancel}
        >
          Cancelar
        </button>

        <button
          type="submit"
          className="bg-blue text-white px-5 py-2 rounded-xl"
        >
          Guardar
        </button>
      </div>
    </form>
  );
}