import type { RoutineFrequency } from "../types/Routine";

function addMonth(currentDate: Date, targetDay: number) {
  const nextMonth = new Date(currentDate);
  nextMonth.setDate(1);
  nextMonth.setMonth(nextMonth.getMonth() + 1);

  const lastDay = new Date(
    nextMonth.getFullYear(),
    nextMonth.getMonth() + 1,
    0
  ).getDate();

  nextMonth.setDate(Math.min(targetDay, lastDay));
  return nextMonth;
}

function parseIsoDate(value: string) {
  return new Date(`${value}T00:00:00`);
}

function toIsoDate(value: Date) {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function generateRecurringDates(
  startDate: string,
  endDate: string,
  frequency: RoutineFrequency
) {
  if (!startDate) return [];

  if (frequency === "once") {
    return [startDate];
  }

  if (!endDate) return [];

  const start = parseIsoDate(startDate);
  const end = parseIsoDate(endDate);

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) {
    return [];
  }

  const dates: string[] = [];
  let current = new Date(start);

  while (current <= end) {
    dates.push(toIsoDate(current));

    if (frequency === "daily") {
      current.setDate(current.getDate() + 1);
    } else if (frequency === "weekly") {
      current.setDate(current.getDate() + 7);
    } else if (frequency === "monthly") {
      current = addMonth(current, start.getDate());
    } else {
      break;
    }
  }

  return dates;
}

export function formatRoutineFrequency(value: RoutineFrequency) {
  const labels: Record<RoutineFrequency, string> = {
    once: "Una vez",
    daily: "Diaria",
    weekly: "Semanal",
    monthly: "Mensual",
  };

  return labels[value];
}
