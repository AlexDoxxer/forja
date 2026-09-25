# ORQUESTACIÓN — cómo ejecutar Forja con subagentes

La **sesión principal de Claude Code es el orquestador**: no escribe código de producto,
delega en los subagentes de `.claude/agents/`, revisa sus handoffs, controla las puertas de
fase y mantiene `docs/TASKS.md` al día.

## 1. Preparación (una vez)
```bash
mkdir forja && cd forja && git init
# copia aquí el contenido de este kit (MASTER_PROMPT.md, ORCHESTRATION.md, CLAUDE.md,
# specs/, docs/, .claude/agents/)
git add . && git commit -m "chore: add Forja agent kit"
claude            # abre Claude Code en la raíz del repo
```
Si Claude Code no ve los agentes, reinicia la sesión (el directorio `.claude/agents/` debe
existir antes de arrancar).

## 2. Prompt de arranque (pégalo tal cual en la sesión principal)

```text
Eres el ORQUESTADOR del proyecto Forja. Lee MASTER_PROMPT.md, ORCHESTRATION.md, CLAUDE.md,
docs/dataset-analysis.md y specs/ completos antes de nada.

Tu trabajo es coordinar, no implementar. Delega cada tarea al subagente propietario
(.claude/agents/) con un encargo autocontenido que incluya: objetivo, secciones del
MASTER_PROMPT aplicables, ficheros de entrada, criterios de aceptación verificables y
el nombre del handoff que debe escribir. Lanza en paralelo las tareas independientes de
una misma fase. Tras cada entrega: lee el handoff, ejecuta tú mismo los comandos de
verificación que indique (lint, tipos, tests, cobertura) y, si algo falla, devuélvelo al
mismo agente con el error exacto. No avances de fase sin cumplir su puerta.

Fases y puertas (ORCHESTRATION.md §3). Empieza por la Fase 0 con el agente arquitecto.
Al final de cada fase, resume en docs/PROGRESS.md: qué se hizo, métricas (cobertura,
tests), decisiones y riesgos abiertos. Pregúntame solo ante decisiones de producto que el
MASTER_PROMPT no resuelva; en lo demás, decide con un ADR.
```

## 3. Fases, encargos y puertas

### Fase 0 · Fundaciones — `arquitecto`
- Encargo: todo lo descrito en su definición.
- **Puerta 0**: `make lint typecheck test` verde en CI; `contracts/openapi.yaml` valida con
  `openapi-spec-validator` y cubre §9 al 100 %; `docs/TASKS.md` completo. El orquestador
  revisa los contratos y los congela (tag `contracts-v1`).

### Fase 1 · Núcleo (en paralelo)
| Agente | Encargo | Criterio de salida |
|---|---|---|
| `ingesta-datos` | §6 completo | 1.324 ejercicios + 2.648 medios verificados; informe de enriquecimiento; nombres ES 100 % |
| `motor-rutinas` | §7 completo | cobertura 100 %/95 %; 1.890 combinaciones; 12 snapshots |
| `motor-nutricion` | §8 completo | cobertura 100 %; propiedades de seguridad |
| `frontend-ui` | Fase 1 de su definición | shell navegable con MSW; `ExerciseMedia` con test de atribución |

Dependencia: `motor-rutinas` empieza con catálogo de fixture y, cuando ingesta termine,
regenera el fixture con `forja-ingest export-cards` y actualiza snapshots.

### Fase 1b · Revisión de dominio — `experto-entrenamiento`
Revisa enriquecimiento, staples, nombres ES, tablas, snapshots y planes de comida.
- **Puerta 1**: 0 BLOQUEANTES; los CAMBIOS aplicados por los propietarios y re-verificados.

### Fase 2 · Integración (en paralelo)
| Agente | Encargo | Criterio de salida |
|---|---|---|
| `backend-api` | §5, §9, §11 | ≥ 90 %; test de contrato verde; rendimiento §9 |
| `frontend-ui` | Fase 2 de su definición, primero contra MSW y luego contra la API real | ≥ 85 %; capturas de todas las pantallas |
- **Puerta 2**: flujo manual completo en local (`docker compose up` de desarrollo):
  registrarse → generar → activar → entrenar → ver progreso.

### Fase 3 · Endurecimiento (en paralelo)
`devops-despliegue` (§12), `qa-tests` (§13), `revisor-seguridad` (§11).
Los hallazgos de seguridad y QA se asignan a sus propietarios y se re-verifican.
- **Puerta 3**: 0 hallazgos altos/críticos; E2E, axe y Lighthouse verdes; bootstrap en
  LXC limpio documentado y reproducible.

### Fase 4 · Cierre
`qa-tests` ejecuta la auditoría de §15 → `docs/DOD_REPORT.md`. El orquestador redacta
`CHANGELOG.md` y `docs/USER_GUIDE.md` (en español, con capturas) y crea el tag `v1.0.0`.

## 4. Protocolo de trabajo entre agentes
- **Propiedad de directorios** (ADR 0002): cada agente solo escribe en su zona. Si necesita
  algo de otra zona, lo pide en su handoff; el orquestador lo encarga al propietario.
- **Contratos**: cambios propuestos en `docs/CONTRACT_CHANGES.md` → aprobación del
  arquitecto → versión nueva → aviso a afectados.
- **Handoff** obligatorio en `docs/handoffs/<fase>-<agente>.md` con estas secciones:
  Resumen · Ficheros tocados · Decisiones (y ADRs) · Cómo verificar (comandos exactos) ·
  Métricas (tests, cobertura) · Riesgos/pendientes · Peticiones a otros agentes.
- **Commits** pequeños con Conventional Commits en inglés; una rama por fase y agente
  (`f1/motor-rutinas`) fusionada por el orquestador tras verificar.
- **Bucle de corrección**: máximo 3 idas y vueltas por tarea; si persiste, el orquestador
  lo escala al usuario con diagnóstico.

## 5. Consejos de ejecución
- Encarga tareas de tamaño medio (una sección del MASTER_PROMPT o menos). Los subagentes
  trabajan mejor con criterios de aceptación cerrados que con «hazlo todo».
- Pide siempre al subagente que ejecute los tests antes de devolver el control.
- Todos los agentes usan `claude-sonnet-5` (campo `model` de `.claude/agents/*.md`).
  Ajusta ese campo si quieres otro equilibrio coste/calidad.
