import js from "@eslint/js";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "dist",
      "coverage",
      "playwright-report",
      "test-results",
      ".lighthouseci",
      // Script de verificación manual con Playwright contra la API real (F2-FE-16).
      "scripts/gate2-live.mjs",
      // Generado por `openapi-typescript` a partir de contracts/openapi.yaml (`npm run gen:api`);
      // no se edita a mano y se sobrescribe en cada generación.
      "src/lib/api/schema.d.ts",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser },
      parserOptions: {
        project: ["./tsconfig.json", "./tsconfig.node.json"],
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
      "jsx-a11y": jsxA11y,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.flatConfigs.strict.rules,
      "react-refresh/only-export-components": ["error", { allowConstantExport: true }],
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/consistent-type-imports": "error",
      "@typescript-eslint/explicit-function-return-type": ["error", { allowExpressions: true }],
      "no-console": ["error", { allow: ["warn", "error"] }],
    },
  },
  {
    files: ["**/*.js"],
    extends: [tseslint.configs.disableTypeChecked],
    languageOptions: { globals: { ...globals.node } },
  },
  {
    // Script de generación de mocks (Node, ejecutado tal cual sin compilar): las anotaciones
    // de tipo de retorno no son sintaxis JS válida aquí.
    files: ["scripts/**/*.js"],
    rules: {
      "@typescript-eslint/explicit-function-return-type": "off",
    },
  },
  {
    files: ["vite.config.ts", "playwright.config.ts", "e2e/**/*.ts"],
    languageOptions: { globals: { ...globals.node } },
  },
  {
    // Medios de ejercicio © Gym visual: solo `ExerciseMedia` puede usar `<img>` (MASTER_PROMPT
    // §2.1, ADR 0004). El resto del código debe pasar por ese componente, que exige la
    // atribución, el tamaño máximo de 180 px y el comportamiento de `prefers-reduced-motion`.
    files: ["src/**/*.{ts,tsx}"],
    ignores: ["src/components/ExerciseMedia.tsx"],
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          selector: "JSXOpeningElement[name.name='img']",
          message:
            "Usa el componente ExerciseMedia para mostrar medios de ejercicio (MASTER_PROMPT §2.1, ADR 0004); no uses <img> directamente.",
        },
      ],
    },
  },
);
