import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Eye, EyeOff, Heart, Info } from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { authService } from "../services/auth.service";

const registerSchema = z.object({
    firstName: z.string().trim().min(1, "Nombre es requerido").max(50),
    lastName: z.string().trim().min(1, "Apellido es requerido").max(50),
    username: z
        .string()
        .trim()
        .min(3, "El nombre de usuario debe tener mínimo 3 caracteres")
        .max(30, "El nombre de usuario debe tener máximo 30 caracteres")
        .regex(/^[a-zA-Z0-9_.-]+$/, "Solo letras, números, . _ -"),
    email: z.string().trim().email("Email inválido"),
    password: z
        .string()
        .min(8, "La contraseña debe tener al menos 8 caracteres")
        .max(100, "La contraseña debe tener máximo 100 caracteres."),
    caregiverType: z.string().trim().min(1, "Tipo de cuidador es requerido").max(50),
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function Register() {
    const navigate = useNavigate();
    const [showPassword, setShowPassword] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm<RegisterFormData>({
        resolver: zodResolver(registerSchema),
    });

    const onSubmit = async (data: RegisterFormData) => {
        console.log("REGISTER DATA:", data);

        try {
            await authService.register({
                username: data.username,
                email: data.email,
                password: data.password,
                first_name: data.firstName,
                last_name: data.lastName,
                role: "caregiver",
                caregiver_type: data.caregiverType,
            });

            navigate("/login");
        } catch (error) {
            console.error(error);
            setFormError("Error al registrar usuario");
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-app-background py-10 px-4">
            <div className="w-full max-w-xl">

                {/* HEADER */}
                <div className="flex flex-col items-center text-center mb-6">
                    <div className="flex h-13 w-13 items-center justify-center rounded-xl bg-blue mb-2">
                        <Heart className="h-7 w-7 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-neutral-dark">
                        Crear cuenta de cuidador
                    </h1>
                    <p className="text-sm text-neutral-light mt-1">
                        Comience a gestionar las rutinas y a brindar apoyo en el cuidado de las personas mayores
                    </p>
                </div>

                {/* CARD */}
                <div >

                    <form
                        onSubmit={handleSubmit(onSubmit)}
                        className="bg-white border border-border-soft rounded-2xl p-6 space-y-5"
                    >
                        {/* NOMBRE Y APELLIDO */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <input
                                    {...register("firstName")}
                                    placeholder="Nombre"
                                    className="w-full border border-border-soft rounded-lg p-3"
                                />
                                {errors.firstName && (
                                    <span className="text-red-500 text-xs">
                                        {errors.firstName.message}
                                    </span>
                                )}
                            </div>

                            <div>
                                <input
                                    {...register("lastName")}
                                    placeholder="Apellido"
                                    className="w-full border border-border-soft rounded-lg p-3"
                                />
                                {errors.lastName && (
                                    <span className="text-red-500 text-xs">
                                        {errors.lastName.message}
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* USERNAME */}
                        <div>
                            <input
                                {...register("username")}
                                placeholder="Username"
                                className="w-full border border-border-soft rounded-lg p-3"
                            />
                            {errors.username && (
                                <span className="text-red-500 text-xs">
                                    {errors.username.message}
                                </span>
                            )}
                        </div>

                        {/* EMAIL */}
                        <div>
                            <input
                                type="email"
                                {...register("email")}
                                placeholder="Correo electrónico"
                                className="w-full border border-border-soft rounded-lg p-3"
                            />
                            {errors.email && (
                                <span className="text-red-500 text-xs">
                                    {errors.email.message}
                                </span>
                            )}
                        </div>

                        {/* PASSWORD */}
                        <div>
                            <div className="relative">
                                <input
                                    type={showPassword ? "text" : "password"}
                                    {...register("password")}
                                    placeholder="Contraseña"
                                    className="w-full border border-border-soft rounded-lg p-3 pr-10"
                                />

                                <button
                                    type="button"
                                    onClick={() => setShowPassword((s) => !s)}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-light hover:text-neutral-dark"
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>

                            {errors.password && (
                                <span className="text-red-500 text-xs">
                                    {errors.password.message}
                                </span>
                            )}
                        </div>

                        {/* ROLE INFO */}
                        <div className="flex justify-between items-center border border-border-soft rounded-xl p-3 bg-app-background">
                            <span className="text-sm text-neutral-light">Rol de Cuenta</span>
                            <div className="inline-flex items-center border rounded-full px-2.5 py-0.5 border-transparent bg-mint-green">
                                <span className="text-xs font-semibold text-white">
                                    Cuidador
                                </span>
                            </div>
                        </div>

                        {/* INFO BOX */}
                        <div className="flex gap-3 bg-blue-light border border-blue rounded-xl p-4 text-sm text-neutral-light">
                            <Info className="h-5 w-5 text-info shrink-0 text-blue" />
                            Los adultos mayores se registran después desde el sistema.
                            Podrás gestionarlos una vez crees tu cuenta.
                        </div>

                        {/* TIPO CUIDADOR */}
                        <div>
                            <input
                                {...register("caregiverType")}
                                placeholder="Tipo de cuidador (Ej: Familiar, Profesional)"
                                className="w-full border border-border-soft rounded-lg p-3"
                            />
                            {errors.caregiverType && (
                                <span className="text-red-500 text-xs">
                                    {errors.caregiverType.message}
                                </span>
                            )}
                        </div>

                        {/* BOTONES */}
                        <div className="flex flex-col sm:flex-row gap-3">
                            <button
                                type="button"
                                onClick={() => navigate("/login")}
                                className="border border-border-soft px-4 py-2 rounded-lg"
                            >
                                Volver
                            </button>

                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="bg-blue text-white px-4 py-2 rounded-lg flex-1 disabled:opacity-50"
                            >
                                {isSubmitting ? "Creando..." : "Crear cuenta"}
                            </button>

                        </div>
                            {formError && (
                                <div className="text-red-500 text-sm">{formError}</div>
                            )}

                        {/* LINK LOGIN */}
                        <p className="text-sm text-center text-neutral-light">
                            ¿Ya tienes cuenta?{" "}
                            <Link to="/login" className="text-blue font-semibold hover:underline">
                                Iniciar sesión
                            </Link>
                        </p>
                    </form>

                </div>
            </div>
        </div>
    );
}