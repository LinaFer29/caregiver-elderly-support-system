import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Eye, EyeOff, Heart } from "lucide-react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useAuth } from "../context/useAuth";
import { isAxiosError } from "axios";

const loginSchema = z.object({
    identifier: z
        .string()
        .trim()
        .min(1, "Usuario o email es requerido")
        .max(255),
    password: z
        .string()
        .min(1, "Contraseña es requerida")
        .max(100),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function Login() {
    const navigate = useNavigate();
    const [showPassword, setShowPassword] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);
    const {login} = useAuth();

    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
        resetField,
    } = useForm<LoginFormData>({
        resolver: zodResolver(loginSchema),
    });

    const onSubmit = async (data: LoginFormData) => {
        setFormError(null);

        try {
            await login(data);
            navigate("/");

        } catch (error: unknown) {
            if (isAxiosError(error)) {
                if (error.response?.status === 404) {
                    setFormError("No se encontraron coincidencias para el usuario ingresado.");
                } else if (error.response?.status === 401) {
                    setFormError("Usuario o contraseña incorrectos.");
                } else {
                    setFormError("Error al iniciar sesión. Intenta nuevamente.");
                }
            } else {
                setFormError("Error al iniciar sesión. Intenta nuevamente.");
            }

            // Solo limpiamos contraseña, el usuario/email se mantiene
            resetField("password");
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-app-background px-4">
            <div className="w-full max-w-md">

                {/* HEADER */}
                <div className="flex flex-col items-center text-center mb-6">
                    <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-blue mb-2">
                        <Heart className="h-7 w-7 text-white" />
                    </div>

                    <h1 className="text-2xl font-bold text-neutral-dark">
                        Iniciar sesión
                    </h1>

                    <p className="text-sm text-neutral-light mt-1">
                        Bienvenido de nuevo, gestiona tus actividades fácilmente
                    </p>
                </div>

                {/* CARD */}
                <div className="bg-white border border-border-soft rounded-2xl p-6 space-y-5">

                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

                        {/* IDENTIFIER */}
                        <div>
                            <label className="text-sm text-neutral-dark">
                                Usuario o email
                            </label>

                            <input
                                {...register("identifier")}
                                className="w-full border border-border-soft rounded-xl p-3 mt-1"
                            />

                            {errors.identifier && (
                                <p className="text-xs text-red-500">
                                    {errors.identifier.message}
                                </p>
                            )}
                        </div>

                        {/* PASSWORD */}
                        <div>
                            <div className="flex justify-between items-center">
                                <label className="text-sm text-neutral-dark">
                                    Contraseña
                                </label>

                                <button
                                    type="button"
                                    className="text-xs text-blue-main"
                                    onClick={() =>
                                        alert("Próximamente recuperación de contraseña")
                                    }
                                >
                                    ¿Olvidaste tu contraseña?
                                </button>
                            </div>

                            <div className="relative">
                                <input
                                    type={showPassword ? "text" : "password"}
                                    {...register("password")}
                                    className="w-full border border-border-soft rounded-xl p-3 mt-1 pr-10"
                                />

                                <button
                                    type="button"
                                    onClick={() => setShowPassword((s) => !s)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-light"
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>

                            {errors.password && (
                                <p className="text-xs text-red-500">
                                    {errors.password.message}
                                </p>
                            )}
                        </div>

                        {/* ERROR GENERAL */}
                        {formError && (
                            <div className="bg-red-100 border border-red-300 text-red-600 text-sm p-3 rounded-lg">
                                {formError}
                            </div>
                        )}

                        {/* BOTÓN */}
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="w-full bg-blue text-white py-3 rounded-xl disabled:opacity-50"
                        >
                            {isSubmitting ? "Ingresando..." : "Iniciar sesión"}
                        </button>

                    </form>

                    {/* REGISTER LINK */}
                    <p className="text-sm text-neutral-light text-center">
                        ¿No tienes cuenta?{" "}
                        <Link to="/signup" className="text-blue-main font-medium">
                            Crear cuenta
                        </Link>
                    </p>

                </div>
            </div>
        </div>
    );
}
