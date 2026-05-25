# Observability — Decisiones de Diseño y Plan de Implementación

> Documento completo del componente **`obs/`** del framework Phronesis. Recoge las decisiones cerradas, su motivación, y el plan de implementación.

---

## Propósito del componente

`obs/` es la infraestructura de observabilidad del framework. Permite que cualquier componente (tools, providers, agents, runtime, pipelines) emita **trazas, spans, métricas y eventos** estructurados.

Se apoya en **OpenTelemetry** como estándar del ecosistema.

### Distinción con `logging.py`

- **Logging** responde a "¿qué pasó en este punto?" → eventos discretos, texto, ya implementado en `_internal/logging.py`.
- **Observability** responde a "¿cómo se comportó el sistema?" → estructura jerárquica, correlación, medición.

Ambos son complementarios. Cuando obs está activo, los logs se enriquecen automáticamente con `trace_id` y `span_id` para correlación.

### Lo que NO cubre

- **Logging textual** — vive en `_internal/logging.py`.
- **Visualización** — eso es el backend (Jaeger, Datadog, Grafana, etc.).
- **Profiling de bajo nivel** — herramientas distintas.
- **APM completo** (alertas, incident management) — fuera de alcance.

---

## Índice de decisiones

1. [Dependencia con OpenTelemetry: opcional vía extras](#d-01)
2. [Decoradores y context managers como API principal](#d-02)
3. [Convenciones de nombres de spans](#d-03)
4. [Catálogo cerrado de atributos estándar](#d-04)
5. [Catálogo cerrado de métricas estándar](#d-05)
6. [Configuración: default razonable + explícita](#d-06)
7. [Correlación con logging vía filter automático](#d-07)
8. [TraceId de Phronesis = trace_id de OpenTelemetry](#d-08)
9. [API directa de OpenTelemetry para métricas](#d-09)
10. [Soporte de exporters: OTLP como first-class](#d-10)

---

<a id="d-01"></a>
## D-01. Dependencia con OpenTelemetry: opcional vía extras

**Decisión:** OpenTelemetry es una dependencia **opcional** vía extras de pip.

- `pip install phronesis-framework` → obs no disponible. Llamadas a `@traced` y `start_span` son **no-op** (no hacen nada).
- `pip install phronesis-framework[obs]` → OpenTelemetry SDK instalado. Llamadas a obs funcionan.

**Alternativas consideradas:**

- Obligatoria (siempre instalada como dependencia base).
- Solo si está instalada (auto-detección sin extra).

**Razón principal:**

- Coherencia con el patrón de providers (extras opcionales por proveedor).
- Usuarios que no necesitan obs no cargan con OpenTelemetry.
- Failure mode claro: si el usuario quiere obs y no tiene el extra, el framework falla con mensaje explícito al configurar ("Install with `pip install phronesis-framework[obs]`").
- Sin magia: el modo no-op es explícito, no auto-detectado.

### Implementación del modo no-op

Una variable global `_obs_available` se determina al importar. Si no está disponible:

- Decoradores `@traced` devuelven la función original sin envolver.
- `start_span(...)` devuelve un context manager que no hace nada.
- Funciones de métricas son no-op.

Cero overhead en runtime cuando obs no está instalado.

---

<a id="d-02"></a>
## D-02. Decoradores y context managers como API principal

**Decisión:** La API para crear spans desde el código del framework es vía **decoradores** (`@traced`) y **context managers** (`async with start_span(...)`). La API funcional de OpenTelemetry está disponible como escape hatch para casos avanzados.

**Alternativas consideradas:**

- API funcional (start/end explícitos) como camino principal.
- Wrapping automático del framework (sin decoradores explícitos).

**Razón principal:**

- Es lo idiomático en Python y en OpenTelemetry.
- Consistencia con el resto del framework (retry, logging usan el mismo patrón).
- Span se gestiona automáticamente: se crea al entrar, se cierra al salir, captura excepciones.
- El 95% de los casos encajan con decoradores y context managers; los exóticos pueden usar la API funcional de OTel directamente.

### Ejemplos de uso

```python
from phronesis.obs import traced, start_span

# Decorador
@traced("phronesis.tools.invoke")
async def invoke_tool(tool, args, ctx):
    ...

# Context manager
async with start_span("phronesis.providers.complete") as span:
    span.set_attribute("provider.name", "anthropic")
    response = await client.post(...)
```

---

<a id="d-03"></a>
## D-03. Convenciones de nombres de spans

**Decisión:** Todos los spans del framework siguen la convención `phronesis.<component>.<operation>`. Los nombres son **estáticos**; la variabilidad va siempre en atributos, no en el nombre.

**Alternativas consideradas:**

- Libre por componente.
- Jerarquía rica que incluye nombres de entidades concretas en el nombre del span.

**Razón principal:**

- Es lo que recomienda OpenTelemetry (semantic conventions).
- Cardinalidad controlada: un número finito de nombres de spans, no explota al añadir nuevas tools o providers.
- Filtrado limpio: `phronesis.*`, `phronesis.providers.*`, etc.

### Catálogo inicial de nombres

**Tools:**
- `phronesis.tools.invoke`
- `phronesis.tools.validate`
- `phronesis.tools.schema_generation`

**Providers:**
- `phronesis.providers.complete`
- `phronesis.providers.stream`
- `phronesis.providers.structured_output`

**Agents:**
- `phronesis.agents.run`
- `phronesis.agents.step`
- `phronesis.agents.tool_call`

**Runtime:**
- `phronesis.runtime.execute`

**Pipelines:**
- `phronesis.pipelines.run`
- `phronesis.pipelines.stage`

**Memory:**
- `phronesis.memory.read`
- `phronesis.memory.write`

**Policies:**
- `phronesis.policies.evaluate`

Catálogo ampliable cuando aparezcan operaciones nuevas que no encajen.

---

<a id="d-04"></a>
## D-04. Catálogo cerrado de atributos estándar

**Decisión:** Catálogo cerrado de atributos que todos los componentes usan con los mismos nombres. La variabilidad de cada operación (qué tool concreta, qué provider, qué agente) va en estos atributos, no en el nombre del span.

**Alternativas consideradas:**

- Libres por componente.
- Mezcla: estándar obligatorios + libres con prefijo.

**Razón principal:**

- Consistencia total: dashboards y queries funcionan igual sin importar dónde se midió.
- Sigue las semantic conventions de OpenTelemetry para LLM observability.
- "Libres con prefijo" se descontrola en la práctica: vuelve a la opción de libre.

### Catálogo inicial

**Identificadores:**
- `tool.id`, `tool.tid`, `tool.name`
- `agent.id`, `agent.name`
- `pipeline.id`, `pipeline.name`
- `run.id`, `session.id`, `tool_call.id`, `message.id`

**Provider:**
- `provider.name` — `"anthropic"`, `"openai"`, etc.
- `provider.model` — modelo concreto.

**Operación / resultado:**
- `operation.duration_ms`
- `operation.success` — bool.
- `error.type`, `error.message`

**Métricas operativas:**
- `tokens.input`, `tokens.output`, `tokens.total`
- `cost.usd`

**Streaming:**
- `stream.chunks_count`
- `stream.first_chunk_ms`

Catálogo ampliable cuando aparezca una necesidad real.

---

<a id="d-05"></a>
## D-05. Catálogo cerrado de métricas estándar

**Decisión:** El framework emite **automáticamente** un catálogo cerrado de métricas estándar. El usuario no las configura; aparecen al instalar el extra `[obs]` y activar configuración.

**Alternativas consideradas:**

- Solo primitivas: el usuario emite las métricas que quiera.
- Mezcla: catálogo estándar + custom por componente.

**Razón principal:**

- Observabilidad útil out of the box. Sin configurar, métricas valiosas aparecen.
- Coherencia con D-04 (catálogo cerrado de atributos).
- Toda app de agentes va a querer las mismas métricas básicas (tokens, latencia, invocaciones); el framework las provee.

### Catálogo inicial de métricas

**Tools:**
- `phronesis.tool.invocations` (counter) — atributos: `tool.id`, `tool.name`, `agent.id`, `operation.success`.
- `phronesis.tool.duration` (histogram, seg) — atributos: `tool.id`.
- `phronesis.tool.errors` (counter) — atributos: `tool.id`, `error.type`.

**Providers:**
- `phronesis.provider.requests` (counter) — atributos: `provider.name`, `provider.model`, `operation.success`.
- `phronesis.provider.tokens.input` (counter) — atributos: `provider.name`, `provider.model`.
- `phronesis.provider.tokens.output` (counter) — atributos: `provider.name`, `provider.model`.
- `phronesis.provider.duration` (histogram, seg) — atributos: `provider.name`, `provider.model`.

**Agents:**
- `phronesis.agent.runs` (counter) — atributos: `agent.id`, `operation.success`.
- `phronesis.agent.run_duration` (histogram, seg) — atributos: `agent.id`.
- `phronesis.agent.tool_calls_per_run` (histogram, count) — atributos: `agent.id`.

**Pipelines:**
- `phronesis.pipeline.runs` (counter) — atributos: `pipeline.id`.
- `phronesis.pipeline.run_duration` (histogram, seg).

**Retries:**
- `phronesis.retry.attempts` (counter) — atributos: `operation.success`.

Catálogo ampliable cuando lleguen componentes que aporten otras métricas relevantes.

---

<a id="d-06"></a>
## D-06. Configuración: default razonable + explícita

**Decisión:** Comportamiento por defecto razonable + configuración explícita vía `configure_obs(...)`.

**Default (sin configurar):**
- `TracerProvider` con `ConsoleSpanExporter` (spans a stdout, formato legible).
- Sampling 100%.
- Métricas no exportadas (requieren configuración explícita).

**Configuración explícita:**

```python
from phronesis.obs import configure_obs

configure_obs(
    exporter="otlp",
    endpoint="http://localhost:4317",
    sampling=0.1,
    service_name="my-service",
)
```

**Alternativas consideradas:**

- Cero configuración por defecto (boilerplate obligatorio).
- Auto-detección desde variables de entorno.

**Razón principal:**

- Funciona out of the box: instalar `[obs]` y ver spans en consola sin escribir código.
- Una sola llamada cubre el caso de producción.
- Sin auto-detección: el comportamiento depende del código, no del entorno. Más predecible y debuggable.

---

<a id="d-07"></a>
## D-07. Correlación con logging vía filter automático

**Decisión:** Cuando obs está activo, se instala automáticamente un `logging.Filter` que añade `trace_id` y `span_id` a cada log record si hay un span activo.

**Alternativas consideradas:**

- Wrapper explícito que el usuario aplica.

**Razón principal:**

- Cumple lo prometido en `LOGGING-IMPLEMENTATION.md`: "cuando obs exista, los logs llevarán trace_id automáticamente".
- Cero código adicional para el usuario: la correlación funciona sin configurar.
- Sin obs activo, simplemente no hay filter — sin magia que confunda.

### Comportamiento

Cuando se loggea desde dentro de un span activo:

```json
{
  "timestamp": "2026-05-23T10:14:23.482Z",
  "level": "INFO",
  "logger": "phronesis.tools",
  "message": "Tool registered",
  "run_id": "run-abc123",
  "tool_id": "TID-A3F2B1C0",
  "trace_id": "5b8aa5a2d2c872e8321cf37308d69df2",
  "span_id": "051581bf3cb55c13"
}
```

Los campos `trace_id` y `span_id` permiten saltar del log al trace completo en el backend de observabilidad.

---

<a id="d-08"></a>
## D-08. TraceId de Phronesis = trace_id de OpenTelemetry

**Decisión:** El `TraceId` (Runtime ID) de Phronesis es el mismo `trace_id` que genera OpenTelemetry.

**Alternativas consideradas:**

- IDs separados con mapeo entre ambos.

**Razón principal:**

- Son el mismo concepto: identifica una ejecución completa.
- Sin duplicación, sin necesidad de mapeo.
- Cuando lleguen Runtime IDs (post-MVP), el `TraceId` de un run es el del span raíz.

### Implicación

El runtime no genera `TraceId`s propios. Cuando arranca un run, el span raíz tiene un `trace_id` de OpenTelemetry, y ese es el `TraceId` que se usa en logs, en el resto de spans del run, y en cualquier referencia futura.

Si obs no está activo (no se instaló `[obs]`), el `TraceId` se genera con UUID v4 normalmente — no hay incompatibilidad.

---

<a id="d-09"></a>
## D-09. API directa de OpenTelemetry para métricas

**Decisión:** Las métricas usan la API de métricas de OpenTelemetry directamente, sin wrapper propio del framework.

**Alternativas consideradas:**

- Wrapper propio que abstrae la API de OTel.

**Razón principal:**

- La API de métricas de OTel es lo bastante estable y limpia.
- Wrappear añade mantenimiento sin valor.
- Si en el futuro hay razón concreta para abstraer, se hace entonces.

### Implicación

El catálogo de métricas (D-05) se define como instrumentos de OpenTelemetry (`Counter`, `Histogram`). El framework expone funciones para incrementarlos/registrar valores:

```python
from phronesis.obs import metrics

metrics.tool_invocations.add(1, attributes={"tool.id": tool.id.canonical})
metrics.provider_duration.record(duration_seconds, attributes={"provider.name": "anthropic"})
```

Los instrumentos se crean al configurar obs y son accesibles vía `obs.metrics`.

---

<a id="d-10"></a>
## D-10. Soporte de exporters: OTLP como first-class

**Decisión:** El framework soporta **OTLP** como exporter de primera clase. `ConsoleSpanExporter` está disponible para desarrollo. Otros exporters (Jaeger, Zipkin, etc.) se pueden usar pasando un exporter custom a `configure_obs(...)` pero no son first-class.

**Alternativas consideradas:**

- Soporte first-class de varios exporters (Jaeger, Zipkin, etc.).

**Razón principal:**

- OTLP es el estándar moderno; todos los backends serios lo soportan.
- Jaeger y Zipkin tienen sus exporters propios en el ecosistema OTel — quien los necesite los pasa como custom.
- Menos código que mantener y testar en el framework.

### Configuración

```python
configure_obs(
    exporter="otlp",
    endpoint="http://localhost:4317",
)
```

```python
# Console (default para desarrollo)
configure_obs(exporter="console")
```

```python
# Custom exporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

configure_obs(
    exporter_instance=JaegerExporter(...),
)
```

---

## Principios transversales

Los criterios que guían las decisiones:

1. **Catálogos cerrados con disciplina.** Tanto atributos como métricas son listas finitas que crecen con discusión, no libremente.
2. **Convenciones sobre configuración.** El usuario tiene comportamiento útil por defecto sin tocar nada.
3. **No-op cuando obs no está disponible.** El framework no falla; simplemente no produce datos.
4. **Reutilización del ecosistema.** OpenTelemetry hace el trabajo duro; el framework solo aporta convenciones.
5. **Composición con logging.** Obs y logging son complementarios; se enlazan automáticamente.

---

## Plan de implementación

### Orden recomendado

1. **Infraestructura no-op base.** Las funciones públicas (`traced`, `start_span`, `configure_obs`, etc.) existen y son no-op por defecto.
2. **Detección de OpenTelemetry.** Si el extra `[obs]` está instalado, las funciones se activan.
3. **`configure_obs(...)` con default razonable** (ConsoleSpanExporter).
4. **Decoradores y context managers** para spans.
5. **Catálogo de métricas** — registro de instrumentos al configurar.
6. **Filter de logging** para correlación automática.
7. **Instrumentación de componentes**: añadir spans y métricas a tools, providers, agents (esto es trabajo cruzado con cada componente).
8. **Tests** — incluyendo el modo no-op (cuando obs no está instalado).

### Estructura de archivos

```
phronesis/obs/
├── __init__.py            # API pública: traced, start_span, configure_obs, metrics
├── config.py              # configure_obs y lógica de inicialización
├── spans.py               # traced, start_span
├── metrics.py             # catálogo de métricas, helpers
├── logging_filter.py      # filter para correlación con logs
├── attributes.py          # constantes de nombres de atributos
└── _noop.py               # implementaciones no-op
```

### Dependencias

**Sin el extra `[obs]`:**
- Solo stdlib.

**Con el extra `[obs]`:**
- `opentelemetry-api`
- `opentelemetry-sdk`
- `opentelemetry-exporter-otlp` (para OTLP)

---

## Decisiones pendientes (a tomar al implementar)

- **Formato exacto de los nombres de los instrumentos de métricas** (snake_case, dot-separated, etc.). OTel tiene convenciones; las seguimos al implementar.
- **Política de sampling configurable.** Por defecto 100%, pero `configure_obs` debe permitir sampling adaptativo. Decisión al ver el caso real.
- **Cómo se inicializa el `MeterProvider`.** Similar al `TracerProvider` pero con sus particularidades.
- **Manejo de spans en código async vs sync.** OpenTelemetry maneja ambos; decisión menor al implementar.

---

## Lo que queda fuera del alcance inicial

- **Alertas y SLOs.** Eso es trabajo del backend de observabilidad, no del framework.
- **Profiling de bajo nivel.** Otras herramientas.
- **Tracing con auto-instrumentation de librerías externas** (auto-instrumentar httpx, etc.). Si el usuario lo quiere, lo configura él mismo con los paquetes de auto-instrumentación de OTel.
- **Distribución de traces a través de mensajes/queues.** Cuando se diseñe `comm/`, se decidirá cómo viaja el contexto de trace.

---

## Definición de hecho

El componente `obs/` está listo cuando:

- Funciona en modo no-op cuando no está el extra `[obs]`.
- Funciona con `[obs]` instalado, default a `ConsoleSpanExporter`.
- `configure_obs(...)` permite OTLP, console, y exporter custom.
- Decoradores `@traced` y context manager `start_span` funcionan en código async y sync.
- Atributos del catálogo D-04 están definidos como constantes accesibles.
- Métricas del catálogo D-05 están registradas y son accesibles.
- Filter de logging añade `trace_id` y `span_id` automáticamente cuando hay span activo.
- Tests cubren los casos: no-op, con obs, correlación con logs, configuración custom.
- Documentación de cómo instrumentar nuevos componentes (para futuras adiciones del framework).

---

## Principios para decisiones futuras

Cuando aparezcan decisiones nuevas durante la implementación:

1. **Si dudas entre "soportar todo" y "soportar lo estándar", elige estándar.** OTel define el camino; lo seguimos.
2. **Si dudas entre "magia automática" y "configuración explícita", elige explícita.** Excepto donde decidimos lo contrario (correlación con logging, que es opt-in vía instalación del extra).
3. **Catálogos cerrados se amplían con discusión, no en silencio.** Cualquier nuevo atributo o métrica pasa por revisión.
4. **El framework no decide políticas de retención, sampling adaptativo, alertas, etc.** Eso lo configura el usuario.
