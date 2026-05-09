type BaseActivity = {
    title: string;
    description: string;
    category: number;
}

export type Activity = BaseActivity & { // Data coming FROM the backend
    id: number 
}; 

export type ActivityCreate = BaseActivity  // Data you SEND to the backend when creating a new activity

// Data used in the form, which can be for both creating and updating an activity
export type ActivityWithProgramData = BaseActivity & {
    date?: string;        // "2026-03-31"
    time?: string;        // "08:00"
    frequency?: "daily" | "weekly";
    is_active?: boolean;
    elderly_id?: number;
};

// Data coming FROM the backend that includes both activity and program information
export type ActivityWithProgram = Activity & {
    program: {
        id: number;
        date: string;        // "2026-03-31"
        time: string;        // "08:00"
        frequency: "daily" | "weekly";
        is_active: boolean;
    }
}

