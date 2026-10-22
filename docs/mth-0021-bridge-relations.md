# MTH-0021 reviewed-card bridge relations

## Scope and decision rule

This report evaluates evidence-backed relations involving the reviewed
`firecracker`, `qemu`, `linux`, `kubernetes`, and `nginx` cards, then checks
the other reviewed cards for a similarly precise bridge. It does not modify
canonical cards. The question is whether an edge can be proposed using only
evidence IDs already present in the source and target cards.

The relation vocabulary is limited to `uses`, `extends`, `composes`,
`resembles`, and `influenced-by`. Relation claim type and review status remain
independent: structural comparisons use `analogy`, documented dependencies
use `fact`, and every candidate remains `proposed` because it is not being
added to a canonical card here. No historical influence is inferred from
shared implementation structure.

For each candidate, `source evidence` is evidence that exists in the source
card and could be stored on its relation. `target evidence` is listed as the
independent evidence for the other endpoint; it must not be copied into the
source card unless it already exists there.

## Justified candidates

| ID | Source → relation → target | Claim type / status | Source evidence | Target evidence | Boundary note |
| --- | --- | --- | --- | --- | --- |
| B1 | `firecracker` → `resembles` → `qemu` | `analogy` / `proposed` | `firecracker-design` | `qemu-system-emulation`, `qemu-kvm-source`, `qemu-qdev-source` | Both cards document a virtual-machine monitor boundary with guest-visible machine/device modeling and KVM-capable execution. Firecracker deliberately narrows the device model and lifecycle around one microVM, while QEMU supports a broad configurable machine and device composition and can select TCG or KVM. This is a structural comparison, not QEMU implementation reuse, equivalence, or historical influence. Use one directed orientation only; do not add a reverse duplicate. |
| B2 | `grpc` → `uses` → `protobuf` | `fact` / `proposed` | `grpc-core-concepts` | `protobuf-language-guide`, `protobuf-encoding` | The gRPC card explicitly documents Protocol Buffers as the default service and message description. The edge records the default interface/serialization path; it does not claim that every gRPC deployment uses Protobuf, that Protobuf requires gRPC, or that gRPC uses the whole Protobuf implementation. |

B1 is the direct Firecracker/QEMU bridge requested by this analysis. B2 is an
independent reviewed-card dependency with a stronger claim than resemblance.
Neither candidate should be represented as `extends` or `influenced-by`.

## Pairwise decisions for Firecracker, QEMU, Linux, Kubernetes, and NGINX

### Firecracker and QEMU

`B1` is justified as `resembles` only. Firecracker's
`firecracker-design` evidence supports its minimal machine model and KVM VMM
execution. QEMU's `qemu-system-emulation`, `qemu-kvm-source`, and
`qemu-qdev-source` evidence independently supports configurable machine/device
composition and accelerator selection. The shared abstraction is the VMM
boundary, not a shared codebase or a compatible base/derived implementation.

### Firecracker and Linux

No relation is justified. `firecracker-design` supports KVM-backed VMM
execution, but the Linux card's available evidence IDs
(`linux-vfs-doc`, `linux-scheduler-doc`, `linux-kbuild-doc`,
`linux-vfs-source`, `linux-scheduler-source`, `linux-module-source`, and
`linux-process-source`) do not establish a KVM subsystem or a Firecracker
integration boundary. Inferring `uses` from the general fact that KVM is a
host facility would exceed the reviewed evidence.

### Firecracker and Kubernetes

No relation is justified. `firecracker-design` describes a microVM boundary,
while Kubernetes evidence (`kubernetes-architecture-doc`,
`kubernetes-controller-doc`, `kubernetes-controller-source`,
`kubernetes-apiserver-source`, `kubernetes-etcd-source`, and
`kubernetes-scheduler-source`) describes declarative resources, reconciliation,
cluster storage, and scheduling. The Kubernetes card does not document
Firecracker as a runtime or a microVM integration, so `uses` and `composes`
would be unsupported. A generic “workload isolation” resemblance would not be
specific enough.

### Firecracker and NGINX

No relation is justified. `firecracker-design` and the NGINX evidence
(`nginx-development-doc`, `nginx-process-source`, `nginx-event-source`,
`nginx-cycle-source`, and `nginx-http-source`) describe unrelated VMM and
network-server boundaries. Shared words such as process, event, and resource
do not establish a typed relation.

### QEMU and Linux

