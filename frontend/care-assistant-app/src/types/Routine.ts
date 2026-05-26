export type RoutineCatalogActivity = {
  id: number;
  title: string;
  description: string;
  category: number;
  category_name: string;
  category_color: string;
  category_icon: string;
};

export type RoutineFrequency = "daily" | "weekly";

export type RoutineActivityConfig = {
  activity_id: number;
  time: string;
  frequency: RoutineFrequency;
  is_active: boolean;
};

export type CreateRoutinePayload = {
  elderly_id: number;
  date: string;
  activities: RoutineActivityConfig[];
};

export type CreateRoutineResponse = {
  elderly_id: number;
  activities_count: number;
  program_ids: number[];
  assignment_ids: number[];
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
