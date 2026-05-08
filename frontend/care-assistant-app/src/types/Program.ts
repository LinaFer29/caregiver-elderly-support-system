type BaseProgram = {
    activity: number
    date: string
    time: string
    frequency: "daily" | "weekly"
    is_active: boolean
}

export type Program = BaseProgram & { // Data coming FROM the backend
    id: number
}

export type ProgramCreate = BaseProgram // Data you SEND to the backend
