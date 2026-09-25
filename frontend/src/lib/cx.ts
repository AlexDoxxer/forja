/** Combina nombres de clase opcionales (p. ej. de un módulo CSS) en una sola cadena. */
export function cx(...classNames: (string | undefined | false)[]): string {
  return classNames.filter((name): name is string => typeof name === "string" && name.length > 0).join(" ");
}
