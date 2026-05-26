import { Bell, User, Menu, ChevronDown } from "lucide-react";
import { useAuth } from "../context/useAuth";
import { useNavigate } from "react-router-dom";
import { useSidebar } from "../context/useSidebar";
import { useSelectedElderly } from "../context/useSelectedElderly";

import { getAllElderly } from "../services/elderly.services";

import type { Elderly } from "../types/Elderly";
import { useEffect, useRef, useState } from "react";

function getInitials(firstName: string, lastName: string) {
  return `${firstName[0] ?? ""}${lastName[0] ?? ""}`.toUpperCase();
}

export function TopBar() {
  const {
    toggleCollapsed,
    toggleMobile,
  } = useSidebar();

  const handleSidebar = () => {
    if (window.innerWidth < 768) {
      toggleMobile();
    } else {
      toggleCollapsed();
    }
  };

  const [elderlyProfiles, setElderlyProfiles] = useState<Elderly[]>([]);
  const [open, setOpen] = useState(false);

  const navigate = useNavigate();
  const { logout } = useAuth();
  const dropdownRef = useRef<HTMLDivElement>(null);

  const {
    selectedElderly,
    setSelectedElderly,
  } = useSelectedElderly();

  useEffect(() => {
    async function loadProfiles() {
      try {
        const data = await getAllElderly();

        setElderlyProfiles(data);

        if (data.length > 0) {

          // Verificar si el seleccionado existe
          const exists = data.some(
            (elderly: Elderly) => elderly.id === selectedElderly?.id
          );

          // Si NO existe en este cuidador,
          // seleccionar el primero válido
          if (!exists) {
            setSelectedElderly(data[0]);
          }
        } else if (selectedElderly) {
          setSelectedElderly(null);
        }
      } catch (error) {
        console.error(error);
      }
    }

    loadProfiles();
  }, [selectedElderly, setSelectedElderly]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener(
        "mousedown",
        handleClickOutside
      );
    };
  }, []);


  return (
    <header className="flex h-16 items-center justify-between border-b border-border-soft bg-white px-4">

      <div className="flex items-center gap-3">
        <button
          onClick={handleSidebar}
          className="h-10 w-10 rounded-xl border border-border-soft flex items-center justify-center hover:bg-hover transition"
        >
          <Menu className="h-5 w-5 text-neutral-dark" />
        </button>

        <div className="relative" ref={dropdownRef}>

          <button
            onClick={() => setOpen(!open)}
            className="flex items-center gap-3 border border-border-soft bg-white px-3 py-2 rounded-xl hover:bg-hover transition"
          >
            {selectedElderly ? (
              <>
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue/10 text-xs font-semibold text-blue">
                  {getInitials(
                    selectedElderly.first_name,
                    selectedElderly.last_name
                  )}
                </span>

                <div className="text-left hidden sm:block">
                  <p className="text-sm font-medium text-neutral-dark">
                    {selectedElderly.first_name}
                  </p>

                  <p className="text-xs text-neutral-light">
                    Adulto Mayor
                  </p>
                </div>
              </>
            ) : (
              <p className="text-sm text-neutral-light">
                Seleccionar perfil
              </p>
            )}

            <ChevronDown className="w-4 h-4 text-neutral-light" />
          </button>

          {open && (
            <div className="absolute right-0 mt-2 w-72 bg-white border border-border-soft rounded-xl shadow-lg z-50 overflow-hidden">

              {elderlyProfiles.map((profile) => (
                <button
                  key={profile.id}
                  onClick={() => {
                    setSelectedElderly(profile);
                    setOpen(false);
                  }}
                  className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-hover transition text-left
                        
                        ${selectedElderly?.id === profile.id
                      ? "bg-blue-50"
                      : ""
                    }
                    `}
                >
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue/10 text-sm font-semibold text-blue shrink-0">
                    {getInitials(
                      profile.first_name,
                      profile.last_name
                    )}
                  </span>

                  <div className="min-w-0">
                    <p className="text-sm font-medium text-neutral-dark truncate">
                      {profile.first_name} {profile.last_name}
                    </p>

                    <p className="text-xs text-neutral-light truncate">
                      {profile.relationship_to_caregiver}
                    </p>
                  </div>
                </button>
              ))}

              {elderlyProfiles.length === 0 && (
                <div className="px-4 py-6 text-center text-sm text-neutral-light">
                  No hay perfiles registrados
                </div>
              )}
            </div>
          )}
        </div>

      </div>

      <div className="flex items-center gap-4">

        <button className="relative hover:text-white">
          <Bell className="h-5 w-5 text-neutral-light" />
        </button>

        <div className="flex items-center gap-2 py-4">
          <div className="h-9 w-9 rounded-full bg-blue-light flex items-center justify-center text-blue font-semibold">
            <User></User>
          </div>
          <div className="hidden md:block">
            <p className="text-sm font-semibold text-neutral-dark leading-none">Maria Costa</p>
            <p className="text-xs text-muted-foreground text-neutral-light mt-0.5">Caregiver</p>
          </div>
        </div>
        <button
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Cerrar sesión
        </button>

      </div>
    </header>
  );
}
