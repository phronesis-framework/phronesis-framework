# Context — Decisiones de Diseño

> Documento completo del componente **Context** del framework Phronesis. Recoge las 6 decisiones cerradas, su motivación, y notas de implementación. Diseñado en paralelo con Agents debido a su dependencia directa.

---

## Propósito del componente

`context/` transforma el **estado del run** en lo que ve el LLM en cada iteración del loop de tool calling.

La frontera con `agents/`:

- **`agents/`** posee: system prompt, historial de mensajes del run, tool_calls hechos, resultados. Ejecuta el loop, llama al provider, ejecuta tools, construye el `Result`.
- **`context/`** hace: dado el estado del run, devolver `list[Message]` lista para mandar al provider en la siguiente iteración.

En el MVP, dos builders disponibles: uno simple (historial completo) y uno con compactación (estilo Claude Code).

### Por qué este componente importa

Aunque su versión MVP simple es trivial, **la abstracción está justificada desde el día uno**: la frontera entre "qué es del agente" y "qué es del contexto" es clara, y separarlo permite que el agente nunca cambie cuando llegue compactación, RAG, retrieval de memoria, etc.

---

## Índice de decisiones

1. [Protocol vs clase concreta](#d-01)
2. [Cómo se configura en el agente](#d-02)
3. [Gestión del límite de tokens (dos builders por defecto)](#d-03)
4. [Nombre del objeto principal](#d-04)
5. [Firma del método principal](#d-05)
6. [Statelessness](#d-06)

---

<a id="d-01"></a>
## D-01. Protocol + implementación por defecto

**Decisión:** `ContextBuilder` como **Protocol**, con implementaciones concretas provistas por el framework.

```python
class ContextBuilder(Protocol):
    async def build(self, input: BuildInput) -> list[Message]: ...
```

Implementaciones del MVP:
- `DefaultContextBuilder` — simple (historial completo).
- `CompactingContextBuilder` — opt-in (con compactación).

El usuario puede aportar su propio builder implementando el Protocol.

**Alternativas consideradas:**

- Solo clase concreta (sin punto de extensión).
- Clase abstracta con método sobreescribible (herencia).

**Razón principal:**

- Coherencia con providers (`LLMProvider` es Protocol). Si para providers vale, para context vale.
- Casos de uso reales esperados: RAG, compactación custom, retrieval de memoria.
- No es abstracción especulativa: hay demanda obvia.
- Implementación por defecto cubre el MVP simple.

---

<a id="d-02"></a>
## D-02. Configurable en el agente

**Decisión:** El context builder es **parámetro del decorador `@agent`**. Default = `DefaultContextBuilder()` si no se especifica.

```python
@agent(model=anthropic("..."), tools=[...])  # usa DefaultContextBuilder
async def simple_agent() -> str: ...

@agent(
    model=anthropic("..."),
    tools=[...],
    context_builder=CompactingContextBuilder(),
)
async def long_conversation_agent() -> str: ...
```

**Alternativas consideradas:**

- Siempre el default, no configurable.
- Configurable globalmente (a nivel framework).

**Razón principal:**

- Coherencia con cómo se configura todo lo demás del agente (model, tools).
- Granularidad correcta: cada agente puede tener su propio builder.
- Configuración global = estado oculto, mala práctica.
- Cero ceremonia para el caso común: no pasar el parámetro usa el default.

**Implicación en agents D-02:**

Añade `context_builder: ContextBuilder | None = None` a los parámetros del agente. No rompe la decisión D-02 de agents, la complementa.

---

<a id="d-03"></a>
## D-03. Gestión del límite de tokens: dos builders por defecto

**Decisión:** El MVP provee dos builders. El usuario elige cuál usar según el caso de uso.

### `DefaultContextBuilder`

Simple. Devuelve `system_prompt + historial completo`. No estima tokens, no trunca, no compacta. Si el historial supera el límite del modelo, el provider falla con error específico (que el agente envuelve en `AgentExecutionError`).

Sin dependencias adicionales. Failure mode claro.

### `CompactingContextBuilder`

Opt-in. Estima tokens del historial. Cuando supera un umbral, invoca un LLM para compactar (estilo Claude Code).

**Sub-decisiones del compactador (todas cerradas):**

| Sub-decisión | Valor |
|---|---|
| 3.1 Trigger de compactación | Umbral configurable, default 80% del límite del modelo |
| 3.2 Cómo se obtiene el límite del modelo | Provider lo expone (`context_window_size()`) |
| 3.3 Cómo se estiman los tokens | Provider lo expone (`count_tokens(messages)`) |
| 3.4 LLM compactador | Configurable; default = mismo provider del agente |
| 3.5 Qué preserva | `system_prompt` + N mensajes recientes (N configurable, default razonable) |
| 3.6 Pares tool_call/tool_result | Protegidos en la lógica (no se rompen al compactar) |
| 3.7 Si falla la compactación | Propagar error (`ContextBuilderError` o similar); sin fallback |

**Razón principal de la decisión global:**

- El MVP simple sigue siendo simple.
- Para conversaciones largas (caso central como Claude Code), hay opción del framework lista.
- No se impone compactación a agentes que no la necesitan (clasificadores, redactores).
- "Just works" para usuarios avanzados que la activan.

### Adiciones al Protocol LLMProvider

El compactador necesita información del provider. Esto añade dos métodos al Protocol:

- `context_window_size() -> int` — tokens máximos del modelo configurado.
- `count_tokens(messages: list[Message]) -> int` — estimación precisa de tokens del historial.

Estas adiciones se documentarán como cambios al documento de providers cuando se implemente.

### Convención para mensajes compactados

Cuando `CompactingContextBuilder` compacta, produce un mensaje especial que representa el resumen. La convención (detalle de implementación):

- Un tipo de bloque específico (e.g. `CompactionSummaryBlock`) o un atributo de mensaje.
- En la siguiente iteración, el builder lo reconoce y no vuelve a compactar esa parte.

Esto es coherencia con la decisión de statelessness (D-06): el estado del compactador vive en el historial, no en el builder.

---

<a id="d-04"></a>
## D-04. Nombre del objeto principal

**Decisión:** `ContextBuilder` como nombre del Protocol. Sin colisión con el `Context` de tools.

```python
# phronesis/context/
ContextBuilder            # Protocol
DefaultContextBuilder     # implementación simple
CompactingContextBuilder  # implementación con compactación
```

**Alternativas consideradas:**

- `Context` como nombre del Protocol (colisiona con `Context` de tools).
- Renombrar el `Context` de tools a `ToolContext` para liberar el nombre.
- `BuiltContext` envolviendo el resultado.

**Razón principal:**

- Sin colisión con `Context` de tools (ya implementado y usado).
- "ContextBuilder" describe lo que hace: construye el contexto.
- Renombrar tools es coste real sin beneficio proporcional.
- Devolver `list[Message]` plano es suficiente; un envoltorio rico se puede añadir después sin romper compatibilidad.

---

<a id="d-05"></a>
## D-05. Firma del método principal

**Decisión:** Método `build(input: BuildInput) → list[Message]`. La entrada es un dataclass ampliable.

```python
class ContextBuilder(Protocol):
    async def build(self, input: BuildInput) -> list[Message]: ...

@dataclass(frozen=True)
class BuildInput:
    system_prompt: str
    history: list[Message]
    new_input: Message | None
    provider: LLMProvider
    # ampliable sin romper
```

**Campos del MVP:**

- `system_prompt: str` — el system prompt del agente.
- `history: list[Message]` — mensajes acumulados del run hasta ahora.
- `new_input: Message | None` — el mensaje nuevo del usuario en esta iteración (None en iteraciones internas del loop donde solo hay resultados de tools).
- `provider: LLMProvider` — necesario para el compactador. Pasado siempre; el default lo ignora.

**Diferidos para cuando lleguen sus componentes:**

- `memory: MemoryStore | None`
- `policies: list[Policy]`
- `metadata: Mapping[str, str]` (del RunRequest)

**Alternativas consideradas:**

- Argumentos sueltos en la firma.

**Razón principal:**

- Ampliable sin romper: cuando lleguen memory, retrieval, etc., se añaden campos.
- Coherencia con `RunRequest`/`LLMRequest` (mismo patrón).
- Más fácil de mockear en tests.

---

<a id="d-06"></a>
## D-06. Statelessness

**Decisión:** El context builder es **stateless**. El estado vive en el `BuildInput`/historial, no en la instancia del builder.

```python
# Una instancia sirve a infinitos agentes y runs concurrentes
default_builder = DefaultContextBuilder()

@agent(model=..., tools=[...], context_builder=default_builder)
async def agent_a() -> str: ...

@agent(model=..., tools=[...], context_builder=default_builder)
async def agent_b() -> str: ...
```

**Alternativas consideradas:**

- Stateful por run (con limpieza entre runs).

**Razón principal:**

- Reutilización máxima: una instancia sirve a todos los agentes y runs simultáneamente sin contaminación.
- Concurrencia segura sin esfuerzo.
- Coherencia con la filosofía del framework (`AgentSpec` inmutable, agente stateless, estado en `Session`).
- Para el compactador: el resultado de la compactación vive en el historial del run que el agente posee. El builder ve el resumen en el `BuildInput` siguiente y sabe que esa parte ya está compactada.

### Implicación práctica para el compactador

Flujo de una compactación:

1. `CompactingContextBuilder.build()` decide compactar (historial supera umbral).
2. Llama al provider con prompt de compactación, obtiene resumen.
3. Construye un mensaje especial (con `CompactionSummaryBlock` o equivalente) que representa el resumen.
4. Devuelve `[system, summary_message, ...mensajes_recientes_preservados]`.
5. El agente recibe esos mensajes, los manda al provider, continúa el loop.
6. En la siguiente iteración, el `BuildInput` trae el historial con el summary dentro.
7. El builder ve el summary en el historial, sabe que esa parte ya está compactada, y no la vuelve a tocar.

El builder es función pura. El estado vive en datos (historial).

---

## Principios transversales

1. **Frontera clara con agents.** El agente posee el estado; el builder transforma estado en mensajes para el provider.
2. **Builder es función pura.** Stateless, sin efectos secundarios fuera del provider call (en el caso del compactador).
3. **Extensibilidad desde el día uno.** Protocol + implementaciones, sin esperar a refactor.
4. **El compactador no es "magia".** Es opt-in explícito. El usuario que no lo quiere, no paga el coste.
5. **Coherencia con providers, agents, tools.** Mismo patrón de Protocol + implementaciones concretas, configurables a nivel agente.

---

## Estructura de archivos

```
phronesis/context/
├── __init__.py           # API pública: ContextBuilder, DefaultContextBuilder, CompactingContextBuilder, BuildInput
├── protocol.py           # ContextBuilder Protocol
├── input.py              # BuildInput dataclass
├── default.py            # DefaultContextBuilder
├── compacting.py         # CompactingContextBuilder
└── errors.py             # ContextBuilderError (y posibles subclases)
```

---

## Dependencias del componente

- `phronesis/core/messages.py` — el tipo `Message` y sus bloques.
- `phronesis/providers/` — `LLMProvider` Protocol (necesario para `BuildInput.provider`).
- `phronesis/_internal/logging.py` — logging del compactador.
- `phronesis/obs/` — spans del compactador (instrumentación).

---

## Lo que queda fuera del alcance inicial

- **Memory store / retrieval.** Cuando exista `memory/`, se añadirá al `BuildInput`.
- **Policies que afecten al contexto.** Cuando exista `policies/`, se añadirán al `BuildInput`.
- **TruncatingContextBuilder** (truncado simple sin compactación). Si surge demanda, se añade como builder adicional.
- **SummarizingContextBuilder** (resumen sin compactación). Variante del compactador.
- **RAGContextBuilder** (retrieval-augmented). Builder específico para RAG.
- **Warnings en `DefaultContextBuilder` al acercarse al límite.** Se podría añadir; ahora mismo el default falla silenciosamente vía el provider.
- **Compactación incremental** (compactar partes específicas en vez de todo el historial antiguo).

Todas estas extensiones son compatibles con el Protocol actual: se implementan como nuevos builders sin romper API.

---

## Definición de hecho

El componente Context está listo cuando:

- `ContextBuilder` Protocol definido en `protocol.py`.
- `BuildInput` dataclass definido en `input.py`.
- `DefaultContextBuilder` implementado: devuelve `[system_prompt, *history]` sin transformación.
- `CompactingContextBuilder` implementado con las siete sub-decisiones de D-03.
- Convención de mensajes compactados definida (bloque específico o atributo).
- Adiciones a `LLMProvider` aplicadas: `context_window_size()` y `count_tokens()`.
- Tests:
  - `DefaultContextBuilder` con historial vacío, con historial pequeño, con historial grande (sin gestión).
  - `CompactingContextBuilder` con historial bajo umbral (no compacta).
  - `CompactingContextBuilder` con historial sobre umbral (compacta).
  - Pares tool_call/tool_result preservados en compactación.
  - Fallo del provider compactador propaga error.
  - Stateless: una misma instancia con dos runs concurrentes no se contamina.
- Integración con agents: el loop del agente llama a `build()` en cada iteración.
- Instrumentación obs: span `phronesis.context.build` con atributos básicos (builder.name, history.size, compacted bool).

---

## Cambios pendientes en otros componentes

Estos cambios deben aplicarse en sus componentes respectivos cuando se implemente context:

### En `phronesis/providers/protocol.py`

Añadir al `Protocol LLMProvider`:

- `context_window_size() -> int` — tokens máximos del modelo.
- `count_tokens(messages: list[Message]) -> int` — estimación de tokens.

### En `phronesis/agents/`

- Añadir `context_builder: ContextBuilder | None = None` al decorador `@agent` y a `Agent`.
- Si no se especifica, instanciar `DefaultContextBuilder()`.
- En el loop del agente, llamar a `context_builder.build(BuildInput(...))` en cada iteración antes de invocar al provider.

### En `phronesis/core/messages.py` (o similar)

- Si se opta por un bloque específico para resúmenes: añadir `CompactionSummaryBlock` a la lista de `ContentBlock`s.

---

## Principios para decisiones futuras

Cuando aparezcan decisiones nuevas durante la implementación:

1. **Si dudas entre "lógica en el builder" y "lógica en el agente", elige builder.** El agente debe permanecer ignorante de cómo se construye el contexto.
2. **Si dudas entre "estado en el builder" y "estado en el historial", elige historial.** El builder debe permanecer stateless.
3. **Si dudas entre "más builders del framework" y "Protocol extensible", elige Protocol.** El framework provee lo común; los casos específicos los hacen los usuarios.
4. **Si una optimización requiere statefulness, justifícala con caso real.** No introduzcas estado especulativo.
