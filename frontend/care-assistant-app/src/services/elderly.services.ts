import type { ElderlyCreate, ElderlyUpdate } from "../types/Elderly";
import { httpClient } from "./httpClient";

export const getAllElderly = async () => {
    try {
        const response = await httpClient.get("/elderly/");
        return response.data;
    } catch (error) {
        console.error("Error en getAllElderly:", error);
        throw error;
    }
};

export const getElderlyById = async (id: number) => {
    try {
        const response = await httpClient.get(`/elderly/${id}/`);
        console.log('Respuesta de getElderlyById:', response.data);
        return response.data;
    } catch (error) {
        console.error('Error en getElderlyById:', error);
        throw error;
    }
}

export const createElderly = async (data: ElderlyCreate) => {
    try {
        const response = await httpClient.post("/elderly/", data);
        return response.data;
    } catch (error) {
        console.error('Error en createElderly:', error);
        throw error;

    }

};

export const updateElderly = async (id: number, data: ElderlyUpdate) => {
    try {
        const response = await httpClient.put(`/elderly/${id}/`, data);
        return response.data;
    } catch (error) {
        console.error('Error en updateElderly:', error);
        throw error;
    }
};

export const deleteElderly = async (id: number) => {
    try {
        await httpClient.delete(`/elderly/${id}/`);
    } catch (error) {
        console.error("Error en deleteElderly:", error);
        throw error;
    }
};
