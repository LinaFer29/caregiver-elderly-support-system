type BaseElderly = {
    first_name: string;
    last_name: string;
    username: string;
    email: string;
    role: string; // "elderly"

    // El backend asignará automáticamente el cuidador actual a 'caregiver'
    relationship_to_caregiver: string;
    dependency_level: "low" | "moderate" | "high" | "total";
    underlying_conditions?: string;
}

export type Elderly = BaseElderly & { // Data coming FROM the backend
    id: number
}

export type ElderlyCreate = BaseElderly & { // Data you SEND to the backend
    password: string;
};

export type ElderlyUpdate = Partial<BaseElderly> & {
    password?: string;
};