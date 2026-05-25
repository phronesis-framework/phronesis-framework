# Providers — Decisiones de Diseño y Plan de Implementación

> Documento completo del componente **Providers** del framework Phronesis. Recoge las decisiones cerradas, su motivación, y el plan de implementación con alcance, estructura y orden recomendado.

---

## Propósito del componente

Un Provider es la capa de adaptación a un LLM concreto (Anthropic, OpenAI, Google Gemini, etc.). Es lo que un agente usa por debajo para enviar mensajes al modelo, recibir respuestas, y orquestar tool calling.

Lo que un Provider tiene que resolver, conceptualmente:

1. **Llamada al modelo** — mandar mensajes, recibir respuesta.
2. **Tool calling** — traducir `ToolSpec`s al formato del provider y traducir las invocaciones de vuelta.
3. **Streaming** — recibir la respuesta en chunks en lugar de bloque completo.
4. **Capabilities específicas** — features propias de cada proveedor expuestas sin esconderlas.
5. **Configuración** — credenciales, base URL, timeouts.
6. **Errores específicos del provider** — traducción a errores comunes del framework.

### Filosofía

El error que **NO queremos cometer** es el patrón LangChain: abstracciones que prometen unicidad pero se rompen al usar features reales de cada proveedor.

La filosofía contraria, que es la que aplicamos:

- **Núcleo común mínimo**: solo lo que de verdad es universal.
- **Acceso a lo específico**: cada provider expone sus capacidades propias sin esconderlas.
- **Switch de provider transparente cuando es posible, explícito cuando no.**

---

## Índice de decisiones

