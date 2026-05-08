import { useState } from "react";
import { CATEGORY_COLORS, CATEGORY_ICONS, type CategoryCreate } from "../types/Category";
import { DynamicIcon } from "./DynamicIcon";

type Props = {
  onCreate: (data: CategoryCreate) => Promise<void>;
  onCancel: () => void;
};

export function CategoryInlineForm({ onCreate, onCancel }: Props) {
  const [formData, setFormData] = useState<CategoryCreate>({
    name: "",
    color: CATEGORY_COLORS[0], // Color por defecto
    icon: CATEGORY_ICONS[0], // Icono por defecto
  });

  return (
    <div className="mt-3 p-4 border border-border-soft rounded-xl bg-app-background space-y-3">
      {/* Nombre */}
      <input
        type="text"
        className="w-full border border-border-soft rounded-lg p-2"
        placeholder="Nombre de la categoría"
        value={formData.name}
        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
      />

      {/* ICONS */}
      <div>
        <label className="text-xs font-semibold text-neutral-light">
          Icono
        </label>

        <div className="flex flex-wrap gap-2 mt-2">
          {CATEGORY_ICONS.map((icon) => (
            <button
              key={icon}
              type="button"
              onClick={() =>
                setFormData({ ...formData, icon })
              }
              className={`flex h-9 w-9 items-center justify-center rounded-lg border transition
                ${
                  formData.icon === icon
                    ? "border-blue bg-blue-light"
                    : "border-transparent hover:bg-hover"
                }`}
            >
              <DynamicIcon name={icon} size={16} />
            </button>
          ))}
        </div>
      </div>

      {/* COLORS */}
      <div>
        <label className="text-xs font-semibold text-neutral-light">
          Color
        </label>

        <div className="flex flex-wrap gap-2 mt-2">
          {CATEGORY_COLORS.map((color) => (
            <button
              key={color}
              type="button"
              onClick={() =>
                setFormData({ ...formData, color })
              }
              className={`h-8 w-8 rounded-full border-2 transition
                ${
                  formData.color === color
                    ? "border-neutral-dark scale-110"
                    : "border-transparent"
                }`}
              style={{ backgroundColor: color }}
            />
          ))}
        </div>
      </div>

      {/* Buttons */}
      <div className="flex justify-end gap-2">
        <button
          type="button"
          className="px-3 py-1 border border-border-soft rounded-lg"
          onClick={onCancel}
        >
          Cancelar
        </button>
        <button
          type="button"
          className="bg-blue text-white px-3 py-1 rounded-lg disabled:opacity-50"
          onClick={() => onCreate(formData)}
          disabled={!formData.name}
        >
          Guardar
        </button>

      </div>
    </div>
  );
}