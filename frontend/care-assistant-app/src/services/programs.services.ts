import type { ActivityWithProgramData } from "../types/Activity";
import type { ProgramCreate } from "../types/Program";
import { httpClient } from "./httpClient";

// Traer todos los program de un id de cuidador getProgramByCaregiverId

export const getAllPrograms = async () => {
    try {
        const response = await httpClient.get('/programs/');
        return response.data;
    } catch (error) {
        console.error('Error en getAllPrograms:', error);
        throw error;
    }
}

export const getProgramById = async (programId: number) => {
    try {
        const response = await httpClient.get(`/programs/${programId}/`);
        return response.data;
    } catch (error) {
        console.error('Error en getActivityById:', error);
        throw error;
    }
}


export const createProgram = async (programData: ProgramCreate) => {
    try {
        console.log('Creando programa con datos:', programData);
        const response = await httpClient.post('/programs/', programData);
        return response.data;
    } catch (error) {
        console.error('Error en createProgram:', error);
        throw error;
    }
}


export const updateProgram = async (programId: number, programData: ProgramCreate) => {
    try {
        console.log('Update programa con datos:', programData);
        const response = await httpClient.put(`/programs/${programId}/`, programData);
        return response.data;
    } catch (error) {
        console.error('Error en updateActivity:', error);
        throw error;
    }
}

export const getActivitiesWithProgram = async () => {
    const res = await httpClient.get("/activities-with-program/");
    return res.data;
};

export const createActivityWithProgram = async (data: ActivityWithProgramData) => {
    // res = {activity_id: 00, program_id: 00}
    const res = await httpClient.post("/activities-with-program/", data);
    return res.data;
};

export const updateActivityWithProgram = async (id: number, data: ActivityWithProgramData) => {
    const res = await httpClient.put(`/activities-with-program/${id}/`, data);
    return res.data;
};