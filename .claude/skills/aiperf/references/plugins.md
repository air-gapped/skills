# Plugin System

AIPerf is a plugin host. Every endpoint, dataset loader, exporter, accuracy grader, plot type, timing strategy, etc. is registered via a YAML manifest and resolved through a singleton registry. Custom plugins ship in a separate Python package, no AIPerf-source modifications required.

## 25 plugin categories

| Group | Categories |
|---|---|
| Timing | `timing_strategy`, `arrival_pattern`, `ramp` |
| Datasets | `dataset_backing_store`, `dataset_client_store`, `dataset_sampler`, `dataset_composer`, `custom_dataset_loader`, `public_dataset_loader` (v0.7.0+) |
| Endpoints / transport | `endpoint`, `transport` |
| Processing | `record_processor`, `results_processor`, `data_exporter`, `console_exporter` |
| Accuracy | `accuracy_benchmark`, `accuracy_grader` |
| UI / selection | `ui`, `url_selection_strategy` |
| Service | `service`, `service_manager` |
| Visualization / telemetry | `plot`, `gpu_telemetry_collector` |
| Internal infra | `communication`, `communication_client`, `zmq_proxy` |

`aiperf plugins --all` lists what's installed. Each category has a typed enum (e.g. `EndpointType`, `CustomDatasetType`) generated dynamically from the registry — IDE autocomplete works.

## Registry usage

```python
from aiperf.plugin import plugins
from aiperf.plugin.enums import PluginType, EndpointType

ChatEndpoint = plugins.get_class(PluginType.ENDPOINT, "chat")
ChatEndpoint = plugins.get_class(PluginType.ENDPOINT, EndpointType.CHAT)
ChatEndpoint = plugins.get_class(PluginType.ENDPOINT, "aiperf.endpoints.openai_chat:ChatEndpoint")

for entry, cls in plugins.iter_all(PluginType.ENDPOINT):
    print(entry.name, "→", entry.class_path, entry.description)

meta = plugins.get_metadata("endpoint", "chat")               # raw dict
ep_meta = plugins.get_endpoint_metadata("chat")               # typed Pydantic
```

## Authoring a custom plugin (4-step recipe)

If contributing **directly to AIPerf**, only steps 1 + 2 apply (add the class under `src/aiperf/`, register in `src/aiperf/plugin/plugins.yaml`).

### 1. The class

Subclass the protocol's base class. Endpoints extend `BaseEndpoint`; dataset loaders extend `BaseDatasetLoader`; exporters extend `BaseExporter`; etc.

**Pick the most-specific endpoint base class.** AIPerf ships category-specific bases that already implement the boilerplate:

| Base class | Use for | What it provides |
|---|---|---|
| `BaseEndpoint` | Truly novel APIs that don't fit a category | The two abstract methods: `format_payload(request_info) -> dict` and `parse_response(response) -> ParsedResponse \| None` |
| `BaseRankingsEndpoint` | Rerank / passage-scoring services | Pre-implements `format_payload` + `parse_response`; subclass overrides `build_payload(query_text, passages, model_name)` and `extract_rankings(json_obj) -> list[dict]` (returns objects with `index` and `score` keys). Handles `--extra-inputs` merging, turn validation, and wrapping into `RankingsResponseData` |
| `BaseEmbeddingsEndpoint` | Vector-embedding services | Pre-implements payload/response with subclass hooks for the wire format |
| `OpenAIChatEndpoint`, `OpenAICompletionsEndpoint`, etc. | Variants of OpenAI APIs | Inherit and override only what differs |

For rerank in particular: a `BaseRankingsEndpoint` subclass is ~10 lines of code; a `BaseEndpoint` subclass is ~50. Start at the most-specific base.

```python
# my_package/endpoints/custom_endpoint.py
from aiperf.endpoints.base_endpoint import BaseEndpoint
from aiperf.common.models import RequestInfo, InferenceServerResponse, ParsedResponse, TextResponseData

class MyCustomEndpoint(BaseEndpoint):
    def format_payload(self, request_info: RequestInfo) -> dict:
        turn = request_info.turns[-1]
        texts = [c for t in turn.texts for c in t.contents if c]
        return {"prompt": texts[0] if texts else ""}

    def parse_response(self, response: InferenceServerResponse) -> ParsedResponse | None:
        if json_obj := response.get_json():
            return ParsedResponse(perf_ns=response.perf_ns,
                                  data=TextResponseData(text=json_obj.get("text", "")))
        return None
```

