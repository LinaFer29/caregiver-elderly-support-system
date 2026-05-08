import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getActivityById, deleteActivity } from "../services/activities.services";
import { getAllCategories } from "../services/categories.services";
import type { Activity } from "../types/Activity";
import type { Category } from "../types/Category";

import { ArrowLeftFromLine, Calendar, Clock, Pen, Repeat, Trash2 } from "lucide-react";
import { toast } from "react-hot-toast";
import type { Program } from "../types/Program";
import { getAllPrograms, updateProgram } from "../services/programs.services";
import { DynamicIcon } from "../components/DynamicIcon";

export function ActivityDetailPage() {
    const { id } = useParams();
    const navigate = useNavigate();

    const [activity, setActivity] = useState<Activity | null>(null);
    const [category, setCategory] = useState<Category | undefined>();
    const [program, setProgram] = useState<Program | undefined>();

    useEffect(() => {
        async function loadData() {
            try {
                if (!id) return;

                const activityData = await getActivityById(Number(id));
                const categories = await getAllCategories();
                const programData = await getAllPrograms();

                setActivity(activityData);

                const foundCategory = categories.find(
                    (c: Category) => c.id === activityData.category
                );
                setCategory(foundCategory);

                const foundProgram = programData.find(
                    (p: Program) => p.activity === activityData.id
                );
                setProgram(foundProgram);
            } catch (error) {
                console.error(error);
            }
        }

        loadData();
    }, [id]);

    if (!activity) {
        return <p>Cargando actividad...</p>;
    }

    return (
        <div className="max-w-5xl mx-auto space-y-6">

            {/* Volver */}
            <button
                onClick={() => navigate("/activities")}
                className="flex gap-2 text-neutral-light text-sm"
            >
                <ArrowLeftFromLine className="h-5 text-neutral-light" />
                Volver a actividades
                {/* icon flecha */}
            </button>

            {/* Header */}
            <div className="flex justify-between items-start">
                <div className="flex gap-5">

                    {/* Icono categoría */}
                    {category && (
                        <div
                            className="h-15 w-15 flex items-center justify-center rounded-xl"
                            style={{ backgroundColor: `${category.color}20` }}
                        >
                            {/* icon dinámico */}
                            <DynamicIcon
                                name={category.icon}
                                size={25}
                                style={{ color: category.color }}
                            />
                        </div>
                    )}
                    <div>
                        <h1 className="text-2xl font-bold text-slate-dark mb-1">
                            {activity.title}
                        </h1>

                        {category && (
                            <span
                                className="text-sm text-blue px-3 py-0.5  rounded-lg"
                                style={{
                                    backgroundColor: `${category.color}20`,
                                    color: category.color,
                                }
                                }
                            >
                                {category.name}
                            </span>

                        )}
                    </div>
                </div>

                <div className="flex gap-2">
                    <button
                        onClick={() => navigate(`/activity/${activity.id}`)}
                        className="bg-blue text-white px-4 py-2 rounded-xl flex items-center gap-2"
                    >
                        <Pen size={16} />
                        Editar
                    </button>

                    <button
                        onClick={async () => {
                            const confirm = window.confirm("¿Eliminar actividad?");
                            if (!confirm) return;

                            await deleteActivity(activity.id);
                            toast.success("Actividad eliminada");
                            navigate("/activities");
                        }}
                        className="bg-red-500 text-white px-4 py-2 rounded-xl flex items-center gap-2"
                    >
                        <Trash2 size={16} />
                    </button>
                </div>
            </div>

            {/* Card */}
            <div className="bg-white border border-border-soft rounded-2xl p-6 space-y-5">

                {/* Descripción */}
                <div>
                    <h2 className="text-sm text-neutral-light mb-1">DESCRIPCIÓN</h2>
                    <p className="text-slate-dark">
                        {activity.description || "Sin descripción"}
                    </p>
                    <hr className="my-5 text-border-soft" />
                </div>

                {/* Info */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

                    <div className="flex items-center gap-2">
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-light">
                            <Calendar className="h-5 w-5 text-blue" />
                        </div>
                        <div>
                            <p className="text-sm text-neutral-light">Fecha</p>
                            <p>{program?.date || "Sin fecha"}</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-light">
                            <Clock className="h-5 w-5 text-blue" />
                        </div>
                        <div>
                            <p className="text-sm text-neutral-light">Hora</p>
                            <p>{program?.time || "Sin hora"}</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-mint-green-light">
                            <Repeat className="h-5 w-5 text-mint-green" />
                        </div>
                        <div>
                            <p className="text-sm text-neutral-light">Frecuencia</p>
                            <p className="text-neutral-dark">{program?.frequency || "Sin frecuencia"}</p>
                        </div>
                    </div>
                </div>
                <hr className="my-5 text-border-soft" />

                {/* Estado */}
                <div className="bg-app-background border border-border-soft rounded-xl p-4 flex items-center justify-between">
                    <div className="flex flex-col">
                        <span className="text-nuetral-dark">Estado de Actividad</span>
                        <p className="text-neutral-light">Activa o desactiva esta actividad.</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">

                        <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={program?.is_active}
                            onChange={async (e) => {
                                if (!program) return;

                                const updated = {
                                    ...program,
                                    is_active: e.target.checked,
                                };

                                await updateProgram(program.id, updated);
                                setProgram(updated);
                            }}
                        />
                        <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:bg-blue transition"></div>
                    </label>

                </div>
            </div>
        </div>
    );
}

export default ActivityDetailPage;