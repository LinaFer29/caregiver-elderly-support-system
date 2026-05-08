import type { CategoryCreate } from '../types/Category';
import { httpClient } from './httpClient';

export const getAllCategories = async () => {
    try {
        const response = await httpClient.get('/categories/');
        return response.data;
    } catch (error) {
        console.error('Error en getAllCategories:', error);
        throw error;
    }
}

export const getCategoryById = async (categoryId: number) => {
    try {
        const response = await httpClient.get(`/categories/${categoryId}/`);
        return response.data;
    } catch (error) {
        console.error('Error en getCategoryById:', error);
        throw error;
    }
}

export const createCategory = async (categoryData: CategoryCreate) => {
    try {
        const response = await httpClient.post('/categories/', categoryData);
        return response.data;
    } catch (error) {
        console.error('Error en createCategory:', error);
        throw error;
    }
}

export const deleteCategory = async (categoryId: number) => {
    try {
        await httpClient.delete(`/categories/${categoryId}/`);
    } catch (error) {
        console.error('Error en deleteCategory:', error);
        throw error;
    }
}

export const updateCategory = async (categoryId: number, categoryData: CategoryCreate) => {
    try {
        const response = await httpClient.put(`/categories/${categoryId}/`, categoryData);
        return response.data;
    } catch (error) {
        console.error('Error en updateCategory:', error);
        throw error;
    }
}