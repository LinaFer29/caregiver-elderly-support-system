import { useNavigate } from "react-router-dom";
import { UserPlus, Users } from "lucide-react";

export default function ElderlyRequiredPage() {
  const navigate = useNavigate();

  return (
    <div className="max-w-2xl mx-auto mt-10 px-4">
      <div className="bg-white border border-border-soft rounded-2xl p-8 shadow-sm text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue/10 text-blue">
          <Users className="h-7 w-7" />
        </div>

        <h1 className="text-2xl font-bold text-neutral-dark">
          Primero registra un adulto mayor
        </h1>

        <p className="mt-3 text-neutral-light">
          Para continuar con el flujo del sistema, primero debes registrar al
          menos un adulto mayor. Luego podras crear y gestionar rutinas usando
          actividades predefinidas.
        </p>

        <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={() => navigate("/elderly-create")}
            className="px-5 py-3 rounded-xl bg-blue text-white hover:opacity-90 transition inline-flex items-center justify-center gap-2"
          >
            <UserPlus className="h-4 w-4" />
            Registrar adulto mayor
          </button>

          <button
            onClick={() => navigate("/elderly")}
            className="px-5 py-3 rounded-xl border border-border-soft text-neutral-dark hover:bg-hover transition"
          >
            Ver listado de adultos mayores
          </button>
        </div>
      </div>
    </div>
  );
}
