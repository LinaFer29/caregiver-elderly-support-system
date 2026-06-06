type BaseProgram = {
    elderly: number
    activity: number
    date: string
    time: string
    frequency: "once" | "daily" | "weekly" | "monthly"
    is_active: boolean
}

export type Program = BaseProgram & { // Data coming FROM the backend
    id: number
}

export type ProgramCreate = BaseProgram // Data you SEND to the backend
