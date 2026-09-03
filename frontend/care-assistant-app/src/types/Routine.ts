export type RoutineCatalogActivity = {
  id: number;
  title: string;
  description: string;
  category: number;
  category_name: string;
  category_color: string;
  category_icon: string;
};

export type RoutineFrequency = "once" | "daily" | "weekly" | "monthly";

export type RoutineActivityConfig = {
  activity_id: number;
  time: string;
  frequency: RoutineFrequency;
  is_active: boolean;
  additional_instructions?: string | null;
};

export type CreateRoutinePayload = {
  elderly_id: number;
  start_date: string;
  end_date: string;
  activities: RoutineActivityConfig[];
};

export type CreateRoutineResponse = {
  elderly_id: number;
  activities_count: number;
  program_ids: number[];
  assignment_ids: number[];
  scheduled_occurrences_count: number;
};

export type RoutineListItem = {
  activity_id: number;
  title: string;
  description: string;
  category_name: string;
  category_color: string;
  time: string;
  frequency: RoutineFrequency;
  is_active: boolean;
  status?: "pending" | "completed" | "missed";
  additional_instructions?: string | null;
};

export type RoutineByDate = {
  id: string;
  date: string;
  elderly: {
    id: number;
    first_name: string;
    last_name: string;
  };
  items: RoutineListItem[];
  activities_count: number;
  general_status: "active" | "mixed" | "completed";
};

export type DailyAssignmentSummary = {
  date: string;
  total: number;
  completed: number;
  missed: number;
  pending: number;
};
