type BaseElderly = {
    first_name: string;
    last_name: string;
    age: number | null;
    relationship_to_caregiver: string;
    dependency_level: "bajo" | "moderado" | "alto" | "total" | "low" | "moderate" | "high";
    underlying_conditions?: string;
}

export type Elderly = BaseElderly & { // Data coming FROM the backend
    id: number
}

export type ElderlyCreate = BaseElderly;

export type ElderlyUpdate = Partial<BaseElderly>;
