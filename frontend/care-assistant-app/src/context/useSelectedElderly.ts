import { useContext } from "react";
import { SelectedElderlyContext } from "./SelectedElderlyContext";

export function useSelectedElderly() {
  const context = useContext(SelectedElderlyContext);

  if (!context) {
    throw new Error(
      "useSelectedElderly debe usarse dentro de SelectedElderlyProvider"
    );
  }

  return context;
}
