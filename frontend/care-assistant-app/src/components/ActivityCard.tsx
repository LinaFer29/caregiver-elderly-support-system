import type { ActivityWithProgram } from "../types/Activity";
import type { Category } from "../types/Category";
import { useNavigate } from "react-router-dom";
import { Calendar, Clock } from "lucide-react";
import { DynamicIcon } from "./DynamicIcon";

interface Props {
  activitiesWithProgram: ActivityWithProgram;
  category?: Category;
}

export function ActivityCard({ activitiesWithProgram, category }: Props) {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/activities/${activitiesWithProgram.id}`)}
      className="group relative bg-white border border-border-soft rounded-2xl p-5 cursor-pointer transition hover:shadow-md"
    >
      {/* Barra lateral de categoría */}
      {category && (
        <div
          className="absolute left-0 top-4 bottom-4 w-1 rounded-r-full"
          style={{ backgroundColor: category.color || "#0C77A9" }}
        />
      )}

      {/* Header */}
      <div className="flex justify-between items-start gap-3">

        {/* Info */}
        <div className="flex gap-3 flex-1">

          {/* Icono categoría */}
          {category && (
            <div
              className="h-10 w-10 flex items-center justify-center rounded-xl"
              style={{ backgroundColor: `${category.color}20` }}
            >
              {/* icon dinámico */}
              <DynamicIcon
                name={category.icon}
                size={25}
                style={{ color: category.color }}
              />
            </div>
          )}

          {/* Texto */}
          <div className="flex-1">
            <h3 className="font-semibold text-slate-dark text-base">
              {activitiesWithProgram.title}
            </h3>

            <p className="text-sm text-slate-light mt-1 line-clamp-2">
              {activitiesWithProgram.description}
            </p>
          </div>
        </div>
      </div>

      <div className="flex gap-2">

      {/* Categoría */}
      {category && (
        <div className="mt-4">
          <span
            className="text-xs px-3 py-1 rounded-lg"
            style={{
              backgroundColor: `${category.color}20`,
              color: category.color,
            }}
          >
            {category.name}
          </span>
        </div>
      )}

      {/* Programacion */}
      {activitiesWithProgram &&(
        <div className="mt-4 flex gap-2">
          <div>
            <span
              className="text-xs px-3 py-1 rounded-lg"
              style={{
                backgroundColor: `#6E7C9220`,
                color: `#6E7C92`,
              }}
            >
              {activitiesWithProgram.program.frequency[0].toUpperCase() + activitiesWithProgram.program.frequency.slice(1)}
            </span>
          </div>
          <div>
            <span>
              {activitiesWithProgram.program.is_active ? (
                <span
                  className="text-xs px-3 py-1 rounded-lg"
                  style={{
                    backgroundColor: `#3CB37120`,
                    color: `#3CB371`,
                  }}
                >
                  Activo
                </span>
              ) : (
                <span
                  className="text-xs px-3 py-1 rounded-lg"
                  style={{
                    backgroundColor: `#FF634720`,
                    color: `#FF6347`,
                  }}
                >
                  Inactivo
                </span>
              )}
            </span>
          </div>
        </div>
      )}
      </div>

      {/* Fecha y hora */}
      <div className="flex items-center gap-4 mt-4 text-xs text-slate-light">

        <span className="flex items-center gap-1">
          <Calendar className="h-4 w-4" />
          {activitiesWithProgram?.program.date || "Sin fecha"}
        </span>

        <span className="flex items-center gap-1">
          <Clock className="h-4 w-4" />
          {activitiesWithProgram?.program.time || "--:--"}
        </span>

      </div>
    </div>
  );
}