import { useEffect, useMemo, useState } from "react";
import { Layers3 } from "lucide-react";
import { getRoutineCatalog } from "../services/routine.services";
import type { RoutineCatalogActivity } from "../types/Routine";
import { DynamicIcon } from "../components/DynamicIcon";

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

export default function ActivitiesCatalogPage() {
  const [activities, setActivities] = useState<RoutineCatalogActivity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadCatalog() {
      try {
        setLoading(true);
        const data = await getRoutineCatalog();
        setActivities(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }

    void loadCatalog();
  }, []);

  const grouped = useMemo(() => groupByCategory(activities), [activities]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-neutral-dark">Activity Catalog</h1>
        <p className="text-neutral-light mt-1">
          Explore available activities managed by the system.
        </p>
      </div>

      {loading && <p className="text-neutral-light">Cargando actividades...</p>}

      {!loading && activities.length === 0 && (
        <div className="bg-white border border-dashed border-border-soft rounded-2xl p-10 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-blue/10 text-blue">
            <Layers3 className="h-6 w-6" />
          </div>
          <p className="text-lg font-semibold text-neutral-dark">No hay actividades disponibles todavía.</p>
          <p className="text-sm text-neutral-light mt-1">
            Las actividades son administradas por el sistema.
          </p>
        </div>
      )}

      {!loading && activities.length > 0 && (
        <div className="space-y-6">
          {Object.entries(grouped).map(([categoryName, group]) => (
            <section key={categoryName} className="bg-white border border-border-soft rounded-2xl p-5">
              <div className="flex items-center gap-3">
                <span
                  className="flex h-9 w-9 items-center justify-center rounded-lg"
                  style={{ backgroundColor: `${group.color}20` }}
                >
                  <DynamicIcon
                    name={group.icon}
                    size={18}
                    style={{ color: group.color }}
                  />
                </span>
                <h2 className="text-lg font-semibold text-neutral-dark">{categoryName}</h2>
              </div>

              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {group.items.map((activity) => (
                  <article
                    key={activity.id}
                    className="border border-border-soft rounded-xl p-4 bg-white"
                  >
                    <h3 className="font-semibold text-neutral-dark">{activity.title}</h3>
                    <p className="text-sm text-neutral-light mt-1 line-clamp-3">
                      {activity.description}
                    </p>
                    <span
                      className="inline-flex mt-3 text-xs px-2 py-1 rounded-lg"
                      style={{
                        backgroundColor: `${activity.category_color}20`,
                        color: activity.category_color,
                      }}
                    >
                      {activity.category_name}
                    </span>
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
