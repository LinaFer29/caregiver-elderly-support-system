import type { ActivityCreate } from '../types/Activity';
import { httpClient } from './httpClient';

export const getAllActivities = async () => {
    try {
        const response = await httpClient.get('/activities/');
        return response.data;
    } catch (error) {
        console.error('Error en getActivities:', error);
        throw error;
    }
}

export const getActivityById = async (activityId: number) => {
    try {
        const response = await httpClient.get(`/activities/${activityId}/`);
        return response.data;
    } catch (error) {
        console.error('Error en getActivityById:', error);
        throw error;
    }
}

export const createActivity = async (activityData: ActivityCreate) => {
    try {
        const response = await httpClient.post('/activities/', activityData);
        return response.data;
    } catch (error) {
        console.error('Error en createActivity:', error);
        throw error;
    }
}

export const deleteActivity = async (activityId: number) => {
    try {
        await httpClient.delete(`/activities/${activityId}/`);
    } catch (error) {
        console.error('Error en deleteActivity:', error);
        throw error;
    }
}

export const updateActivity = async (activityId: number, activityData: ActivityCreate) => {
    try {
        const response = await httpClient.put(`/activities/${activityId}/`, activityData);
        return response.data;
    } catch (error) {
        console.error('Error en updateActivity:', error);
        throw error;
    }
}