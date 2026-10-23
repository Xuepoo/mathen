# Final reviewed relation graph report

## Scope and interpretation

This report covers the current `172` reviewed Architecture Cards under `data/systems/`. It distinguishes typed evidence-backed relations from legacy navigation metadata and from the separate mathematical-model projection. It does not add edges merely to remove isolated nodes.

A typed relation is directional and remains `proposed` until deliberate review accepts it. Its evidence IDs must be local to the source card. A legacy `related` edge is navigation context and carries no typed claim. A model-neighborhood edge groups explicitly named mathematical views; it is not a dependency or equivalence claim.

## Inventory

- Systems: **172**
- Features: **661**
- Mathematical views: **481**
- Typed relations: **45** (`uses`: 30, `composes`: 4, `resembles`: 11)
- Valid legacy related edges: **262**
- Combined directed edges: **307**

## Connectivity

- Combined undirected components: **27**: one of size 140, six of size 2, and 20 singletons.
- Largest component: **140** nodes.
- Isolated nodes: **20**.

The remaining isolates have no recorded connection in this projection; some still need relation review. A card can be valuable without a supported cross-system edge; shared words such as “runtime”, “pipeline”, “storage”, “window”, or “protocol” are not relation evidence.

### Remaining isolates

`alacritty`, `bazel`, `blender`, `cassandra`, `flutter`, `foundationdb`, `haproxy`, `imagemagick`, `javafx`, `just`, `kitty`, `leveldb`, `lsp`, `mongodb`, `oauth2-proxy`, `pulsar`, `qt`, `traefik`, `wezterm`, `wxwidgets`

### Non-singleton components outside the largest

- `authentik`, `keycloak`
- `dovecot`, `postfix`
- `ghostty`, `gtk`
- `jq`, `yq`
- `minio`, `seaweedfs`
- `openbao`, `vault`

## Mathematical model neighborhood

The `/api/graph/models` projection currently exposes **172 system nodes**, **242 model nodes**, and **468 `modeled-by` links** from reviewed mathematical views. It is a bipartite navigational graph. The model hubs preserve each view’s model name, question, assumptions, claim type, and source-local evidence IDs. Shared placement in a hub indicates matching model-title wording; it does not establish common implementation, a shared law, formal proof, historical influence, or composition compatibility.

A view may belong to multiple navigation families. All **481** distinct view keys are retained. Keys derive from the source system, normalized model title, and question, so reseeding database row IDs does not change them; changing those identity fields does. Aggregate edges retain a shared claim type or report `mixed` when their views differ. Each view's own claim type remains available.

The frontend exposes this projection through the `Systems / Math models` toggle. The system graph remains the evidence-backed software relation graph.

### Reading shapes and apparent isolation

The full model graph has no degree-zero nodes, but includes **232 degree-one model leaves** and 12 connected components. Many leaves represent a view title with no shared family match, not an unconnected software system. Domain filters can remove a system's neighbors; use Expand 1 hop to reveal actual connections outside the selected group. Hidden nodes remain hidden until restored.

Stars indicate high-degree hubs; chains connect hubs through a small number of systems; separate islands are disconnected components in the current projection. Position, edge length, angle, and cluster shape are force-layout geometry rather than measured architectural similarity or dependency depth. A 3D graph must have non-coplanar coordinates: an edge-on flat line was a layout initialization defect, not an architectural property.

The isolate reviews added ten proposed edges: Ghostty to GTK; Hyprland, niri, and Sway to Wayland; Celery to RabbitMQ and Redis; Postfix to Dovecot; webpack to Node.js; ast-grep to Tree-sitter; and React Native to React. Celery transports and Postfix's Dovecot SASL provider are configurable options, not universal dependencies. The MTH-0089 review retained React Native → Three.js and MinIO → SeaweedFS as legacy navigation only, and left the remaining isolates unchanged where source-local evidence did not establish a safe typed relation. Remaining isolates need more precise source-backed relation review rather than automatic similarity links.

## Review priorities

1. Review the remaining isolates only through primary source evidence and precise relation boundaries.
2. Deepen cards through the nine-dimensional coverage protocol: domains/components, state, interfaces/dependencies, consistency/ordering, security, failure/recovery, resources/scale, evolution/compatibility, and transferable patterns.
3. Add quantitative reliability, cost, temporal, algebraic, and distributed-time views only when evidence and assumptions support them.
4. Keep protocol specifications, protocol implementations, product integrations, and mathematical navigation hubs as distinct layers.

## Reproducible metric command

```bash
uv run mathen validate
just check
```

The graph counts above can be recomputed from canonical JSON by resolving typed relation targets and valid `related_systems` targets, then finding undirected connected components. Draft cards are not included.
