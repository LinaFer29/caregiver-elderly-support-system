import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { Eye, EyeOff, ArrowLeft, UserPlus, Info } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
    createElderly,
    getElderlyById,
    updateElderly,
} from "../services/elderly.services";
import { toast } from "react-hot-toast";
import { z } from "zod";
import type { ElderlyCreate, ElderlyUpdate } from "../types/Elderly";
import { isAxiosError } from "axios";

const elderlySchema = z.object({
    firstName: z.string().min(1, "Nombre es requerido").max(50),
    lastName: z.string().min(1, "Apellido es requerido").max(50),
    username: z
        .string()
        .min(3, "El nombre de usuario debe tener mínimo 3 caracteres")
        .max(30, "El nombre de usuario debe tener máximo 30 caracteres")
        .regex(/^[a-zA-Z0-9_.-]+$/, "Solo letras, números, . _ -"),
    email: z.string().email("Email inválido"),
    password: z
        .string()
        .min(8, "La contraseña debe tener mínimo 8 caracteres")
        .max(100, "La contraseña debe tener máximo 100 caracteres.")
        .optional()
        .or(z.literal("")),

    relationshipToCaregiver: z.string().min(1, "Relación es requerida"),
    dependencyLevel: z.enum(["low", "moderate", "high", "total"],
        {
            message: "Seleccione un nivel de dependencia"
        }
    ),
    conditions: z.string().min(5, "Condiciones médicas es requerida"),
});

type ElderlyFormData = z.infer<typeof elderlySchema>;
type BackendErrors = Record<string, string[]>;

