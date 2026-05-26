import { useEffect, useMemo, useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CalendarDays, Clock3, Repeat, CheckSquare, ChevronDown, ChevronRight } from "lucide-react";
import { DynamicIcon } from "./DynamicIcon";
import type { RoutineCatalogActivity, RoutineFrequency } from "../types/Routine";

const formSchema = z.object({
  date: z.string().min(1, "La fecha es requerida"),
  activities: z
    .array(
      z.object({
        activity_id: z.number(),
        time: z.string().min(1, "La hora es requerida"),
        frequency: z.enum(["daily", "weekly"], { message: "Selecciona una frecuencia" }),
        is_active: z.boolean(),
      })
    )
    .min(1, "Selecciona al menos una actividad"),
});

type RoutineFormValues = z.infer<typeof formSchema>;

type ActivityConfig = {
  time: string;
  frequency: RoutineFrequency;
  is_active: boolean;
};

type Props = {
  activities: RoutineCatalogActivity[];
  loadingActivities: boolean;
  disabled?: boolean;
  submitLabel: string;
  initialDate?: string;
  initialActivities?: Array<{
    activity_id: number;
    time: string;
    frequency: RoutineFrequency;
    is_active: boolean;
  }>;
  onSubmit: (values: RoutineFormValues) => Promise<void>;
  onCancel: () => void;
};

function groupByCategory(activities: RoutineCatalogActivity[]) {
  return activities.reduce<Record<string, { color: string; icon: string; items: RoutineCatalogActivity[] }>>((acc, activity) => {
    const key = activity.category_name || "Sin categoría";
    if (!acc[key]) {
      acc[key] = {
        color: activity.category_color || "#0C77A9",
        icon: activity.category_icon || "HelpCircle",
        items: [],
      };
    }
    acc[key].items.push(activity);
    return acc;
  }, {});
}

