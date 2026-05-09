import { useState, type ReactNode } from "react";
import type { Elderly } from "../types/Elderly";
import { SelectedElderlyContext } from "./SelectedElderlyContext";

type Props = {
  children: ReactNode;
};

export function SelectedElderlyProvider({ children }: Props) {
  const [selectedElderly, setSelectedElderlyState] =
    useState<Elderly | null>(() => {
      const stored = localStorage.getItem("selectedElderly");
      if (!stored) return null;

      try {
        return JSON.parse(stored) as Elderly;
      } catch {
        localStorage.removeItem("selectedElderly");
        return null;
      }
    });

  const setSelectedElderly = (elderly: Elderly | null) => {
    setSelectedElderlyState(elderly);

    if (elderly) {
      localStorage.setItem("selectedElderly", JSON.stringify(elderly));
    } else {
      localStorage.removeItem("selectedElderly");
    }
  };

  return (
    <SelectedElderlyContext.Provider
      value={{
        selectedElderly,
        setSelectedElderly,
      }}
    >
      {children}
    </SelectedElderlyContext.Provider>
  );
}