1. [Forma de declarar/usar un provider](#d-01)
2. [Interfaz común mínima](#d-02)
3. [Acceso a features específicas de cada provider](#d-03)
4. [Reutilización interna por composición](#d-04)
5. [Streaming](#d-05)
6. [Structured output](#d-06)
7. [Forma de los tipos de mensajes (Request/Response)](#d-07)
8. [Forma de los chunks de streaming](#d-08)
9. [Forma de `supports()`](#d-09)
10. [Reporte de tokens y coste](#d-10)
11. [Jerarquía de errores del provider](#d-11)
12. [Retry/backoff integrado en providers](#d-12)

---

<a id="d-01"></a>
## D-01. Forma de declarar/usar un provider

**Decisión:** Función factory por cada provider built-in. Sin exponer clases internas. `Protocol LLMProvider` documentado para providers custom.

```python
model = anthropic("claude-opus-4-7", temperature=0.2)
model = openai("gpt-5", reasoning_effort="high")
```

**Alternativas consideradas:**

- Clases públicas (`AnthropicProvider("...")`).
- String identificadores (`model="anthropic:claude-opus-4-7"`).
- Híbrido (function factory + clases públicas + custom_provider wrapper).

**Razón principal:**

- Ergonomía y tipado a la vez: el IDE autocompleta parámetros, el type checker valida.
- Permite features específicas por provider sin contaminar la interfaz común.
- Esconde implementación interna — refactorizar la clase subyacente no rompe la API.
- Es el patrón validado por pydantic-ai y por los SDKs oficiales.

Las clases internas (`AnthropicProvider`, etc.) **no se exponen** como API pública. Para custom providers, el usuario implementa el `Protocol LLMProvider` desde cero (composición), no hereda de la clase interna.

### Provider custom (caso avanzado)

```python
from phronesis.providers import LLMProvider  # Protocol documentado

class MyInternalLLM:
    """Implementa LLMProvider sin heredar de nada."""

    async def complete(self, request): ...
    async def stream(self, request): ...
    def supports(self, feature): ...

researcher = Agent("researcher", model=MyInternalLLM(...), ...)
```

### Wrapper sobre provider existente

```python
class LoggingProvider:
    def __init__(self, inner: LLMProvider, logger):
        self.inner = inner
        self.logger = logger

    async def complete(self, request):
        self.logger.info(...)
        return await self.inner.complete(request)

    async def stream(self, request):
        async for chunk in self.inner.stream(request):
            yield chunk

    def supports(self, feature):
        return self.inner.supports(feature)

researcher = Agent("researcher", model=LoggingProvider(anthropic("..."), logger), ...)
```

Composición pura. El wrapper cumple el protocolo, el agente no distingue.

---

<a id="d-02"></a>
## D-02. Interfaz común mínima

**Decisión:** Protocolo **realista** que incluye tool calling como ciudadano de primera. Métodos:

- `complete(request) → response` — llamada síncrona, devuelve respuesta completa.
- `stream(request) → AsyncIterator[chunk]` — streaming.
- Tool calling **integrado** en el request/response (mensajes con tool_use blocks, tool_result blocks).
- `supports(feature) → bool` — capabilities introspection para features opcionales.

**Alternativas consideradas:**

- Protocolo minimalista (solo `complete()`, todo lo demás como extensiones opcionales).
- Protocolo rico (estilo LangChain, con muchos métodos especializados).

**Razón principal:**

- Phronesis es un framework de **agentes**. Tool calling no es opcional; es la razón de existir.
- Streaming es estándar en todos los proveedores serios.
- Features genuinamente opcionales (vision, prompt caching, structured output nativo, etc.) van por `supports()`.
- Embeddings y conteo de tokens se excluyen deliberadamente — son servicios distintos al de generación. Si se necesitan, otro protocolo separado.

### Features cubiertas por `supports()`

Lista no cerrada, crece según aparecen:

- `structured_output` — output estructurado nativo.
- `prompt_caching` — caching del prompt.
- `vision` — input de imágenes.
- `documents` — input de documentos.
- `extended_thinking` — modo de razonamiento extendido.
- `reasoning_effort` — control de esfuerzo de razonamiento.
- `predicted_outputs` — predicción de salida.

---

<a id="d-03"></a>
## D-03. Acceso a features específicas de cada provider

**Decisión:** Features específicas como **parámetros tipados** en la factory de cada provider.

```python
model = anthropic(
    "claude-opus-4-7",
    temperature=0.2,
    max_tokens=4096,
    prompt_caching=True,        # específico Anthropic
    extended_thinking=True,     # específico Anthropic
)

model = openai(
    "gpt-5",
    temperature=0.2,
    reasoning_effort="high",    # específico OpenAI
    predicted_output="...",     # específico OpenAI
)
```

**Alternativas consideradas:**

- Atributo `.native` para acceso al cliente subyacente.
- Diccionario de "extras" sin tipar.

**Razón principal:**

- Tipado real: IDE autocompleta, type checker valida.
- Descubrible: el usuario escribe `anthropic(` + Tab y ve los parámetros válidos.
- Honesto: cada factory expone lo suyo. Lo específico se ve como específico.
- Errores tempranos: si el provider deprecia una feature, el type check lo señala.
- Encaja con el principio "no escondas lo específico".

El coste (cada factory crece al añadir features nuevas) es **trabajo que paga el framework una vez**, no el usuario muchas veces. Es la división de trabajo correcta.

---

<a id="d-04"></a>
## D-04. Reutilización interna por composición

**Decisión:** Sin herencia (ni simple ni múltiple) entre providers. Reutilización vía:

- Funciones puras en módulos `_common/`.
- Clases utilitarias compuestas (`HttpClient`, `TokenCounter`, `StreamingDecoder`, etc.).
- Funciones de orden superior y decoradores para cross-cutting concerns.
- Protocols internos pequeños cuando hay piezas intercambiables.

**Alternativas consideradas:**

- Herencia simple con `BaseProvider`.
- Herencia múltiple con mixins (`BaseHTTPProvider`, `BaseToolCalling`, etc.).

**Razón principal:**

- Herencia múltiple en Python genera problemas reales (MRO impredecible, diamond problem, frágil al refactor).
- La comunidad Python moderna evita mixins via herencia múltiple por las lecciones aprendidas (Django).
- Composición permite que cada pieza sea independiente, sustituible y testeable.
- Encaja con `Protocol LLMProvider` (duck typing estructural): herencia interna confundiría el modelo.

Cada provider concreto (`AnthropicProvider`, `OpenAIProvider`, etc.) acaba con ~200-400 líneas de código específico tras factorizar utilidades comunes. La mayor parte del código duplicable vive fuera, en utilidades compartidas.

### Estructura interna típica de un provider

```python
class AnthropicProvider:
    def __init__(self, model: str, **kwargs):
        self._http = HttpClient(base_url="https://api.anthropic.com", ...)
        self._messages = AnthropicMessageBuilder()
        self._tools = AnthropicToolFormatter()
        # cada pieza independiente, compuesta no heredada
```

---

<a id="d-05"></a>
## D-05. Streaming

**Decisión:** Streaming SÍ en el MVP, vía **método separado** `agent.stream(...)`. Alcance acotado.

```python
async for chunk in agent.stream("Explain phronesis"):
    print(chunk.text, end="", flush=True)
```

`agent.run(...)` sigue existiendo para el caso no-streaming.

**Alternativas consideradas:**

- Diferir streaming completo al post-MVP.
- Un solo método con parámetro `stream=True`.

**Razón principal:**

- Streaming es expectativa básica en UIs modernas. Sin él, Phronesis queda fuera de juego para aplicaciones interactivas.
- Método separado es el patrón validado (SDKs oficiales, pydantic-ai).
- Un solo método con parámetro genera problemas de tipos (overloads con `Literal`) feos y frágiles.
- Internamente, `run()` puede implementarse consumiendo el stream y agregando — evita drift.

### Alcance acotado del MVP

Incluido:

- Chunks de texto.
- Eventos básicos: `tool_call_start`, `tool_call_end`, `tool_result`.

Diferido al post-MVP:

- Streaming de tool arguments token a token.
- Streaming de structured output.
- Cancelación granular dentro del stream.

---

<a id="d-06"></a>
## D-06. Structured output

**Decisión:** Declarado en el **agente** (`output_type=...`). Internamente, el agente comprueba `provider.supports("structured_output")`. Si sí, delega al provider (ruta nativa). Si no, emula con tool calling forzado.

```python
class Classification(BaseModel):
    category: Literal["billing", "technical", "general"]
    confidence: float
    reasoning: str

classifier = Agent(
    "classifier",
    model=anthropic("claude-opus-4-7"),
    output_type=Classification,
)

result = await classifier.run("...")
# result.output es Classification
```

**Alternativas consideradas:**

- Solo en el provider (request lleva `output_schema`).
- Solo en el agente (sin aprovechar features nativas).

**Razón principal:**

- Responsabilidad clara: el provider transporta mensajes; el agente decide qué tipo de output quiere.
- API limpia: el usuario declara `output_type` una vez al construir el agente.
- Funciona con cualquier provider — los que tienen soporte nativo se aprovechan; los que no, se emulan.
- El agente puede orquestar lógica adicional (retry con feedback, validación post-parse) que el provider no puede.

### Comportamiento detallado

1. Al construir el `AgentSpec`, se valida que `output_type` es un tipo válido (modelo Pydantic, dataclass, etc.).
2. En `agent.run()`, el agente comprueba `provider.supports("structured_output")`.
3. Si **sí**: construye el request con el schema del `output_type` y delega al provider. El provider devuelve respuesta ya estructurada.
4. Si **no**: el agente inyecta una "tool sintética" `return_result(output: OutputType)` y fuerza al modelo a invocarla. Captura la invocación, valida el output, y la devuelve.
5. En ambos casos, `result.output` es una instancia del tipo declarado.

---

<a id="d-07"></a>
## D-07. Forma de los tipos de mensajes (Request/Response)

**Decisión:** `dataclasses` con `frozen=True` y `slots=True` para todos los tipos que viajan por el protocolo (`LLMRequest`, `LLMResponse`, `Message`, `ToolCall`, `ToolResult`, etc.). Mismo estilo que `phronesis.tools`.

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class LLMRequest:
    model: str
    messages: tuple[Message, ...]
    tools: tuple[ToolSpec, ...] = ()
    temperature: float | None = None
    max_tokens: int | None = None
```

**Alternativas consideradas:**

- Modelos Pydantic v2 (validación automática, schema generation).
- `TypedDict` (sin overhead, sin runtime check).
- `NamedTuple` (inmutable, ligero, sin defaults convenientes).

**Razón principal:**

- Coherencia con el resto del framework: `phronesis.tools` ya usa dataclasses para `ToolSpec`. Mantener un solo estilo reduce carga cognitiva.
- `frozen=True` garantiza inmutabilidad — los requests viajan por capas (agente → middleware → provider) sin riesgo de mutación.
- `slots=True` reduce footprint de memoria y previene typos al asignar atributos inexistentes.
- Pydantic es excelente para entrada externa (JSON del LLM), pero los tipos internos no necesitan validación en cada paso.
- Schema/serialización se hace en los puntos exactos donde se necesita (boundary con la API HTTP), no como ceremonia constante.

---

<a id="d-08"></a>
## D-08. Forma de los chunks de streaming

**Decisión:** Jerarquía sellada de dataclasses bajo un union explícito `LLMChunk`. Cada subtipo modela un evento concreto del stream.

```python
@dataclass(frozen=True, slots=True)
class TextChunk:
    text: str

@dataclass(frozen=True, slots=True)
class ToolCallStart:
    call_id: str
    tool_name: str

@dataclass(frozen=True, slots=True)
class ToolCallEnd:
    call_id: str
    arguments: dict[str, Any]

@dataclass(frozen=True, slots=True)
class ToolResult:
    call_id: str
    output: Any

@dataclass(frozen=True, slots=True)
class Finish:
    reason: str
    usage: TokenUsage | None = None

LLMChunk = TextChunk | ToolCallStart | ToolCallEnd | ToolResult | Finish
```

**Alternativas consideradas:**

- Un único dataclass `LLMChunk` con `kind: Literal[...]` y campos opcionales.
- Eventos como diccionarios sin tipar (`dict[str, Any]`).
- Clases con herencia común (`class TextChunk(LLMChunk):`).

**Razón principal:**

- `match`/`isinstance` exhaustivo: el consumidor sabe exactamente qué eventos puede recibir y el type checker valida los `match`.
- Cada subtipo solo tiene los campos que aplican — sin `None`s espurios.
- Union sellado en lugar de herencia: composición sobre herencia (coherente con D-04).
- Inmutabilidad y bajo overhead — los streams emiten muchos eventos, conviene que sean baratos.

---

<a id="d-09"></a>
## D-09. Forma de `supports()`

**Decisión:** `Enum` cerrado `ProviderFeature` y firma `supports(feature: ProviderFeature) -> bool`.

```python
from enum import Enum

class ProviderFeature(str, Enum):
    STRUCTURED_OUTPUT = "structured_output"
    PROMPT_CACHING = "prompt_caching"
    VISION = "vision"
    DOCUMENTS = "documents"
    EXTENDED_THINKING = "extended_thinking"
    REASONING_EFFORT = "reasoning_effort"
    PREDICTED_OUTPUTS = "predicted_outputs"

provider.supports(ProviderFeature.STRUCTURED_OUTPUT)  # -> bool
```

**Alternativas consideradas:**

- `supports(name: str) -> bool` con strings libres.
- `supports() -> set[str]` (devuelve el conjunto completo).
- `set[ProviderFeature]` expuesto como atributo (`provider.features`).

**Razón principal:**

- Cerrado: añadir una feature nueva requiere actualizar el enum — fuerza coordinación explícita entre providers.
- Tipado: el IDE autocompleta los miembros, el type checker rechaza strings inválidos.
- Heredar de `str` permite usarlo como clave en dicts y comparar con strings cuando hace falta.
- Compatible con `Literal` si en algún momento conviene tiparlo en signatures.

---

<a id="d-10"></a>
## D-10. Reporte de tokens y coste

**Decisión:** `TokenUsage` dataclass con tokens de input, output y caching. **Sin** cálculo de coste — Phronesis no es un sistema de billing.

```python
@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_creation_tokens: int | None = None
```

`LLMResponse.usage` es opcional (`TokenUsage | None`). El chunk `Finish` lo expone también para streaming.

**Alternativas consideradas:**

- Incluir `cost_usd` calculado por el framework con tabla de precios.
- Diccionario libre `dict[str, int]` por flexibilidad.
- Solo `input_tokens` y `output_tokens`, ignorar caching.

**Razón principal:**

- Los tokens son el dato bruto que cada API expone; el framework lo transporta sin opinar.
- El coste depende de tabla de precios, tier, región — mantener esa tabla actualizada es responsabilidad del usuario o de un helper opt-in, no del core.
- Caching es relevante para Anthropic (prompt caching) y OpenAI (cached input); merece campos propios.
- Campos `None`-by-default permiten que un provider que no expone alguna métrica simplemente la deje fuera.

---

<a id="d-11"></a>
## D-11. Jerarquía de errores del provider

**Decisión:** Jerarquía bajo `ProviderError` con subclases por tipo de fallo.

```python
class ProviderError(Exception):
    """Base de todos los errores de un provider."""

class TransportError(ProviderError):
    """Fallo de red, timeout, conexión cerrada."""

class AuthenticationError(ProviderError):
    """Credencial inválida o ausente."""

class RateLimitError(ProviderError):
    """429 / cuota agotada. Lleva retry_after_seconds cuando se conoce."""
    retry_after_seconds: float | None

class ContextWindowExceededError(ProviderError):
    """El input excede la ventana del modelo."""

class ServerError(ProviderError):
    """5xx del provider."""

class BadRequestError(ProviderError):
    """4xx no cubiertos arriba — request mal formado, parámetros inválidos."""

class StreamError(ProviderError):
    """Fallo durante el streaming (conexión cortada, evento malformado)."""
```

**Alternativas consideradas:**

- Un único `ProviderError` con campo `kind`.
- Re-exportar los errores del SDK subyacente (cada provider expone sus propias clases).
- Solo `ProviderError` + `RateLimitError`, todo lo demás "lo que sea" genérico.

**Razón principal:**

- El usuario quiere poder `except RateLimitError:` específicamente sin parsear strings.
- `RateLimitError.retry_after_seconds` encaja directamente con el `delay_hook` de `@retry` (`docs/internal/retry/`).
- Hierarquía pequeña pero suficiente — cubre los casos accionables sin proliferación de tipos.
- No re-exportamos errores del SDK del provider: aislamos al usuario del cambio del SDK.

---

<a id="d-12"></a>
## D-12. Retry/backoff integrado en providers

**Decisión:** Integrar `@retry` de `phronesis._internal.retry` sobre las operaciones de red de cada provider. Configurable por la factory.

```python
def anthropic(
    model: str,
    *,
    retry: RetryConfig | None = None,  # None -> defaults sensatos
    **kwargs,
) -> AnthropicProvider:
    ...
```

Por defecto: reintentar `TransportError`, `RateLimitError` y `ServerError`. No reintentar `AuthenticationError`, `BadRequestError`, `ContextWindowExceededError`. Honrar `retry_after_seconds` cuando el error lo provee.

**Alternativas consideradas:**

- Reintentar fuera del provider (responsabilidad del agente o del usuario).
- Reintentar dentro del SDK del provider (cada SDK trae el suyo, dejarlo así).
- Sin retry en MVP, añadirlo después.

**Razón principal:**

- Ya existe `@retry` con jitter, backoff exponencial, `delay_hook` y `should_retry`. Reusarlo evita duplicar la lógica.
- El provider conoce qué errores son reintentables (semántica HTTP del SDK específico). El agente no debería saberlo.
- Configurable por factory: el usuario puede pasar `retry=RetryConfig(max_attempts=5, ...)` o desactivarlo con `retry=None` explícito si quiere control externo.
- `retry_after_seconds` del `RateLimitError` (D-11) se enlaza con el `delay_hook` automáticamente.

---

## Principios transversales

Aplicables a todo el componente Providers:

1. **Núcleo común mínimo, acceso a lo específico.** El protocolo común cubre lo universal; las features propias se exponen sin esconderse.

2. **Composición sobre herencia.** Sin clases base compartidas; piezas independientes que se componen.

3. **Tipado real y descubrible.** Cada factory expone sus parámetros tipados. El IDE autocompleta, el type checker valida.

4. **Portabilidad como valor.** Cambiar de provider debe ser sustituir una factory; el resto del código no debería cambiar (salvo features genuinamente específicas).

5. **Sin escondrijos.** Lo que es específico se ve como específico. No mentimos sobre uniformidad.

6. **Honestidad sobre capabilities.** `supports()` permite que el framework y el usuario sepan qué hay disponible. Sin features mágicas que funcionan a medias.

---

## Plan de implementación

### Orden recomendado

1. **Protocol `LLMProvider`** — el contrato común. Sin implementación todavía, solo la definición.
2. **Tipos compartidos** — `LLMRequest`, `LLMResponse`, `LLMChunk`, `ToolCall`, `ToolResult`, etc. Los datos que viajan por el protocolo.
3. **Excepciones de provider** — `ProviderError`, `RateLimitError`, `ContextWindowExceededError`, etc.
4. **Utilidades en `_common/`** — primero las que sepamos que se reusan (`MessageConverter`, `ToolFormatter`).
5. **Anthropic** — primer provider real. Es el más documentado y completo en features, buen punto de partida.
6. **OpenAI** — segundo. Aquí ya empezamos a ver el patrón y a extraer más utilidades comunes al `_common/` si emergen.
7. **Tests de integración** — con mocks de respuestas reales de cada API.

### Por qué Anthropic primero

- API documentada con muy alta calidad.
- Tool calling integrado de forma natural en el formato de mensajes.
- Streaming bien documentado.
- Features avanzadas (prompt caching, extended thinking) bien definidas.
- Buen punto de partida para que el segundo provider (OpenAI) revele qué patrones son genuinamente comunes.

### Estructura de archivos

```
phronesis/providers/
├── __init__.py            # API pública: anthropic, openai, LLMProvider, etc.
├── protocol.py            # Protocol LLMProvider
├── types.py               # LLMRequest, LLMResponse, LLMChunk, etc.
├── errors.py              # ProviderError y subclases
├── _common/               # utilidades compartidas internas
│   ├── __init__.py
│   ├── messages.py        # conversores genéricos de mensajes
│   ├── tools.py           # formatters genéricos de tools
│   └── streaming.py       # decoders SSE comunes
├── anthropic/
│   ├── __init__.py
│   ├── provider.py        # implementación AnthropicProvider
│   ├── factory.py         # función anthropic(...)
│   ├── messages.py        # conversión específica de mensajes
│   ├── tools.py           # formato específico de tools
│   └── errors.py          # mapeo de errores específicos
└── openai/
    ├── ... (mismo patrón)
```

---

## Decisiones pendientes (a tomar al implementar)

Las decisiones que originalmente quedaban abiertas se cerraron antes de empezar la implementación: **forma de los mensajes (D-07)**, **forma de los chunks (D-08)**, **forma de `supports()` (D-09)**, **reporte de tokens (D-10)**, **jerarquía de errores (D-11)** y **retry/backoff (D-12)**.

Las decisiones que sigan apareciendo durante la implementación se documentarán como `D-NN` adicionales en este mismo fichero.

---

## Lo que queda fuera del alcance inicial

Decisiones diferidas conscientemente:

- **Provider para modelos locales** (vLLM, llama.cpp, Ollama). MVP empieza con APIs comerciales.
- **Routing entre providers** (fallback automático si uno falla).
- **Caching propio del framework** por encima de los providers.
- **Embeddings.** Protocolo distinto (`EmbeddingProvider`) si se necesita en el futuro.
- **Conteo de tokens propio.** Cada provider lo expone como puede; si en algún momento hace falta unificarlo, se diseña entonces.
- **Multi-model dentro de un mismo provider** (ej. switch dinámico entre Claude Sonnet y Opus en runtime). Cada factory devuelve un provider para un modelo concreto.

---

## Definición de hecho

El componente Providers está listo cuando:

- `Protocol LLMProvider` definido y documentado.
- Tipos compartidos (`LLMRequest`, `LLMResponse`, etc.) implementados y tipados.
- Jerarquía de excepciones implementada.
- Provider Anthropic implementado con: complete, stream, tool calling, manejo de errores, soporte de `prompt_caching` y al menos otra feature específica.
- Provider OpenAI implementado con: complete, stream, tool calling, manejo de errores, soporte de al menos `reasoning_effort` o `predicted_outputs`.
- Tests de cada provider con mocks de respuestas reales.
- Tests de portabilidad: una tool definida una vez, ejecutada con ambos providers, mismo resultado funcional.
- `__all__` explícito en cada `__init__.py`.
- Docstrings completos en API pública.

---

## Principios que guían las decisiones que aparecerán

Cuando surjan decisiones nuevas durante la implementación que este documento no cubre, los principios que las guían:

1. **Cuando dudes entre "núcleo común" y "específico del provider", elige específico.** Es más honesto y se equivoca menos.
2. **Cuando dudes entre "feature en el protocolo" y "feature opcional vía `supports()`", elige opcional.** Mantiene el protocolo pequeño.
3. **Cuando dudes entre "abstracción genérica" y "código específico del provider", elige específico.** La abstracción se extrae cuando se ve el patrón real (regla de tres).
4. **Cuando dudes entre "ocultar" y "exponer" una decisión de implementación, expón.** La transparencia es valor.
5. **Cuando dudes entre "más infraestructura" y "más simple", elige simple.** El coste de complejidad lo paga el mantenedor; el coste de simplicidad lo paga nadie.
