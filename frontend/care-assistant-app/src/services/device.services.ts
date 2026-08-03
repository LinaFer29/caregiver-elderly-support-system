import type {
  DeviceAssociationPayload,
  DeviceAssociationResponse,
} from "../types/Device";
import { httpClient } from "./httpClient";

export const associateDevice = async (
  payload: DeviceAssociationPayload
): Promise<DeviceAssociationResponse> => {
  try {
    const response = await httpClient.post("/devices/associate/", payload);
    return response.data;
  } catch (error) {
    console.error("Error en associateDevice:", error);
    throw error;
  }
};
