import { useCallback, useEffect, useState } from "react";
import { getAllElderly } from "../services/elderly.services";

type UseHasElderlyProfilesResult = {
  hasElderlyProfiles: boolean;
  loading: boolean;
  reload: () => Promise<void>;
};

export function useHasElderlyProfiles(
  refreshKey?: string
): UseHasElderlyProfilesResult {
  const [hasElderlyProfiles, setHasElderlyProfiles] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const elderly = await getAllElderly();
      setHasElderlyProfiles(elderly.length > 0);
    } catch (error) {
      console.error("Error verificando adultos mayores:", error);
      setHasElderlyProfiles(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  return {
    hasElderlyProfiles,
    loading,
    reload: load,
  };
}
