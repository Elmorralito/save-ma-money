import { Navigate } from "react-router-dom";

/** Account creation is handled automatically on first Google sign-in. */
export function RegisterPage() {
  return <Navigate to="/login" replace />;
}
