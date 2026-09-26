/** Retroalimentación del reproductor: vibración, sonido, notificación y Wake Lock (§10.2.5). */

export type WakeLockHandle = Pick<WakeLockSentinel, "release">;

/** Pide mantener la pantalla encendida; devuelve `null` si el navegador no lo soporta. */
export async function requestWakeLock(): Promise<WakeLockHandle | null> {
  if (!("wakeLock" in navigator)) return null;
  try {
    return await navigator.wakeLock.request("screen");
  } catch {
    return null;
  }
}

export function vibrate(pattern: number | number[]): boolean {
  return typeof navigator.vibrate === "function" ? navigator.vibrate(pattern) : false;
}

/** Pitido corto con Web Audio (sin ficheros de audio externos). */
export function beep(times = 2): void {
  const Ctor: typeof AudioContext | undefined =
    typeof AudioContext === "undefined" ? undefined : AudioContext;
  if (Ctor === undefined) return;
  try {
    const ctx = new Ctor();
    for (let i = 0; i < times; i += 1) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = 880;
      gain.gain.value = 0.15;
      osc.connect(gain).connect(ctx.destination);
      const start = ctx.currentTime + i * 0.25;
      osc.start(start);
      osc.stop(start + 0.15);
    }
    window.setTimeout(() => void ctx.close(), times * 250 + 300);
  } catch {
    // Sin audio disponible: la vibración y el aviso visual siguen funcionando.
  }
}

export async function ensureNotificationPermission(): Promise<NotificationPermission | "unsupported"> {
  if (typeof Notification === "undefined") return "unsupported";
  if (Notification.permission !== "default") return Notification.permission;
  try {
    return await Notification.requestPermission();
  } catch {
    return Notification.permission;
  }
}

/** Notificación de fin de descanso, solo si la app está en segundo plano. */
export function notifyRestOver(title: string, body: string): boolean {
  if (typeof Notification === "undefined" || Notification.permission !== "granted") return false;
  if (document.visibilityState === "visible") return false;
  new Notification(title, { body, tag: "forja-rest" });
  return true;
}

export interface FeedbackPrefs {
  sounds: boolean;
  vibration: boolean;
}

/** Aviso completo de fin de descanso según las preferencias del perfil. */
export function restFinished(prefs: FeedbackPrefs, title: string, body: string): void {
  if (prefs.vibration) vibrate([200, 100, 200]);
  if (prefs.sounds) beep();
  notifyRestOver(title, body);
}
