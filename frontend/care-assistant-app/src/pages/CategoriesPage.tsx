import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { DynamicIcon } from "../components/DynamicIcon";
import {
  getAllCategories,
  createCategory,
  updateCategory,
  deleteCategory,
} from "../services/categories.services";
import { useAuth } from "../context/useAuth"
import { CATEGORY_COLORS, CATEGORY_ICONS, type Category } from "../types/Category";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "../components/ui/dialog";


export function CategoriesPage() {

  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCat, setEditingCat] = useState<Category | null>(null);;
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const [name, setName] = useState("");
  const [icon, setIcon] = useState(CATEGORY_ICONS[0]);
  const [color, setColor] = useState(CATEGORY_COLORS[0]);

  const { isAuthenticated, loading : authLoading } = useAuth();

  // Get All Categories
  useEffect(() => {
    if (!isAuthenticated) return; 
    
    function loadCategories() {
      getAllCategories()
        .then((categories) => {
          setCategories(categories);
          setLoading(false);
        })
        .catch((error) => {
          console.error("Error loading categories:", error);
          setLoading(false);
        });
    }
    loadCategories();
  }, [isAuthenticated])

  // Create Category
  const openCreate = () => {
    setEditingCat(null);
    setName("");
    setIcon(CATEGORY_ICONS[0]);
    setColor(CATEGORY_COLORS[0]);
    setDialogOpen(true);
  }

  // Edit Category
  const openEdit = (category: Category) => {
    setEditingCat(category);
    setName(category.name);
    setIcon(category.icon);
    setColor(category.color);
    setDialogOpen(true);
  }

  // Save
  const handleSave = async () => {
    if (!name.trim()) {
      alert("Name is required");
      return;
    }
    try {
      if (editingCat) {
        await updateCategory(editingCat.id, { name, icon, color });
      } else {
        await createCategory({ name, icon, color });
      }
      const updatedCategories = await getAllCategories();
      setCategories(updatedCategories);
      setDialogOpen(false);
    } catch (error) {
      console.error("Error saving category:", error);
    }
  }

  // Delete
  const handleDelete = async (categoryId: number) => {
    if (!deleteId) return;

    try {
      await deleteCategory(categoryId);
      const updatedCategories = await getAllCategories();
      setCategories(updatedCategories);
      setDeleteId(null);
    } catch (error) {
      console.error("Error deleting category:", error);
    }
  }

  if (authLoading) return <p>Verificando sesión...</p>;
  
  return (
    <div className="space-y-6 max-w-3xl mx-auto">

      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-slate-dark">Categorías</h1>
          <p className="text-neutral-light mt-1">
            Organiza las actividades
          </p>
        </div>

        <button
          onClick={openCreate}
          className="bg-blue text-white px-4 py-2 rounded-xl flex items-center gap-2"
        >
          <Plus size={16} />
          Nueva Categoría
        </button>
      </div>

      {/* LIST */}
      {loading ? (
        <p>Cargando...</p>
      ) : categories.length === 0 ? (
        <p>No hay categorías</p>
      ) : (
        <div className="space-y-3">
          {categories.map((cat) => (
            <div
              key={cat.id}
              className="flex items-center gap-4 border border-border-soft rounded-xl p-4"
            >
              {/* ICON */}
              <div
                className="h-12 w-12 flex items-center justify-center rounded-xl"
                style={{ backgroundColor: `${cat.color}20` }}
              >
                <DynamicIcon
                  name={cat.icon}
                  style={{ color: cat.color }}
                />
              </div>

              {/* INFO */}
              <div className="flex-1">
                <p className="font-semibold">{cat.name}</p>

                <div className="flex items-center gap-2 mt-1">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: cat.color }}
                  />
                  <span className="text-xs text-neutral-light">
                    {cat.color}
                  </span>
                </div>
              </div>

              {/* ACTIONS */}
              <div className="flex gap-2">
                <button onClick={() => openEdit(cat)}>
                  <Pencil size={16} />
                </button>

                <button onClick={() => setDeleteId(cat.id)}>
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* MODAL SIMPLE (luego lo refinamos) */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md rounded-2xl p-0 overflow-hidden">

          {/* HEADER */}
          <DialogHeader className="px-6 pt-6 pb-2">
            <DialogTitle className="text-xl font-semibold text-neutral-dark">
              {editingCat ? "Editar categoría" : "Nueva categoría"}
            </DialogTitle>
            <p className="text-sm text-neutral-light">
              Define un nombre, icono y color.
            </p>
          </DialogHeader>

          {/* BODY */}
          <div className="px-6 py-4 space-y-6">

            {/* NAME */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-neutral-dark">
                Nombre
              </label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ej. Medicación"
                className="w-full px-3 rounded-xl h-11 border border-border-soft focus:ring-blue-main"
              />
            </div>

            {/* ICON */}
            <div className="space-y-3">
              <label className="text-sm font-medium text-neutral-dark">
                Icono
              </label>

              <div className="flex flex-wrap justify-center gap-2 mt-2">
                {CATEGORY_ICONS.map((ic) => (
                  <button
                    key={ic}
                    type="button"
                    onClick={() => setIcon(ic)}
                    className={`
                flex h-11 w-11 items-center justify-center rounded-xl border transition-all
                ${icon === ic
                        ? "border-blue-main bg-blue-light shadow-sm scale-105"
                        : "border-transparent hover:bg-hover"
                      }
              `}
                  >
                    <DynamicIcon
                      name={ic}
                      size={18}
                      className={icon === ic ? "text-blue-main" : "text-neutral-light"}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* COLOR */}
            <div className="space-y-3">
              <label className="text-sm font-medium text-neutral-dark">
                Color
              </label>

              <div className="flex flex-wrap justify-center gap-3 mt-2">
                {CATEGORY_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setColor(c)}
                    className={`
                h-10 w-10 rounded-full border-2 transition-all
                ${color === c
                        ? "border-neutral-dark scale-110 shadow-sm"
                        : "border-transparent hover:scale-105"
                      }
              `}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>

            {/* PREVIEW */}
            <div className="flex items-center gap-3 rounded-xl border border-border-soft p-3 bg-app-background">
              <div
                className="h-10 w-10 flex items-center justify-center rounded-lg"
                style={{ backgroundColor: `${color}20` }}
              >
                <DynamicIcon name={icon} style={{ color }} />
              </div>

              <div>
                <p className="text-sm font-semibold text-neutral-dark">
                  {name || "Nombre de categoría"}
                </p>
                <p className="text-xs text-neutral-light">
                  Vista previa
                </p>
              </div>
            </div>

          </div>

          {/* FOOTER */}
          <DialogFooter className="px-6 py-4 border-t border-border-soft flex justify-end gap-2">
            <button
              onClick={() => setDialogOpen(false)}
              className="px-3 py-3 border border-border-soft rounded-lg"
            >
              Cancelar
            </button>

            <button
              onClick={handleSave}
              disabled={!name.trim()}
              className="bg-blue text-white px-3 py-3 rounded-lg disabled:opacity-50"
            >
              {editingCat ? "Guardar cambios" : "Crear categoría"}
            </button>
          </DialogFooter>

        </DialogContent>
      </Dialog>

      {/* DELETE CONFIRM */}
      {deleteId && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center">
          <div className="bg-white p-6 rounded-xl space-y-5 w-full max-w-sm">
            <p>¿Desea eliminar categoría?</p>

            <div className="flex justify-end gap-2">
              <button 
              className="px-3 py-2 border border-border-soft rounded-lg"
              onClick={() => setDeleteId(null)}
              >
                Cancelar
              </button>
              <button 
              className="bg-red-light text-white px-3 py-2 rounded-lg"
              onClick={() => handleDelete(deleteId)}>
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CategoriesPage;