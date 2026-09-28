# Guía de usuario de Forja

Una aplicación web de entrenamiento autoalojada para uso personal o familiar.

## 1. ¿Qué es Forja y para quién?

Forja es una **aplicación web de entrenamiento** que te permite:

- **Explorar una biblioteca de 1.324 ejercicios** con vídeos (GIF animado), fotografías e
  instrucciones paso a paso en español (y otros 9 idiomas).
- **Generar rutinas automáticamente** según tu objetivo (fuerza, hipertrofia, pérdida de peso,
  resistencia, fitness general o tonificación), días por semana, nivel de experiencia, equipamiento
  disponible y limitaciones físicas.
- **Editar rutinas a mano** si quieres cambiar ejercicios, series, repeticiones, descansos o
  notas.
- **Entrenar con un reproductor interactivo** que te muestra el vídeo del ejercicio, te cronometra
  los descansos, registra tu rendimiento y te sugiere progresión de cargas.
- **Seguir tu progreso**: gráficos de volumen semanal, historial de pesos, 1RM estimado, récords
  personales y evolución del peso corporal.
- **Opcionalmente, planificar tu dieta**: cálculo de calorías y macros personalizadas, plan de
  comidas semanal generado a partir de alimentos españoles comunes, lista de la compra.

Forja está diseñada para **entrenar desde casa o el gimnasio en privado**, con tus datos bajo tu
control en tu propio servidor (Proxmox, LXC con Docker, nginx). No requiere conexión de red una
vez descargada la biblioteca: puedes seguir entrenando offline.

Forja es para **personas que entrenan por cuenta propia o con ayuda de un entrenador personal**,
no sustituye el consejo de profesionales de la salud ni de nutrición.

---

## 2. Antes de empezar: avisos importantes

### 2.1 Licencia de los medios de ejercicio

