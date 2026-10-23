# systemd taxonomy review

## Review boundary

This review covers the canonical card in `data/systems/systemd.json` at the
reviewed source context `558da3129cce0f4ab52cc03d7444d12355300daa`. It is a
taxonomy and evidence-coverage review only; the canonical card was not edited.
The card is a useful compact description of typed units, dependency
transactions, service supervision, readiness, timeouts, watchdogs, and restart
policy. The official documentation review adds the dimensions below as
follow-up candidates, not as claims already present in the card.

## Coverage assessment

| Dimension                          | Current card coverage                                                                                                          | Assessment and likely missing boundary                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Service manager and unit model     | `typed-unit-model` describes common typed units and a common lifecycle model.                                                  | **Good baseline, incomplete taxonomy.** The card does not distinguish the system manager from per-user managers, or static unit files from generated, transient, template, alias, and drop-in configuration. It also does not identify targets and special units as boot, shutdown, initrd, and user-session coordination objects.                                                                                                                                                                                                                  |
| Dependency and transaction graph   | `dependency-transaction-graph` separates requirement from ordering edges and describes transaction conflict resolution.        | **Adequate for the graph core.** A future review could add activation-time implicit/default dependencies, job modes, propagation relationships such as `BindsTo=`/`PartOf=`, and the distinction between a unit being active and a service being ready. The last distinction is already hinted at in the cost text and should remain explicit.                                                                                                                                                                                                      |
| Activation                         | The scope names socket and bus activation; the service feature mentions socket activation.                                     | **Partial and currently over-broad.** Socket activation is supported by the cited socket/service documentation, including listening sockets, descriptor passing, `Accept=`, and service triggering. No bus-specific evidence is present in the card, so “bus activation” should be treated as an unreviewed scope label until D-Bus evidence is added. Path, timer, device/udev, mount, automount, and credential/file-descriptor activation are also omitted if the intended taxonomy is activation mechanisms rather than only socket activation. |
| Process supervision                | `supervised-service-lifecycle` covers process tracking, `Type=notify`, timeouts, watchdogs, exit outcomes, and restart policy. | **Good core coverage.** It should eventually distinguish process supervision from readiness signaling, watchdog liveness, stop/kill policy, restart rate limiting, and failure propagation. These are different control loops and should not be collapsed into one “supervision” label.                                                                                                                                                                                                                                                             |
| Resource control                   | No feature, view, or evidence ID covers resources.                                                                             | **Missing major dimension.** `systemd.resource-control` describes a hierarchical cgroup model across services, slices, scopes, sockets, mounts, and swaps, with CPU, memory, I/O, task, network, accounting, delegation, and controller inheritance. A resource-control feature should model the unit-to-slice hierarchy and effective inherited limits, not merely list individual directives.                                                                                                                                                     |
| Journal and observability          | No feature, view, or evidence ID covers journald or service logging.                                                           | **Missing major dimension.** `systemd-journald` collects kernel, syslog, native journal, stdout/stderr, and audit records; supports structured metadata, persistent or volatile storage, journal namespaces, rotation/flush/sync operations, and access controls. Its stream-FD behavior during stop/restart is also relevant to recovery semantics. A future card addition needs journald evidence rather than treating generic service logs as sufficient.                                                                                        |
| Recovery and boot failure handling | The supervision view mentions failure, timeout, and restart; service evidence mentions restart policy.                         | **Partial.** Restart is only one recovery layer. The taxonomy should separately cover restart/backoff and start-rate limits, `OnFailure=`/dependency failure propagation, watchdog escalation, boot-complete health gates, initrd-to-host transition, rescue and emergency targets, shutdown/soft-reboot paths, and offline-update recovery boundaries. The special-unit documentation supports these as manager-level recovery and lifecycle states.                                                                                               |
| Execution and security boundaries  | Not named in scope or features.                                                                                                | **Unreviewed/optional depending on card scope.** `systemd.exec`, resource control, namespaces, credentials, user/group identity, filesystem restrictions, and network filtering form a substantial execution-isolation dimension. It should be added only if the review collects source-local evidence; it should not be inferred from the existence of service units.                                                                                                                                                                              |

