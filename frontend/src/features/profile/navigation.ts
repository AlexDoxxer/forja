/** Recarga completa hacia la portada (tras borrar la cuenta se descarta todo el estado en memoria). */
export function reloadToHome(): void {
  window.location.assign("/");
}
