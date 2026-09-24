#!/usr/bin/env node
/**
 * Genera `src/mocks/handlers.generated.ts` a partir de `contracts/openapi.yaml`.
 *
 * Regla del proyecto (MASTER_PROMPT §4.1, docs/handoffs/f0-arquitecto.md): el cliente y los
 * mocks del frontend nunca se escriben a mano a partir del contrato. Para cada operación del
 * OpenAPI se busca la primera respuesta 2xx y se construye el cuerpo de ejemplo con, por este
 * orden: el `example` de la respuesta, los `examples` de nivel de esquema (JSON Schema), o una
 * síntesis recursiva a partir del propio esquema (resolviendo `$ref`, `allOf`, `oneOf`/`anyOf`,
 * enumeraciones y formatos conocidos). Así se generan handlers para las 71 operaciones del
 * contrato sin transcribirlas.
 *
 * Uso: `npm run gen:mocks` (también se ejecuta antes de `dev`, `build`, `lint` y `test`).
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { parse } from "yaml";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SPEC_PATH = resolve(__dirname, "../../contracts/openapi.yaml");
const OUTPUT_PATH = resolve(__dirname, "../src/mocks/handlers.generated.ts");
const METHODS = ["get", "put", "post", "delete", "patch"];

/** Resuelve un `$ref` interno del documento (solo `#/...`). */
function resolveRef(doc, ref) {
  const path = ref.replace(/^#\//, "").split("/");
  let node = doc;
  for (const segment of path) {
    node = node[segment];
    if (node === undefined) {
      throw new Error(`No se pudo resolver la referencia ${ref}`);
    }
  }
  return node;
}

const STRING_PATTERNS = [
  { pattern: "^[0-9]{4}$", value: "0001" },
  { pattern: "^[0-9a-f]{64}$", value: "0".repeat(64) },
  { pattern: "^[0-9a-f]{40}$", value: "7455efae41b330c265e7cd4b78dfa848e7ce5ebd" },
  { pattern: "^[a-z0-9]+(?:-[a-z0-9]+)*$", value: "ejemplo-forja" },
  { pattern: "^[a-z0-9]+(?:_[a-z0-9]+)*$", value: "ejemplo_forja" },
  { pattern: "^[a-z][a-z0-9_]*$", value: "ejemplo_valido" },
];

function synthesizeString(schema) {
  if (typeof schema.pattern === "string") {
    const known = STRING_PATTERNS.find((entry) => entry.pattern === schema.pattern);
    if (known) return known.value;
  }
  switch (schema.format) {
    case "date":
      return "2026-09-23";
    case "date-time":
      return "2026-09-23T08:00:00Z";
    case "uuid":
      return "0192f09e-0000-7c2d-8e4f-5a6b7c8d9e00";
    case "uri":
    case "uri-reference":
      return "/ejemplo";
    case "email":
      return "persona@example.org";
    default:
      return "texto de ejemplo";
  }
}

/** Sintetiza un valor de ejemplo a partir de un (sub)esquema JSON Schema/OpenAPI. */
function synthesize(schema, doc, depth = 0, seen = []) {
  if (schema === null || schema === undefined) return null;
  if (typeof schema.$ref === "string") {
    if (seen.includes(schema.$ref) || depth > 10) return null;
    return synthesize(resolveRef(doc, schema.$ref), doc, depth, [...seen, schema.$ref]);
  }
  if (Object.prototype.hasOwnProperty.call(schema, "example")) return schema.example;
  if (Array.isArray(schema.examples) && schema.examples.length > 0) return schema.examples[0];
  if (Object.prototype.hasOwnProperty.call(schema, "const")) return schema.const;
  if (Array.isArray(schema.enum) && schema.enum.length > 0) return schema.enum[0];
  if (Object.prototype.hasOwnProperty.call(schema, "default")) return schema.default;

  if (Array.isArray(schema.allOf)) {
    let merged = {};
    for (const sub of schema.allOf) {
      const part = synthesize(sub, doc, depth + 1, seen);
      if (part !== null && typeof part === "object" && !Array.isArray(part)) {
        merged = { ...merged, ...part };
      }
    }
    return merged;
  }
  const variants = schema.oneOf ?? schema.anyOf;
  if (Array.isArray(variants) && variants.length > 0) {
    const nonNull = variants.find((variant) => variant.type !== "null") ?? variants[0];
    return synthesize(nonNull, doc, depth + 1, seen);
  }
  if (Array.isArray(schema.type)) {
    const nonNull = schema.type.find((type) => type !== "null") ?? schema.type[0];
    return synthesize({ ...schema, type: nonNull }, doc, depth, seen);
  }
  if (depth > 12) return null;

  switch (schema.type) {
    case "object": {
      const result = {};
      const properties = schema.properties ?? {};
      for (const [key, propSchema] of Object.entries(properties)) {
        result[key] = synthesize(propSchema, doc, depth + 1, seen);
      }
      return result;
    }
    case "array": {
      const item = synthesize(schema.items ?? {}, doc, depth + 1, seen);
      return item === null ? [] : [item];
    }
    case "string":
      return synthesizeString(schema);
    case "integer":
    case "number":
      return typeof schema.minimum === "number" ? schema.minimum : 1;
    case "boolean":
      return false;
    default:
      return {};
  }
}

function toMswPath(openApiPath) {
  return openApiPath.replace(/\{([^}]+)\}/g, ":$1");
}

