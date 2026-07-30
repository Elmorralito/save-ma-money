import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { setUnauthorizedHandler } from "@/api/http";

/** Wires apiFetch 401 / failed BFF refresh to a login redirect. */
export function AuthRedirectBridge(): null {
  const navigate = useNavigate();

  useEffect(() => {
    setUnauthorizedHandler(() => {
      void navigate("/login", { replace: true });
    });
    return () => {
      setUnauthorizedHandler(null);
    };
  }, [navigate]);

  return null;
}