export default function RegisterElderlyPage() {
    const navigate = useNavigate();
    const params = useParams();
    const isEdit = !!params.id;

    const [showPassword, setShowPassword] = useState(false);

    const {
        register,
        handleSubmit,
        setError,
        reset,
        formState: { errors, isSubmitting },
    } = useForm<ElderlyFormData>({
        resolver: zodResolver(elderlySchema),
    });

    // Cargar datos si es edición
    useEffect(() => {
        async function loadElderly() {
            if (!params.id) return;

            try {
                const data = await getElderlyById(Number(params.id));

                reset({
                    firstName: data.first_name,
                    lastName: data.last_name,
                    username: data.username,
                    email: data.email,
                    relationshipToCaregiver: data.relationship_to_caregiver,
                    dependencyLevel: data.dependency_level,
                    conditions: data.underlying_conditions,
                });
            } catch (error) {
                console.error("Error cargando adulto mayor:", error);
            }
        }

        loadElderly();
    }, [params.id, reset]);

    // SUBMIT
    const onSubmit = async (data: ElderlyFormData) => {
        try {
            if (isEdit && params.id) {
                const updatePayload: ElderlyUpdate = {
                    first_name: data.firstName,
                    last_name: data.lastName,
                    username: data.username,
                    email: data.email,

                    ...(data.password
                        ? { password: data.password }
                        : {}),

                    role: "elderly",
                    relationship_to_caregiver: data.relationshipToCaregiver,
                    dependency_level: data.dependencyLevel,
                    underlying_conditions: data.conditions,
                };

                await updateElderly(Number(params.id), updatePayload);

                toast.success("Adulto mayor actualizado correctamente", {
                    position: "top-center",
                    duration: 3000,
                    style: {
                        background: "#4BB543",
                        color: "#fff",
                    }
                });

                navigate(`/elderly`)
            } else {
                const createPayload: ElderlyCreate = {
                    first_name: data.firstName,
                    last_name: data.lastName,
                    username: data.username,
                    email: data.email,

                    password: data.password!,

                    role: "elderly",

                    relationship_to_caregiver:
                        data.relationshipToCaregiver,

                    dependency_level:
                        data.dependencyLevel,

                    underlying_conditions:
                        data.conditions,
                };
                await createElderly(createPayload);

                toast.success("Adulto mayor creado correctamente", {
                    position: "top-center",
                    duration: 3000,
                    style: {
                        background: "#4BB543",
                        color: "#fff",
                    }
                });

                navigate("/elderly");
            }
        } catch (error: unknown) {
            console.error(error);

            if (isAxiosError(error) && error.response?.data && typeof error.response.data === "object") {
                const backendErrors = error.response.data as BackendErrors;
                const fieldMap: Record<string, keyof ElderlyFormData> = {
                    first_name: "firstName",
                    last_name: "lastName",
                    username: "username",
                    email: "email",
                    password: "password",
                    relationship_to_caregiver: "relationshipToCaregiver",
                    dependency_level: "dependencyLevel",
                    underlying_conditions: "conditions",
                };

                Object.keys(backendErrors).forEach((key) => {
                    const message = backendErrors[key]?.[0];
                    const formField = fieldMap[key];
                    if (formField && typeof message === "string") {
                        setError(formField, { message });
                    }
                });
            } else {
                toast.error("Error al guardar");
            }
        }
    };

    return (
        <div className="max-w-3xl mx-auto mt-3 pb-10 px-4 space-y-6">

            {/* HEADER */}
            <div className="flex justify-between items-center flex-wrap gap-3">
                <div>
                    <button
                        onClick={() => navigate("/elderly")}
                        className="flex items-center text-sm text-gray-500 p-2 hover:bg-border-soft/40 rounded-lg"
                    >
                        <ArrowLeft className="w-4 h-4 mr-1" />
                        Volver
                    </button>

                    <h1 className="text-2xl font-bold">
                        {isEdit ? "Editar Adulto Mayor" : "Registrar Adulto Mayor"}
                    </h1>

                    <p className="text-sm text-gray-500 mt-1">
                        {isEdit
                            ? "Modifica la información del perfil"
                            : "Crea un perfil asociado a tu cuenta de cuidador"}
                    </p>
                </div>

                <div className="w-12 h-12 bg-blue text-white rounded-xl flex items-center justify-center shadow">
                    <UserPlus />
                </div>
            </div>

            {/* INFO BOX */}
            <div className="flex gap-3 bg-blue-50 border border-blue/20 p-4 rounded-xl text-sm">
                <Info className="h-5 w-5 text-blue shrink-0 mt-0.5" />
                <p className="text-sm text-neutral-light leading-relaxed">
                    Este perfil permitirá gestionar actividades, rutinas y seguimiento del adulto mayor.
                </p>
            </div>

            {/* FORM CARD */}
            <div className="bg-white shadow-md rounded-xl border border-border-soft p-6">
                <div>
                    <span>Información personal</span>
                    <p>Datos básicos de la cuenta para el usuario de edad avanzada</p>
                </div>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

                    {/* NOMBRES */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="text-sm">
                                Nombre <span className="text-red-700">*</span>
                            </label>
                            <input
                                {...register("firstName")}
                                placeholder="John"
                                className="w-full mt-1 border border-border-soft rounded-lg p-3"
                            />
                            {errors.firstName && (
                                <p className="text-red-500 text-xs">{errors.firstName.message}</p>
                            )}
                        </div>

                        <div>
                            <label className="text-sm">
                                Apellido <span className="text-red-700">*</span>
                            </label>
                            <input
                                {...register("lastName")}
                                placeholder="Smith"
                                className="w-full mt-1 border border-border-soft rounded-lg p-3"
                            />
                            {errors.lastName && (
                                <p className="text-red-500 text-xs">{errors.lastName.message}</p>
                            )}
                        </div>
                    </div>

                    {/* USERNAME */}
                    <div>
                        <label className="text-sm">
                            Username
                            <span className="text-red-700">*</span>
                        </label>
                        <input
                            {...register("username")}
                            placeholder="john.smith"
                            className="w-full mt-1 border border-border-soft rounded-lg p-3"
                        />
                        {errors.username && (
                            <p className="text-red-500 text-xs">{errors.username.message}</p>
                        )}
                    </div>

                    {/* EMAIL */}
                    <div>
                        <label className="text-sm">
                            Email
                            <span className="text-red-700">*</span>
                        </label>
                        <input
                            type="email"
                            {...register("email")}
                            placeholder="elderly@example.com"
                            className="w-full mt-1 border border-border-soft rounded-lg p-3"
                        />
                        {errors.email && (
                            <p className="text-red-500 text-xs">{errors.email.message}</p>
                        )}
                    </div>

                    {/* PASSWORD SOLO CREATE */}
                    {!isEdit && (
                        <div>
                            <label className="text-sm">
                                Contraseña
                                <span className="text-red-700">*</span>
                            </label>
                            <div className="relative">
                                <input
                                    type={showPassword ? "text" : "password"}
                                    {...register("password")}
                                    placeholder="Al menos 8 caracteres"
                                    className="w-full mt-1 border border-border-soft rounded-lg p-3"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-5 top-1/2 -translate-y-1/2"
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                            {errors.password && (
                                <p className="text-red-500 text-xs">{errors.password.message}</p>
                            )}
                        </div>
                    )}

                    <div className="pt-4 border-t border-border-soft">
                        <h3 className="text-base text-neutral-dark mb-1">
                            Detalles de la atención
                        </h3>
                        <p className="text-sm text-neutral-light mb-4">
                            Ayúdenos a comprender la atención que necesita esta persona.
                        </p>

                        {/* RELACIÓN + DEPENDENCIA */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="text-sm">
                                    Relación con el cuidador
                                    <span className="text-red-700">*</span>
                                </label>

                                <input
                                    {...register("relationshipToCaregiver")}
                                    placeholder="Ej: Padre, Madre, Paciente, etc."
                                    className="w-full mt-1 border border-border-soft rounded-lg p-3"
                                />

                                {errors.relationshipToCaregiver && (
                                    <p className="text-red-500 text-xs mt-1">
                                        {errors.relationshipToCaregiver.message}
                                    </p>
                                )}
                            </div>

                            <div>
                                <label className="text-sm">
                                    Nivel de dependencia
                                    <span className="text-red-700">*</span>
                                </label>

                                <select
                                    {...register("dependencyLevel")}
                                    className="w-full mt-1 border border-border-soft rounded-lg p-3"
                                >
                                    <option value="">Selecciona un nivel</option>
                                    <option value="low">Bajo</option>
                                    <option value="moderate">Moderado</option>
                                    <option value="high">Alto</option>
                                    <option value="total">Total</option>
                                </select>

                                {errors.dependencyLevel && (
                                    <p className="text-red-500 text-xs mt-1">
                                        {errors.dependencyLevel.message}
                                    </p>
                                )}
                            </div>
                        </div>

                        {/* CONDICIONES */}
                        <div className="mt-5">
                            <label className="text-sm">
                                Condiciones médicas
                                <span className="text-red-700">*</span>
                            </label>

                            <textarea
                                {...register("conditions")}
                                placeholder="Ej: Diabetes, hipertensión, etc."
                                className="w-full mt-1 border border-border-soft rounded-lg p-3"
                            />

                            {errors.conditions && (
                                <p className="text-red-500 text-xs">
                                    {errors.conditions.message}
                                </p>
                            )}
                        </div>
                    </div>

                    {/* BOTONES */}
                    <div className="flex flex-col-reverse sm:flex-row gap-3 pt-2">
                        <button
                            type="button"
                            onClick={() => navigate("/elderly")}
                            className="px-4 py-2 border border-border-soft rounded-lg"
                        >
                            Cancelar
                        </button>

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="flex-1 h-11 text-white bg-blue rounded-lg p-3"
                        >
                            {isSubmitting
                                ? "Guardando..."
                                : isEdit
                                    ? "Guardar cambios"
                                    : "Crear perfil de adulto mayor"}
                        </button>
                    </div>

                </form>
            </div>
        </div>
    );
}