### 2. `plugins.yaml`

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/ai-dynamo/aiperf/refs/heads/main/src/aiperf/plugin/schema/plugins.schema.json
schema_version: "1.0"
endpoint:
  my_custom:
    class: my_package.endpoints.custom_endpoint:MyCustomEndpoint
    description: Custom endpoint for my API.
    priority: 0
    metadata:
      endpoint_path: /v1/generate
      supports_streaming: true
      produces_tokens: true
      tokenizes_input: true
      metrics_title: My Custom Metrics
```

### 3. Entry point in `pyproject.toml`

```toml
[project.entry-points."aiperf.plugins"]
my-package = "my_package:plugins.yaml"
```

### 4. Install + verify

```bash
pip install -e .
aiperf plugins endpoint my_custom
aiperf plugins --validate
```

`aiperf profile --endpoint-type my_custom ...` now works.

## Metadata schemas

Pydantic models in `aiperf.plugin.schema.schemas`:

| Model | Key fields |
|---|---|
| `EndpointMetadata` | `endpoint_path`, `supports_streaming`, `produces_tokens`, `tokenizes_input`, `metrics_title`, plus optional streaming/service/multimodal/polling fields |
| `TransportMetadata` | `transport_type`, `url_schemes` |
| `PlotMetadata` | `display_name`, `category` |
| `ServiceMetadata` | `required`, `auto_start`, `disable_gc`, `replicable` |

## Conflict resolution

When two packages register a plugin under the same `<category>:<name>`:

1. Higher `priority:` wins.
2. External package beats built-in (equal priority).
3. First registered wins (a warning is logged).

Shadowed plugins remain accessible by full class path: `plugins.get_class("endpoint", "my_pkg.endpoints:MyEndpoint")`.

## Runtime / testing helpers

```python
plugins.register("endpoint", "test", TestEndpoint, priority=10)
plugins.reset_registry()                           # tests
errors = plugins.validate_all(check_class=True)    # {category: [(name, err), ...]}
name = plugins.find_registered_name(PluginType.ENDPOINT, ChatEndpoint)
pkg  = plugins.get_package_metadata("aiperf")      # version, author, …
```

Auto-generate enums for IDE help:

```bash
make generate-plugin-enums       # writes src/aiperf/plugin/enums.py
make generate-plugin-overloads   # type hints
```

## Common errors

| Error | Cause / fix |
|---|---|
| `TypeNotFoundError: Type 'X' not found for category 'Y'` | Not registered in `plugins.yaml`, or entry point missing in `pyproject.toml`, or package not installed. Run `aiperf plugins --validate`. |
| `ImportError: Failed to import module for endpoint:X` | Class path wrong (`module.path:ClassName`), missing dep, or module not importable. `python -c "import module.path"`. |
| `AttributeError: Class 'Y' not found` | Case-sensitive; class not exported from module. |
| Plugin shadowed | Bump `priority:` in the manifest, or call `plugins.get_class("endpoint", "my_pkg.x:Y")` directly. |

## Built-in plugin highlights

Endpoints: see `endpoints.md`.

Timing strategies: `fixed_schedule`, `request_rate`, `user_centric_rate`.

Arrival patterns: `constant`, `poisson`, `gamma`, `concurrency_burst`.

Dataset composers: `synthetic`, `custom`, `synthetic_rankings`.

UI types: `dashboard` (Rich terminal), `simple` (tqdm), `none` (headless).

Accuracy benchmarks: `mmlu`, `aime`, `aime24`, `aime25`, `hellaswag`, `bigbench`, `math_500`, `gpqa_diamond`, `lcb_codegeneration`.

Accuracy graders: `exact_match`, `math`, `multiple_choice`, `code_execution`.

GPU telemetry collectors: `dcgm` (Prometheus scrape), `pynvml` (direct query, no exporter).