## Service-manager, activation, resource, journal, and recovery answer

The card has enough detail to identify systemd as a typed unit/service manager
with dependency transactions and supervised service lifecycle. It does **not**
yet have enough detail for a taxonomy that claims to cover the full manager
architecture:

1. **Service manager:** sufficient for the core abstraction, but it lacks
   manager instances, generated/transient units, special targets, and the
   boot/initrd/user-session boundaries.
2. **Activation:** sufficient for socket activation at a high level, but the
   scope's bus-activation label is unsupported by the current evidence and the
   broader activation family is absent.
3. **Resources:** insufficient. Cgroups, slices, scopes, controller
   inheritance, accounting, and delegation are entirely absent.
4. **Journal:** insufficient. Structured collection, persistence mode,
   namespaces, metadata/access controls, and stream lifecycle are entirely
   absent.
5. **Recovery:** partially covered for service-local restart and watchdog
   behavior, but manager-level boot, dependency, and emergency recovery paths
   are absent.

## Scope-label review

The existing labels are useful as a first navigation set, but they mix
abstraction levels:

- `init and service manager` names a system role;
- `unit dependency graph` names a model;
- `service supervision` names an execution/control behavior; and
- `socket and bus activation` names two mechanisms, one of which is not
  evidenced in this card.

For a reviewed card, labels should describe reviewed dimensions rather than
serve as a complete feature inventory. A normalized current label set could be:

```text
init and service manager
typed unit model
dependency transactions and ordering
service readiness and supervision
socket activation
```

After separate evidence review, the following labels would be useful additions:

```text
activation mechanisms
cgroup resource control
structured journal and logging
boot, shutdown, and recovery targets
execution and security isolation
```

`activation mechanisms` should replace the narrower `socket and bus activation`
only when the card has evidence for the mechanisms it names. Conversely, if
the intended card remains deliberately narrow, retaining `socket activation`
and removing the unsupported bus label is the safer taxonomy choice.

## Recommended follow-up evidence units

These are review targets, not edits made by this document:

| Candidate dimension         | Primary documentation anchor                                                                        | Source areas to pin and inspect                                                                           |
| --------------------------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Socket and other activation | `systemd.socket`, `systemd.path`, `systemd.timer`, `systemd.device`, D-Bus activation documentation | socket/service activation paths, trigger job creation, descriptor passing, bus activation integration     |
| Cgroup resource control     | `systemd.resource-control`, `systemd.slice`, `systemd.scope`                                        | cgroup setup, slice placement, controller inheritance, delegation, effective limits                       |
| Journal                     | `systemd-journald.service`, `journald.conf`, `systemd.journal-fields`                               | journal sockets, stream forwarding, storage/rotation, namespace lifecycle, metadata and access boundaries |
| Boot and recovery           | `systemd.special`, `bootup`, `systemd.service`, `systemd-system.conf`                               | special targets, initrd transition, emergency/rescue paths, watchdog/restart limits, failure propagation  |
| Execution isolation         | `systemd.exec`, `systemd.kill`, resource-control network settings                                   | identity, namespaces, credentials, filesystem/network restrictions, process termination                   |

The current evidence IDs (`systemd-unit-doc`, `systemd-service-doc`,
`systemd-manager-source`, `systemd-transaction-source`, and
`systemd-service-source`) support the existing card, but they do not support
adding these dimensions without new evidence IDs and corresponding feature or
mathematical-view claims.

## Decision

Keep the current card as a valid compact service-manager card, subject to a
future evidence-backed review. Mark resource control and journald as the
highest-priority missing dimensions, then broaden recovery and activation with
separate evidence. Treat the current scope labels as useful navigation tags,
but narrow or qualify “bus activation” until it has source-local evidence.