function firstSuccessResponse(responses) {
  const codes = Object.keys(responses)
    .filter((code) => /^2\d\d$/.test(code))
    .sort((a, b) => Number(a) - Number(b));
  return codes[0] ?? null;
}

function buildHandlers(doc) {
  const basePath = new URL(doc.servers[0].url, "http://localhost").pathname.replace(/\/$/, "");
  const handlers = [];
  for (const [pathKey, pathItem] of Object.entries(doc.paths)) {
    for (const method of METHODS) {
      const operation = pathItem[method];
      if (!operation) continue;
      const code = firstSuccessResponse(operation.responses ?? {});
      if (code === null) continue;
      let responseObj = operation.responses[code];
      if (typeof responseObj.$ref === "string") {
        responseObj = resolveRef(doc, responseObj.$ref);
      }
      const mediaType = responseObj.content?.["application/json"];
      let body = null;
      if (mediaType) {
        body = Object.prototype.hasOwnProperty.call(mediaType, "example")
          ? mediaType.example
          : synthesize(mediaType.schema, doc);
      }
      handlers.push({
        method,
        path: `${basePath}${toMswPath(pathKey)}`,
        status: Number(code),
        body,
        operationId: operation.operationId ?? `${method}${pathKey}`,
      });
    }
  }
  return handlers;
}

function renderHandlers(handlers) {
  const lines = handlers.map((handler) => {
    const resolver =
      handler.body === null
        ? `() => new HttpResponse(null, { status: ${handler.status} })`
        : `() => HttpResponse.json(${JSON.stringify(handler.body)}, { status: ${handler.status} })`;
    return `  http.${handler.method}(${JSON.stringify(handler.path)}, ${resolver}), // ${handler.operationId}`;
  });
  return `/**
 * ARCHIVO GENERADO — no editar a mano.
 * Fuente: contracts/openapi.yaml. Regenerar con \`npm run gen:mocks\`.
 */
import { http, HttpResponse } from "msw";

/** Un handler MSW por operación del contrato (primera respuesta 2xx). */
export const generatedHandlers = [
${lines.join("\n")}
];
`;
}

function main() {
  const doc = parse(readFileSync(SPEC_PATH, "utf8"));
  const handlers = buildHandlers(doc);
  writeFileSync(OUTPUT_PATH, renderHandlers(handlers));
  process.stdout.write(`gen:mocks → ${handlers.length} handlers escritos en ${OUTPUT_PATH}\n`);
}

main();