export function RoutineForm({
  activities,
  loadingActivities,
  disabled = false,
  submitLabel,
  initialDate,
  initialActivities,
  onSubmit,
  onCancel,
}: Props) {
  const [selectedIds, setSelectedIds] = useState<number[]>(initialActivities?.map((item) => item.activity_id) ?? []);
  const [activityConfigs, setActivityConfigs] = useState<Record<number, ActivityConfig>>(() => {
    const map: Record<number, ActivityConfig> = {};
    for (const item of initialActivities ?? []) {
      map[item.activity_id] = {
        time: item.time,
        frequency: item.frequency,
        is_active: item.is_active,
      };
    }
    return map;
  });
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({});

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
    setError,
    clearErrors,
  } = useForm<RoutineFormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      date: initialDate ?? "",
      activities: initialActivities ?? [],
    },
  });

  const grouped = useMemo(() => groupByCategory(activities), [activities]);

  useEffect(() => {
    const formActivities = selectedIds.map((id) => ({
      activity_id: id,
      time: activityConfigs[id]?.time ?? "",
      frequency: activityConfigs[id]?.frequency ?? "daily",
      is_active: activityConfigs[id]?.is_active ?? true,
    }));

    setValue("activities", formActivities, { shouldValidate: true });
  }, [selectedIds, activityConfigs, setValue]);

  const toggleCategory = (categoryName: string) => {
    setOpenCategories((prev) => ({
      ...prev,
      [categoryName]: !prev[categoryName],
    }));
  };

  const toggleActivity = (activityId: number) => {
    setSelectedIds((prev) => {
      const isSelected = prev.includes(activityId);

      if (isSelected) {
        const next = prev.filter((id) => id !== activityId);
        if (next.length > 0) {
          clearErrors("activities");
        }
        return next;
      }

      setActivityConfigs((cfg) => ({
        ...cfg,
        [activityId]: cfg[activityId] ?? {
          time: "",
          frequency: "daily",
          is_active: true,
        },
      }));
      clearErrors("activities");
      return [...prev, activityId];
    });
  };

  const updateActivityConfig = (activityId: number, patch: Partial<ActivityConfig>) => {
    setActivityConfigs((prev) => ({
      ...prev,
      [activityId]: {
        ...(prev[activityId] ?? { time: "", frequency: "daily", is_active: true }),
        ...patch,
      },
    }));
  };

  const submitHandler = async (values: RoutineFormValues) => {
    if (selectedIds.length === 0) {
      setError("activities", { message: "Selecciona al menos una actividad" });
      return;
    }

    const hasMissingTime = selectedIds.some((id) => !activityConfigs[id]?.time);
    if (hasMissingTime) {
      setError("activities", { message: "Cada actividad seleccionada debe tener hora configurada" });
      return;
    }

    await onSubmit(values);
  };

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-6">
      <section className="bg-white border border-border-soft rounded-2xl p-5">
        <h2 className="text-lg font-semibold text-neutral-dark mb-4">Fecha global de la rutina</h2>
        <div className="max-w-sm">
          <label className="text-sm text-neutral-dark flex items-center gap-2">
            <CalendarDays className="h-4 w-4" /> Fecha inicio
          </label>
          <input
            type="date"
            {...register("date")}
            disabled={disabled}
            className="w-full mt-1 border border-border-soft rounded-lg p-3"
          />
          {errors.date && <p className="text-red-500 text-xs mt-1">{errors.date.message}</p>}
        </div>
      </section>

      <section className="bg-white border border-border-soft rounded-2xl p-5">
        <div className="flex items-center justify-between gap-2 flex-wrap mb-4">
          <h2 className="text-lg font-semibold text-neutral-dark">Actividades disponibles</h2>
          <span className="text-xs px-3 py-1 rounded-lg bg-blue-50 text-blue">
            {selectedIds.length} seleccionada(s)
          </span>
        </div>

        {loadingActivities && <p className="text-neutral-light">Cargando actividades...</p>}

        {!loadingActivities && activities.length === 0 && (
          <div className="border border-dashed border-border-soft rounded-xl p-8 text-center">
            <p className="font-semibold text-neutral-dark">No hay actividades disponibles todavía.</p>
            <p className="text-sm text-neutral-light mt-1">Las actividades son administradas por el sistema.</p>
          </div>
        )}

        {!loadingActivities && activities.length > 0 && (
          <div className="space-y-4">
            {Object.entries(grouped).map(([categoryName, group]) => (
              <div key={categoryName} className="border border-border-soft rounded-xl overflow-hidden">
                <button
                  type="button"
                  onClick={() => toggleCategory(categoryName)}
                  className="w-full px-4 py-3 bg-app-background flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-md" style={{ backgroundColor: `${group.color}20` }}>
                      <DynamicIcon name={group.icon} size={15} style={{ color: group.color }} />
                    </span>
                    <span className="font-semibold text-neutral-dark">{categoryName}</span>
                  </div>
                  {openCategories[categoryName] ? (
                    <ChevronDown className="h-4 w-4 text-neutral-light" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-neutral-light" />
                  )}
                </button>

                  {(openCategories[categoryName] ?? true) && (
                  <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {group.items.map((activity) => {
                      const selected = selectedIds.includes(activity.id);
                      const cfg = activityConfigs[activity.id] ?? {
                        time: "",
                        frequency: "daily" as RoutineFrequency,
                        is_active: true,
                      };

                      return (
                        <div
                          key={activity.id}
                          className={`border rounded-xl p-4 transition ${selected ? "border-blue bg-blue-50" : "border-border-soft bg-white"}`}
                        >
                          <button
                            type="button"
                            onClick={() => toggleActivity(activity.id)}
                            disabled={disabled}
                            className={`w-full text-left ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <h3 className="font-semibold text-neutral-dark">{activity.title}</h3>
                              <CheckSquare className={`h-4 w-4 ${selected ? "text-blue" : "text-neutral-light"}`} />
                            </div>
                            <p className="text-sm text-neutral-light mt-1 line-clamp-2">{activity.description}</p>
                          </button>

                          {selected && (
                            <div className="mt-4 space-y-3 border-t border-blue-100 pt-3">
                              <div>
                                <label className="text-xs text-neutral-dark flex items-center gap-1">
                                  <Clock3 className="h-3.5 w-3.5" /> Hora
                                </label>
                                <input
                                  type="time"
                                  value={cfg.time}
                                  onChange={(e) => updateActivityConfig(activity.id, { time: e.target.value })}
                                  className="w-full mt-1 border border-border-soft rounded-lg p-2"
                                  disabled={disabled}
                                />
                              </div>

                              <div>
                                <label className="text-xs text-neutral-dark flex items-center gap-1">
                                  <Repeat className="h-3.5 w-3.5" /> Frecuencia
                                </label>
                                <select
                                  value={cfg.frequency}
                                  onChange={(e) =>
                                    updateActivityConfig(activity.id, {
                                      frequency: e.target.value as RoutineFrequency,
                                    })
                                  }
                                  className="w-full mt-1 border border-border-soft rounded-lg p-2 bg-white"
                                  disabled={disabled}
                                >
                                  <option value="daily">Daily</option>
                                  <option value="weekly">Weekly</option>
                                </select>
                              </div>

                              <label className="inline-flex items-center gap-2 text-xs text-neutral-dark">
                                <input
                                  type="checkbox"
                                  checked={cfg.is_active}
                                  onChange={(e) => updateActivityConfig(activity.id, { is_active: e.target.checked })}
                                  disabled={disabled}
                                />
                                Rutina activa para esta actividad
                              </label>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {errors.activities && <p className="text-red-500 text-xs mt-3">{errors.activities.message}</p>}
      </section>

      <div className="flex flex-col sm:flex-row gap-3 justify-end">
        <button type="button" onClick={onCancel} className="px-5 py-3 rounded-xl border border-border-soft text-neutral-dark hover:bg-hover">
          Cancelar
        </button>

        <button type="submit" disabled={disabled || isSubmitting} className="px-5 py-3 rounded-xl bg-blue text-white hover:opacity-90 disabled:opacity-60">
          {isSubmitting ? "Guardando..." : submitLabel}
        </button>
      </div>
    </form>
  );
}

export type { RoutineFormValues };
