# Kit de agentes · Forja

Kit para construir con Claude Code y subagentes una app web de entrenamiento autoalojada a
partir de https://github.com/hasaneyldrm/exercises-dataset (1.324 ejercicios con GIF,
miniatura e instrucciones en 10 idiomas).

## Contenido
| Ruta | Qué es |
|---|---|
| `MASTER_PROMPT.md` | Especificación completa (fuente de verdad) |
| `ORCHESTRATION.md` | Fases, puertas, protocolo y **prompt de arranque** para la sesión principal |
| `CLAUDE.md` | Reglas del proyecto que Claude Code carga automáticamente |
| `.claude/agents/` | 10 subagentes: arquitecto, ingesta-datos, motor-rutinas, motor-nutricion, backend-api, frontend-ui, devops-despliegue, qa-tests, revisor-seguridad, experto-entrenamiento |
| `specs/` | Tablas YAML del motor (splits, volumen, prescripción, periodización, sexo, nutrición, normalización, reglas de enriquecimiento, glosario ES, staples con ids reales) — validadas contra el dataset |
| `docs/dataset-analysis.md` | Análisis real del dataset: vocabularios, recuentos y peculiaridades |

## Uso rápido
1. Crea un repo vacío, copia este kit dentro y haz commit.
2. Abre `claude` en la raíz.
3. Pega el prompt de arranque de `ORCHESTRATION.md` §2.

## Aviso sobre los GIF e imágenes
Los datos del dataset son MIT, pero los medios son © Gym visual y se redistribuyen con
permiso a 180×180. El kit fuerza atribución visible, medios sin modificar y acceso solo
autenticado por defecto. Para uso público, revisa
https://gymvisual.com/content/3-terms-and-conditions-of-use.
