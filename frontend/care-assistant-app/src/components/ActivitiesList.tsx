import { useEffect, useState } from "react"
import type { ActivityWithProgram } from "../types/Activity"
import { ActivityCard } from "./ActivityCard"
import { getAllCategories } from "../services/categories.services"
import type { Category } from "../types/Category"
import { useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";
import { getActivitiesWithProgram } from "../services/programs.services"
import { useAuth } from "../context/useAuth"

export function ActivitiesList() {
    
    const [categories, setCategories] = useState<Category[]>([])
    const [activitiesWithProgram, setActivitiesWithProgram] = useState<ActivityWithProgram[]>([])
    const navigate = useNavigate()

    const { isAuthenticated, loading } = useAuth();

    useEffect(() => {
        if (loading) return;
        if (!isAuthenticated) return;

        console.log("Cargando Actividades con programacion...");

        getActivitiesWithProgram()
            .then(data => {
                console.log("Actividades con programación obtenidas:", data)
                setActivitiesWithProgram(data)
            })
            .catch(error => {
                console.error("Error al cargar actividades con programación:", error)
            })

        getAllCategories()
            .then(categories => {
                console.log("Categorías obtenidas:", categories)
                setCategories(categories)
            })
            .catch(error => {
                console.error("Error al cargar categorías:", error)
            })

    }, [isAuthenticated, loading]);

    if (loading) return <p>Cargando...</p>;

    return (
        <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">

                {/* Texto */}
                <div>
                    <h1 className="text-2xl md:text-4xl font-bold text-slate-dark">
                        Actividades
                    </h1>
                    <p className="text-neutral-light mt-1">
                        Gestiona las rutinas diarias y las actividades de cuidado.
                    </p>
                </div>

                {/* Botón */}
                <button
                    onClick={() => navigate("/activity-create")}
                    className="flex items-center gap-2 bg-blue text-white px-5 py-2.5 rounded-xl hover:opacity-90 transition"
                >
                    <Plus className="h-4 w-4" />
                    Create Activity
                </button>

            </div>
            {activitiesWithProgram.length === 0 ? (
                <p>Cargando actividades...</p>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {activitiesWithProgram.map((item) => {
                        const category = categories.find(
                            (c) => c.id === item.category
                        );


                        // const program = programs.find(
                        //     (p) => p.id === item.activity_id
                        // );

                        return (
                            <ActivityCard
                                key={item.id}
                                activitiesWithProgram={item}
                                category={category}
                            />
                        );
                    })}
                </div>
            )}
        </div>
    )
}

export default ActivitiesList