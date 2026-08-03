export type DeviceAssociationPayload = {
  elderly_id: number;
  name: string;
  serial_number: string;
};

export type DeviceAssociationResponse = {
  message: string;
  device: {
    id: number;
    name: string;
    serial_number: string;
    mac_address: string;
    model: string;
    status: string;
    elderly_id: number;
  };
};
