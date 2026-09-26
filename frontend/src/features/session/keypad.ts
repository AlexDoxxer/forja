const MAX_LENGTH = 6;

/** Aplica una tecla al texto de un campo numérico. Pura para poder probarla. */
export function applyKey(value: string, key: string, allowDecimal: boolean): string {
  if (key === "back") return value.slice(0, -1);
  if (key === ",") {
    if (!allowDecimal || value.includes(",")) return value;
    return value === "" ? "0," : `${value},`;
  }
  if (value.length >= MAX_LENGTH) return value;
  return value === "0" ? key : `${value}${key}`;
}
