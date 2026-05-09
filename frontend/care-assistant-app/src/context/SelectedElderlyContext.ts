import { createContext } from "react";
import type { Elderly } from "../types/Elderly";

export type SelectedElderlyContextType = {
  selectedElderly: Elderly | null;
  setSelectedElderly: (elderly: Elderly | null) => void;
};

export const SelectedElderlyContext =
  createContext<SelectedElderlyContextType | undefined>(undefined);