No relation is justified. QEMU's `qemu-kvm-source` documents an accelerator
integration, but the reviewed Linux evidence does not document KVM. The
available Linux process, scheduler, VFS, and module evidence is insufficient to
record `qemu` `uses` `linux`; the host-OS association would be external to the
card evidence.

### QEMU and Kubernetes

No relation is justified. QEMU's machine composition and management boundary
(`qemu-system-emulation`, `qemu-qom-doc`, `qemu-vl-source`, `qemu-qdev-source`,
and `qemu-qmp-source`) does not establish Kubernetes integration. Kubernetes'
resource and controller evidence does not identify QEMU as a node runtime or
virtualization provider.

### QEMU and NGINX

No relation is justified. QEMU's evidence concerns machine/device composition
and QMP; NGINX's evidence concerns worker processes, readiness events,
configuration modules, and request memory lifetimes. The two eventful runtime
systems do not share a sufficiently specific reviewed boundary.

### Linux and Kubernetes

No relation is recorded. Linux's `linux-scheduler-doc` and
`linux-scheduler-source` concern selection of runnable tasks under kernel
scheduler policy. Kubernetes' `kubernetes-architecture-doc` and
`kubernetes-scheduler-source` concern placement of pending workloads onto
cluster nodes. Both contain a scheduling decision, but the execution domains,
state, and guarantees differ; a generic scheduler resemblance would not add a
useful bridge without a more explicit cross-system abstraction.

### Linux and NGINX

No relation is recorded. NGINX's `nginx-development-doc` and
`nginx-event-source` mention platform-specific notification modules including
`epoll`, `kqueue`, and `select`, but do not establish a Linux-specific
dependency in the reviewed card. Linux's available evidence does not cover
the NGINX event integration. Do not infer `uses` from NGINX commonly running
on Linux.

### Kubernetes and NGINX

No relation is justified. Kubernetes' API, controller, storage, and scheduler
evidence does not identify NGINX as a managed workload or ingress component;
NGINX's card does not identify Kubernetes. Their independently useful
configuration/module and reconciliation graphs are not a documented
composition.

## Other reviewed-card checks

The following edges were checked because the reviewed cards expose explicit
component boundaries:

| Pair or direction | Decision | Evidence boundary |
| --- | --- | --- |
| `grpc` → `protobuf` | **B2 justified** | `grpc-core-concepts` explicitly says Protocol Buffers are the default service and message description; target semantics are covered by `protobuf-language-guide` and `protobuf-encoding`. |
| `rust` → `llvm` | No relation yet | `rustc-overview` identifies LLVM IR in the compiler representation sequence, but that does not by itself establish use of the LLVM project as an implementation dependency. Do not turn an intermediate representation name into `uses`. |
| `kubernetes` → `etcd` | No relation possible in this review | `kubernetes-architecture-doc`, `kubernetes-etcd-source`, and `kubernetes-apiserver-source` support an etcd-backed state boundary, but there is no reviewed `etcd` card target. Do not create a relation to an unreviewed node. |
| `qemu` → `kvm` | No relation possible in this review | `qemu-system-emulation` and `qemu-kvm-source` support accelerator selection, but there is no reviewed `kvm` card target. `qemu` → `linux` is not a substitute. |
| `elasticsearch` → `lucene` | No relation possible in this review | `elasticsearch-cluster-shards` and `elasticsearch-merge` support Lucene-backed shard structure, but there is no reviewed `lucene` card target. |
| `wasmtime` ↔ `firecracker` | No relation recorded | `wasmtime-architecture` describes Store-scoped runtime ownership; `firecracker-design` describes VM isolation. The analogy would conflate runtime state separation with hardware virtualization isolation. |

Existing reviewed relations remain valid in their current cards, including
the database analogies and `supabase` `composes` `postgresql`. This report does
not duplicate or alter them.

## Conclusion

Two precise proposed bridges are supported by the current reviewed evidence:

1. `firecracker` `resembles` `qemu` (`analogy`, `proposed`) through the
   documented VMM, machine/device, and KVM execution boundary.
2. `grpc` `uses` `protobuf` (`fact`, `proposed`) through gRPC's documented
   default Protocol Buffers service and message representation.

No `extends` or `influenced-by` relation is supported. Linux, Kubernetes, and
NGINX should remain unconnected in this scope; their broad scheduler, process,
event, and configuration similarities do not provide a sufficiently specific
evidenced bridge.
