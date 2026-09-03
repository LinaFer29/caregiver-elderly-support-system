import { httpClient } from "./httpClient";
import type {
  DailyAssignmentSummary,
  RoutineByDate,
  CreateRoutinePayload,
  CreateRoutineResponse,
  RoutineCatalogActivity,
} from "../types/Routine";

export const getRoutineCatalog = async (): Promise<RoutineCatalogActivity[]> => {
  try {
    const response = await httpClient.get("/routines/catalog/");
    return response.data;
  } catch (error) {
    console.error("Error en getRoutineCatalog:", error);
    throw error;
  }
};

export const createRoutine = async (
  payload: CreateRoutinePayload
): Promise<CreateRoutineResponse> => {
  try {
    const response = await httpClient.post("/routines/", payload);
    return response.data;
  } catch (error) {
    console.error("Error en createRoutine:", error);
    throw error;
  }
};

export const getRoutinesByElderly = async (
  elderlyId: number
): Promise<RoutineByDate[]> => {
  try {
    const response = await httpClient.get("/routines/", {
      params: { elderly_id: elderlyId },
    });
    return response.data;
  } catch (error) {
    console.error("Error en getRoutinesByElderly:", error);
    throw error;
  }
};

export const getRoutineById = async (routineId: string): Promise<RoutineByDate> => {
  try {
    const response = await httpClient.get(`/routines/${routineId}/`);
    return response.data;
  } catch (error) {
    console.error("Error en getRoutineById:", error);
    throw error;
  }
};

export const getDailyAssignmentSummary = async (
  elderlyId: number
): Promise<DailyAssignmentSummary> => {
  try {
    const response = await httpClient.get("/routines/daily-summary/", {
      params: { elderly_id: elderlyId },
    });
    return response.data;
  } catch (error) {
    console.error("Error en getDailyAssignmentSummary:", error);
    throw error;
  }
};

export const updateRoutine = async (
  routineId: string,
  payload: CreateRoutinePayload
): Promise<RoutineByDate> => {
  try {
    const response = await httpClient.put(`/routines/${routineId}/`, payload);
    return response.data;
  } catch (error) {
    console.error("Error en updateRoutine:", error);
    throw error;
  }
};

export const deleteRoutine = async (routineId: string): Promise<void> => {
  try {
    await httpClient.delete(`/routines/${routineId}/`);
  } catch (error) {
    console.error("Error en deleteRoutine:", error);
    throw error;
  }
};
