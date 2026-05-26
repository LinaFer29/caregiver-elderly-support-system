import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Plus,
    Pencil,
    Trash2,
    User,
    AlertTriangle,
} from "lucide-react";

import { toast } from "react-hot-toast";

import type { Elderly } from "../types/Elderly";

import {
    deleteElderly,
    getAllElderly,
} from "../services/elderly.services";

export default function ElderlyPage() {

    const navigate = useNavigate();

    const [elderlyList, setElderlyList] = useState<Elderly[]>([]);
    const [loading, setLoading] = useState(true);

    const [deleteId, setDeleteId] = useState<number | null>(null);

    useEffect(() => {
        loadElderly();
    }, []);

    const loadElderly = async () => {
        try {
            setLoading(true);

            const data = await getAllElderly();

            setElderlyList(data);

        } catch (error) {
            console.error(error);

            toast.error("Error cargando adultos mayores", {
                position: "top-center",
                duration: 3000,
                style: {
                    background: "#780606",
                    color: "#fff",
                },
            });

        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async () => {

        if (!deleteId) return;

        try {

            await deleteElderly(deleteId);

            setElderlyList((prev) =>
                prev.filter((person) => person.id !== deleteId)
            );

            toast.success("Adulto mayor eliminado correctamente", {
                position: "top-center",
                duration: 3000,
                style: {
                    background: "#4BB543",
                    color: "#fff",
                },
            });

            setDeleteId(null);

        } catch (error) {

            console.error(error);

            toast.error("Error eliminando adulto mayor", {
                position: "top-center",
                duration: 3000,
                style: {
                    background: "#780606",
                    color: "#fff",
                },
            });
        }
    };

    const getInitials = (
        firstName: string,
        lastName: string
    ) => {
        return `${firstName[0] ?? ""}${lastName[0] ?? ""}`.toUpperCase();
    };

    const dependencyStyles = {
        low: "bg-green-100 text-green-700 border border-green-200",
        moderate: "bg-yellow-100 text-yellow-700 border border-yellow-200",
        high: "bg-orange-100 text-orange-700 border border-orange-200",
        total: "bg-red-100 text-red-700 border border-red-200",
    };

    const dependencyLabels = {
        low: "Bajo",
        moderate: "Moderado",
        high: "Alto",
        total: "Total",
    };

    return (
        <div className="max-w-4xl mx-auto mt-3 px-4 pb-10 space-y-6">

            {/* HEADER */}
            <div className="flex items-center justify-between gap-4 flex-wrap">

                <div>
                    <h1 className="text-2xl md:text-3xl font-bold text-neutral-dark">
                        Adultos Mayores
                    </h1>

                    <p className="text-neutral-light mt-1">
                        Administra los perfiles asociados a tu cuidado.
                    </p>
                </div>

                <button
                    onClick={() => navigate("/elderly-create")}
                    className="h-11 px-5 bg-blue text-white rounded-xl flex items-center gap-2 shadow hover:opacity-90 transition"
                >
                    <Plus className="w-4 h-4" />
                    Agregar Adulto Mayor
                </button>
            </div>

            {/* EMPTY STATE */}
            {!loading && elderlyList.length === 0 && (

                <div className="text-center py-16 border border-dashed border-border-soft rounded-2xl bg-white">

                    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-app-background">
                        <User className="h-7 w-7 text-neutral-light" />
                    </div>

                    <p className="text-lg font-semibold text-neutral-dark">
                        No hay adultos mayores registrados
                    </p>

                    <p className="text-sm text-neutral-light mt-1">
                        Agrega uno para comenzar a gestionar actividades y rutinas.
                    </p>

                    <button
                        onClick={() => navigate("/elderly-create")}
                        className="mt-5 px-5 py-3 bg-blue text-white rounded-xl inline-flex items-center gap-2 shadow hover:opacity-90 transition"
                    >
                        <Plus className="w-4 h-4" />
                        Agregar Adulto Mayor
                    </button>
                </div>
            )}

            {/* LOADING */}
            {loading && (
                <div className="text-center py-10 text-neutral-light">
                    Cargando adultos mayores...
                </div>
            )}

            {/* LIST */}
            {!loading && elderlyList.length > 0 && (

                <div className="space-y-3">

                    {elderlyList.map((person) => {

                        const fullName =
                            `${person.first_name} ${person.last_name}`;

                        return (

                            <div
                                key={person.id}
                                className="flex items-center gap-4 bg-white border border-border-soft rounded-2xl p-4 shadow-sm hover:shadow-md transition"
                            >

                                {/* AVATAR */}
                                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue/10 text-blue font-semibold shrink-0">
                                    {getInitials(
                                        person.first_name,
                                        person.last_name
                                    )}
                                </div>

                                {/* INFO */}
                                <div className="flex-1 min-w-0">

                                    <div className="flex items-center gap-2 flex-wrap">

                                        <p className="font-semibold text-neutral-dark truncate">
                                            {fullName}
                                        </p>

                                        <span
                                            className={`text-[10px] uppercase tracking-wide font-semibold px-2 py-1 rounded-full ${dependencyStyles[person.dependency_level]}`}
                                        >
                                            {
                                                dependencyLabels[
                                                person.dependency_level
                                                ]
                                            }
                                        </span>
                                    </div>

                                    <p className="text-xs text-neutral-light mt-1 truncate">
                                        {person.relationship_to_caregiver}

                                        {person.underlying_conditions
                                            ? ` · ${person.underlying_conditions}`
                                            : ""}
                                    </p>
                                </div>

                                {/* ACTIONS */}
                                <div className="flex gap-1">

                                    <button
                                        onClick={() =>
                                            navigate(`/elderly/${person.id}`)
                                        }
                                        className="h-9 w-9 rounded-xl flex items-center justify-center text-neutral-light hover:bg-app-background hover:text-neutral-dark transition"
                                    >
                                        <Pencil className="w-4 h-4" />
                                    </button>

                                    <button
                                        onClick={() =>
                                            setDeleteId(person.id)
                                        }
                                        className="h-9 w-9 rounded-xl flex items-center justify-center text-neutral-light hover:bg-red-50 hover:text-red-600 transition"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* DELETE MODAL */}
            {deleteId && (

                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">

                    <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">

                        <div className="flex items-start gap-3">

                            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center shrink-0">
                                <AlertTriangle className="w-5 h-5 text-red-600" />
                            </div>

                            <div>
                                <h2 className="text-lg font-semibold text-neutral-dark">
                                    ¿Eliminar perfil?
                                </h2>

                                <p className="text-sm text-neutral-light mt-1">
                                    Esta acción no se puede deshacer.
                                    El perfil del adulto mayor será eliminado
                                    permanentemente.
                                </p>
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 mt-6">

                            <button
                                onClick={() => setDeleteId(null)}
                                className="px-4 py-2 border border-border-soft rounded-xl hover:bg-app-background transition"
                            >
                                Cancelar
                            </button>

                            <button
                                onClick={handleDelete}
                                className="px-4 py-2 bg-red-600 text-white rounded-xl hover:bg-red-700 transition"
                            >
                                Confirmar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}