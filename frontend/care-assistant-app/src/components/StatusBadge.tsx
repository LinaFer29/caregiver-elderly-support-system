import type { RoutineGeneralStatus } from "../types/Routine";

type ActivityStatus = "pending" | "completed" | "missed";

const activityStatusStyles: Record<ActivityStatus, { label: string; className: string }> = {
  completed: {
    label: "Completada",
    className: "bg-green-100 text-green-700",
  },
  missed: {
    label: "No completada",
    className: "bg-red-100 text-red-600",
  },
  pending: {
    label: "Pendiente",
    className: "bg-yellow-100 text-yellow-700",
  },
};

const routineGeneralStatusStyles: Record<RoutineGeneralStatus, { label: string; className: string }> = {
  active: {
    label: "Activa",
    className: "bg-green-100 text-green-700",
  },
  mixed: {
    label: "Mixta",
    className: "bg-yellow-100 text-yellow-700",
  },
  completed: {
    label: "Completada",
    className: "bg-green-100 text-green-700",
  },
};

type StatusBadgeProps = {
  className?: string;
};

export function ActivityStatusBadge({
  status,
  className = "",
}: StatusBadgeProps & { status: ActivityStatus }) {
  const config = activityStatusStyles[status];

  return (
    <span className={`inline-flex text-xs px-2 py-1 rounded-lg ${config.className} ${className}`}>
      {config.label}
    </span>
  );
}

export function RoutineActiveBadge({
  isActive,
  className = "",
}: StatusBadgeProps & { isActive: boolean }) {
  return (
    <span
      className={`inline-flex text-xs px-2 py-1 rounded-lg ${
        isActive ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
      } ${className}`}
    >
      {isActive ? "Activa" : "Inactiva"}
    </span>
  );
}

export function RoutineGeneralStatusBadge({
  status,
  className = "",
}: StatusBadgeProps & { status: RoutineGeneralStatus }) {
  const config = routineGeneralStatusStyles[status];

  return (
    <span className={`inline-flex text-xs px-2 py-1 rounded-lg ${config.className} ${className}`}>
      {config.label}
    </span>
  );
}
