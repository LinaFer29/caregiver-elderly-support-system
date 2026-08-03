import { isAxiosError } from "axios";
import { Cpu, Link2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { useSelectedElderly } from "../context/useSelectedElderly";
import { associateDevice } from "../services/device.services";

const formSchema = z.object({
  name: z.string().trim().min(1, "El nombre es obligatorio").max(100),
  serialNumber: z
    .string()
    .trim()
    .min(1, "El número de serie es obligatorio")
    .max(100),
});

type FormValues = z.infer<typeof formSchema>;

export default function DeviceLinkPage() {
  const navigate = useNavigate();
  const { selectedElderly } = useSelectedElderly();
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
  });

  const onSubmit = async (values: FormValues) => {
    if (!selectedElderly) {
      toast.error("Debes seleccionar un adulto mayor");
      return;
    }

    try {
      setSubmitting(true);

      const response = await associateDevice({
        elderly_id: selectedElderly.id,
        name: values.name,
        serial_number: values.serialNumber,
      });

      toast.success(response.message, {
        position: "top-center",
        duration: 3000,
        style: {
          background: "#4BB543",
          color: "#fff",
        },
      });

      reset();
    } catch (error: unknown) {
      let message = "No fue posible vincular el dispositivo.";

      if (isAxiosError(error) && typeof error.response?.data?.detail === "string") {
        message = error.response.data.detail;
      }

      toast.error(message, {
        position: "top-center",
        duration: 3000,
        style: {
          background: "#780606",
          color: "#fff",
        },
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-neutral-dark">
            Vincular Dispositivo
          </h1>
          <p className="text-neutral-light mt-1">
            Asocia un dispositivo existente al adulto mayor seleccionado.
          </p>
        </div>
      </div>

      {!selectedElderly && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-2xl p-5">
          <p className="font-semibold text-yellow-800">
            No hay adulto mayor seleccionado
          </p>
          <p className="text-sm text-yellow-700 mt-1">
            Selecciona un adulto mayor desde la barra superior para vincular un
            dispositivo.
          </p>
          <button
            onClick={() => navigate("/elderly")}
            className="mt-4 px-4 py-2 rounded-xl bg-yellow-600 text-white hover:opacity-90"
          >
            Ir a adultos mayores
          </button>
        </div>
      )}

      {selectedElderly && (
        <>
          <div className="bg-white border border-border-soft rounded-2xl p-5 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue/10 text-blue">
              <Cpu className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-neutral-light">Adulto mayor seleccionado</p>
              <p className="font-semibold text-neutral-dark">
                {selectedElderly.first_name} {selectedElderly.last_name}
              </p>
            </div>
          </div>

          <form
            onSubmit={handleSubmit(onSubmit)}
            className="bg-white border border-border-soft rounded-2xl p-6 space-y-5"
          >
            <div>
              <label className="text-sm text-neutral-dark">Nombre</label>
              <input
                {...register("name")}
                placeholder="Ej. Dispositivo habitación principal"
                className="w-full border border-border-soft rounded-xl p-3 mt-1"
              />
              {errors.name && (
                <p className="text-xs text-red-500 mt-1">{errors.name.message}</p>
              )}
            </div>

            <div>
              <label className="text-sm text-neutral-dark">Número de serie</label>
              <input
                {...register("serialNumber")}
                placeholder="Ej. ESP32-0008"
                className="w-full border border-border-soft rounded-xl p-3 mt-1"
              />
              {errors.serialNumber && (
                <p className="text-xs text-red-500 mt-1">
                  {errors.serialNumber.message}
                </p>
              )}
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-blue text-white hover:opacity-90 disabled:opacity-60"
              >
                <Link2 className="h-4 w-4" />
                {submitting ? "Vinculando..." : "Vincular dispositivo"}
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  );
}
