import { ProfileScreen } from "../features/profile/ProfileScreen";

/**
 * Pantalla «Perfil» (MASTER_PROMPT §10.2.10): ajustes, datos, sesiones activas, uso sin conexión
 * y Créditos y licencias (§2.1); la lógica vive en `features/profile`.
 */
export function ProfileRoute(): React.JSX.Element {
  return <ProfileScreen />;
}