Los vídeos (GIF animados) e imágenes de ejercicio proceden de
[**Gym visual**](https://gymvisual.com/) y se redistribuyen con permiso. **© Gym visual —
https://gymvisual.com/**

Gym visual permite su uso en aplicaciones de entrenamiento personales, pero **no garantiza la
redistribución pública o el reempaquetado sin restricciones**. Antes de exponer tu instancia de
Forja públicamente:

1. Lee los [términos y condiciones de Gym visual](https://gymvisual.com/content/3-terms-and-conditions-of-use).
2. Verifica que tu uso (número de usuarios, si es de pago, alcance geográfico) cumple sus límites.
3. Si tienes dudas, **deja activa la autenticación de medios** (por defecto): solo usuarios
   conectados verán los vídeos e imágenes.

Esta responsabilidad legal corre a cargo de quien despliega Forja, no del software.

### 2.2 Aviso de salud

Forja no sustituye el consejo de profesionales sanitarios, entrenadores personales ni
nutricionistas. Si tienes dudas sobre tu salud o aptitud para entrenar, consulta a un profesional
antes de empezar.

---

## 3. Instalación y primer arranque

### 3.1 Requisitos

Para desplegar Forja necesitas:

- **Un servidor Linux** (Ubuntu, Debian, Rocky, etc.) o un **contenedor LXC en Proxmox**.
- **Docker Engine** y **Docker Compose**.
- **2–4 GB de RAM** y **2 vCPU** como mínimo.
- **12 GB de espacio en disco** para el sistema + **20 GB** para datos (base de datos, vídeos,
  copias de seguridad).

### 3.2 Instalación rápida en Proxmox LXC

Para una guía **paso a paso detallada** incluyendo creación del contenedor LXC en Proxmox,
instalación de Docker, configuración de TLS y copias de seguridad, ve a:
**[`deploy/lxc/README.md`](../deploy/lxc/README.md)**.

Resumen del flujo:

1. **Crear un LXC en Proxmox** con Debian 12 (2 vCPU, 3–4 GB RAM, 12 GB raíz + 20 GB `/var/lib/forja-data`).
2. **Entrar en el LXC e instalar Docker Engine**.
3. **Clonar Forja** y copiar `.env.example` a `.env`.
4. **Personalizar `.env`** (URL pública, puerto, contraseña de BD, si está abierto el registro, etc.).
5. **Ejecutar `make bootstrap`** (construye imágenes, inicia BD, descarga 1.324 ejercicios, crea
   usuario admin).
6. **Configurar nginx externo** (reverse proxy con TLS) o dejar nginx de Forja con TLS en el LXC.

Al terminar, la app está operativa en `http://127.0.0.1:8080` (dentro del LXC) y accesible desde
el exterior a través del proxy.

### 3.3 Primer arranque después de `make bootstrap`

Tras la instalación:

1. **Abre Forja** en tu navegador (PC o móvil).
2. **Regístrate** con tu correo y contraseña (o usa el usuario admin creado en `make bootstrap`).
3. **Sigue el asistente de perfil** (4 pasos):
   - Datos básicos: nombre, sexo (opcional), fecha de nacimiento, altura, peso.
   - Cuestionario PAR-Q: si respondiste «sí» a alguna pregunta, se fija el nivel a «principiante»
     (pero puedes cambiarlo). Consulta a un profesional si tienes dudas.
   - Equipamiento: selecciona qué tienes disponible (gimnasio completo, mancuernas, bandas
     elásticas, solo peso corporal, otro).
   - Limitaciones: si tienes lesiones o patrones de movimiento que evitar, indícalos (Forja
     excluirá ejercicios automáticamente).
4. **Opción de dieta**: actívala si quieres planes de comidas personalizados (puedes cambiarla
   después en Perfil).

¡Ya estás listo para entrenar!

---

## 4. Recorrido por las pantallas principales

### 4.1 Inicio · Hoy

Tu punto de partida. Muestra:

- **Sesión programada del día**: si tienes una rutina activa, ve qué ejercicios tocan hoy y el
  botón «Empezar» para entrenar.
- **Resumen semanal**: sesiones completadas vs. planificadas, volumen total de series.
- **Último récord**: tu personal record más reciente (peso máximo, series de un ejercicio, etc.).
- **Registro de peso rápido**: añade tu peso corporal hoy sin salir de esta pantalla.

Si no tienes rutina activa o es día de descanso, se te sugiere descansar o generar una nueva.

### 4.2 Generador de rutinas

Un asistente paso a paso que construye tu rutina automáticamente:

1. **Objetivo**: elige entre fuerza, hipertrofia, pérdida de peso, resistencia, fitness general o
   tonificación. Se explica brevemente qué hace cada una.
2. **Frecuencia**: cuántos días por semana quieres entrenar (1–7).
3. **Sexo**: Forja preselecciona un énfasis basado en tu sexo (p. ej. glúteos para mujeres), pero
   lo puedes cambiar (Forja **nunca excluye ejercicios ni limita cargas por sexo**).
4. **Nivel y duración**: principiante/intermedio/avanzado, cuántos minutos tienes por sesión
   (20–120).
5. **Equipamiento y limitaciones**: qué tienes disponible y qué grupos musculares o patrones
   evitar (lesiones).
6. **Vista previa**: Forja genera un ejemplo de programa. Ves:
   - Un resumen de una semana: qué ejercicios cada día, series × repeticiones, descansos.
   - Vídeos de cada ejercicio (puedes pasar el cursor o tocar para verlos).
   - Gráfico de distribución de volumen por grupo muscular.
   - Explicación en español de por qué eligió esa estructura.
   - Avisos si algo no es ideal (p. ej., «poco volumen de espalda»).

Acciones en la vista previa:

- **Regenerar**: crea un programa distinto (diferente orden de ejercicios, misma estructura).
- **Regenerar día**: cambia solo un día sin tocar el resto.
- **Cambiar ejercicio**: abre una lista de alternativas para un ejercicio específico.
- **Guardar**: guarda el programa y lo activa (empezará a aparecer en «Hoy»).

### 4.3 Editor de rutinas

Edita cualquier programa después de crearlo:

- **Arrastra y suelta** ejercicios entre días o dentro del mismo día.
- **Crea superseries** (dos ejercicios con descanso corto entre ambos) o circuitos (varios en ronda).
- **Edita parámetros**: series, reps, RIR (repeticiones en reserva), tempo, descansos, notas.
- **Busca ejercicios** desde un panel lateral (filtros: zona, equipamiento, patrón, dificultad).
- **Valida en vivo**: Forja te avisa si la estructura no es balanceada (p. ej., demasiado volumen
  en un día).
- **Deshacer/rehacer**: recupera cambios accidentales.

### 4.4 Reproductor de sesión

Donde realmente entrenas:

- **Vídeo del ejercicio**: GIF grande en la pantalla, con instrucciones paso a paso debajo
  (elige el idioma con un selector).
- **Teclado numérico**: escribe el peso y las reps que levantaste (cada serie).
- **Botón «Serie hecha»**: registra la serie y pasa a la siguiente.
- **Contador de descanso**: anillo que cuenta el tiempo de descanso recomendado (puedes acortar
  15 s, alargar 15 s o saltar). Vibración y sonido al terminar; si sales de la app, recibes una
  notificación en segundo plano.
- **Histórico de rendimiento**: qué peso/reps hiciste la última vez en este ejercicio (te ayuda
  a saber si subir o mantener carga).
- **Sugerencia de progresión**: si completaste todas las series con facilidad, te sugiere cuánto
  subir (siempre confirmas antes de hacerlo).
- **Alternativas en caliente**: si un ejercicio no te funciona hoy, puedes pedirle al reproductor
  que te sugiera otro del mismo patrón.
- **Deshacer serie**: si te equivocaste al registrar una serie, la deshacer.
- **Bloqueo de pantalla**: mientras entrenas, la pantalla no se apaga (incluso si tienes ese ajuste
  global).

Funcionamiento **offline**: todos tus datos de sesión se guardan en el teléfono/navegador. Si
pierdes conexión, puedes seguir entrenando; cuando se reconecta, todo se sincroniza.

### 4.5 Biblioteca de ejercicios

Un catálogo completo de 1.324 ejercicios:

- **Búsqueda**: escribe el nombre del ejercicio (tolerante a acentos, busca en español e inglés).
- **Filtros**: zona del cuerpo (pecho, espalda, hombros, etc.), equipamiento, patrón de movimiento,
  dificultad, favoritos.
- **Mapa muscular interactivo**: toca un músculo en el diagrama (frontal o posterior) para filtrar
  solo ejercicios para ese grupo.
- **Detalles del ejercicio**:
  - Vídeo (GIF) e imagen estática.
  - Músculos objetivo y secundarios (resaltados en el mapa).
  - Equipamiento necesario.
  - Instrucciones paso a paso en tu idioma elegido (10 disponibles).
  - Variantes del mismo ejercicio (diferentes ángulos de cámara, demostradores).
  - Ejercicios alternativos (si quieres cambiar este por otro similar).
  - Tu historial personal en este ejercicio (pesos/series registrados, 1RM estimado).
  - Botón para añadirlo a una rutina durante la edición.

### 4.6 Seguimiento del progreso

Gráficos y estadísticas de tu rendimiento:

- **Calendario de heatmap** (26 semanas): cada día coloreado según si entrenaste o descansaste.
- **Volumen semanal**: gráfico de barras mostrando el total de series por grupo muscular cada
  semana.
- **1RM por ejercicio**: línea de tendencia del 1RM estimado en tus ejercicios principales
  (sirve para ver si estás más fuerte).
- **Récords personales**: tus mejores logros históricos (mayor peso levantado, mayor número de
  reps, mayor volumen en una sesión).
- **Peso corporal**: gráfico de línea con tu peso diario y media móvil de 7 días (para ver
  tendencia sin ruido diario).

### 4.7 Nutrición (opcional)

Si activaste la dieta en el onboarding:

- **Objetivo diario**: anillo visual con tus calorías y macros (proteína, grasa, carbohidratos).
  Muestra cómo vas respecto al objetivo en tono neutro (sin frases punitivas como «te pasaste»).
- **Plan semanal**: 7 días × (desayuno, media mañana, comida, merienda, cena). Cada comida
  muestra alimentos, cantidades en gramos y calorías.
- **Intercambio de alimentos**: cambia un alimento por otro de la misma categoría si no tienes
  ingredientes o no quieres comer lo que está previsto. Forja reajusta automáticamente las
  cantidades.
- **Lista de la compra**: resumen por categoría (frutas, verduras, proteína, etc.) con cantidades
  semanales y checkboxes para marcar conforme compras.
- **Avisos de seguridad**: si eres menor de 18, estás embarazada o lactando, o si tu déficit
  calórico es muy agresivo, Forja te avisa y te recomienda consultar a un profesional.

La app **nunca te fuerza a contar calorías obsesivamente**: es informativa, para ayudarte a
planificar, no para culpabilizarte.

### 4.8 Perfil y ajustes

Configura tu experiencia:

- **Datos personales**: nombre, edad, altura, peso (puedes actualizar en cualquier momento).
- **Unidades**: kilogramos/libras, centímetros/pulgadas.
- **Idioma**: español o inglés (la app se refresca al cambiar).
- **Tema**: oscuro (por defecto, recomendado para entrenar), claro, o automático según tu sistema.
- **Sonidos y vibración**: activa/desactiva al terminar descansos y al marcar series.
- **Descanso por defecto**: duración del descanso sugerido entre series (puedes cambiarla en cada
  sesión).
- **Exportar datos**: descarga todo tu historial en JSON (entrenamientos, rutinas, progreso). Útil
  para copias de seguridad personales.
- **Importar datos**: recupera un backup en JSON que hayas descargado antes.
- **Eliminar cuenta**: borra permanentemente tu cuenta y todos tus datos (pide confirmación de
  contraseña).
- **Sesiones activas**: ve dónde estás conectado (dispositivos) y desconecta sesiones antiguas.
- **Descargar biblioteca offline**: predescargar todos los vídeos de tu programa activo para
  entrenar sin conexión (ahorra datos móviles).
- **Créditos y licencias**: muestra la licencia MIT del dataset de ejercicios, la atribución de
  Gym visual, el identificador del dataset ingerido y el aviso de salud.

### 4.9 Administración (solo admin)

Si eres administrador:

- **Registro abierto/cerrado**: activa o desactiva que nuevos usuarios puedan crear cuentas
  (para invitar solo a familia).
- **Dieta global**: activa o desactiva la función de nutrición para toda la app (afecta a todos
  los usuarios).
- **Usuarios**: lista de todos los usuarios (busca por correo), ve quién es admin, activa/desactiva
  cuentas.
- **Ingesta de ejercicios**: lanza una nueva ingesta si el dataset se actualiza (descarga nuevos
  ejercicios, vídeos, etc.). Ves progreso en tiempo real, historial de ejecuciones anteriores y
  qué ejercicios se añadieron/modificaron.

---

## 5. Exportar y descargar tus datos

Forja permite exportar tus datos en varios formatos:

### 5.1 Exportar todo en JSON

En **Perfil > Eliminar datos**, botón «Exportar». Descargas un JSON con:

- Todos tus entrenamientos (sesiones, series, pesos, reps registrados).
- Todas tus rutinas (programas con estructura completa).
- Tu progreso (1RM, récords, historial de peso corporal).
- Tus planes de dieta (si la tienes activada).
- Tus preferencias (equipamiento, limitaciones, etc.).

Serve como copia de seguridad personal o para migrar a otra instancia de Forja.

### 5.2 Exportar rutina a PDF (próximamente)

Planificado para una próxima versión: descarga cada rutina en PDF con estructura completa
(días, bloques, ejercicios, series, reps, descansos), fotos de ejercicios e instrucciones,
para imprimir o compartir con tu entrenador.

### 5.3 Exportar calendario a ICS (próximamente)

Planificado para una próxima versión: sincroniza tu calendario de entrenamientos con Google
Calendar, Apple Calendar, Outlook o cualquier app que lea formato `.ics`, para no olvidarte
de tus sesiones.

---

## 6. Desactivar o eliminar tu cuenta

### 6.1 Desactivar temporalmente

Para pausar Forja sin borrar datos:

1. Ve a **Perfil > Administrador** (la pestaña Admin si eres admin).
2. Desactiva tu usuario (click en el usuario en la lista).

Tu cuenta no puede iniciar sesión, pero los datos se mantienen. Un admin puede reactivarla.

### 6.2 Eliminar permanentemente

Para borrar tu cuenta y todos tus datos de forma irreversible:

1. Ve a **Perfil > Eliminar datos**.
2. Haz click en «Eliminar cuenta».
3. Se te pide que confirmes escribiendo tu contraseña.
4. Los datos se borran al instante, sin recuperación.

Consejo: antes de eliminar, descarga un backup en JSON (botón «Exportar» en la misma pantalla).

---

## 7. Preguntas frecuentes

**P: ¿Es necesaria conexión de red para entrenar?**

R: No. Una vez descargada la biblioteca (manualmente en Perfil o en la primera sesión), puedes
entrenar offline. Los datos se sincronizarán cuando recuperes conexión.

**P: ¿Cómo deshago una sesión registrada por error?**

R: La sesión se sincroniza al terminarla. Pídele al administrador que la borre desde la BD, o
[abre un issue](https://github.com/forja-kit/forja-kit/issues) con tu situación.

**P: ¿Puedo compartir una rutina con otro usuario?**

R: No directamente. Cada usuario crea o edita sus propias rutinas. Para compartir, puedes:
- Anotarla a mano (días, ejercicios, series).
- Pedir al otro usuario que genere con los mismos parámetros (las rutinas son deterministas con
  la misma semilla).

**P: ¿Qué pasa si mis datos se pierden?**

R: Forja realiza copias de seguridad automáticas cada día. El administrador puede restaurarlas.
Tú también puedes descargar un backup en JSON desde Perfil.

**P: ¿Funciona Forja en móvil?**

R: Sí, es responsive (funciona en cualquier tamaño de pantalla) y se puede instalar como una
aplicación PWA (botón de instalación en el navegador; no requiere App Store).

**P: Si tengo dudas sobre mi salud o una lesión, ¿qué hago?**

R: Consulta siempre a un profesional sanitario. Forja es una herramienta de seguimiento, no de
diagnóstico ni tratamiento.

---

## 8. Contacto y reportes

Si encuentras un error o tienes una sugerencia:

- **Issues**: [https://github.com/forja-kit/forja-kit/issues](https://github.com/forja-kit/forja-kit/issues)
  (requiere cuenta de GitHub; en inglés).
- **Contacto del administrador**: pídele a quien desplegó Forja para tu familia o equipo.

---

**¡Que disfrutes entrenando!**
