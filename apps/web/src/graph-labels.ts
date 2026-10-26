/** Keep resources only for requested labels, spreading canvas creation across frames. */
export function createLabelPool<Item extends { id: string }, Resource>(options: {
  create: (item: Item) => Resource;
  update: (resource: Resource, item: Item) => void;
  dispose: (resource: Resource) => void;
  schedule: (run: () => void) => void;
  batchSize?: number;
}) {
  const resources = new Map<string, Resource>();
  let pending: Item[] = [];
  let scheduled = false;
  const batchSize = options.batchSize ?? 4;

  function schedule() {
    if (scheduled || !pending.length) return;
    scheduled = true;
    options.schedule(() => {
      scheduled = false;
      for (const item of pending.splice(0, batchSize)) {
        const resource = options.create(item);
        resources.set(item.id, resource);
        options.update(resource, item);
      }
      schedule();
    });
  }

  return {
    sync(items: Item[]) {
      const wanted = new Map(items.map((item) => [item.id, item]));
      for (const [id, resource] of resources) {
        const item = wanted.get(id);
        if (item) options.update(resource, item);
        else {
          options.dispose(resource);
          resources.delete(id);
        }
      }
      pending = items.filter((item) => !resources.has(item.id));
      schedule();
    },
    clear() {
      pending = [];
      for (const resource of resources.values()) options.dispose(resource);
      resources.clear();
    },
  };
}

export function shouldShowLabel(options: {
  id: string;
  allNames: boolean;
  mobile: boolean;
  selectedId?: string;
  hoveredId?: string;
  highlighted: Set<string>;
  searchMatches?: Set<string>;
}) {
  return (
    options.allNames ||
    options.id === options.selectedId ||
    options.id === options.hoveredId ||
    (!options.mobile && options.highlighted.has(options.id)) ||
    Boolean(options.searchMatches?.has(options.id))
  );
}

/** Keep model labels scannable on the canvas without changing their full names. */
export function compactModelLabel(name: string, maxLength = 34): string {
  const normalized = name.replace(/^(?:same title:\s*)+/i, "").trim();
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, Math.max(1, maxLength - 1)).trimEnd()}…`;
}

export function displayNodeColor(options: {
  baseColor: string;
  selected?: boolean;
  path?: boolean;
  savedPathColor?: string;
  dimmed?: boolean;
}) {
  if (options.selected) return "#ffffff";
  if (options.savedPathColor) return options.savedPathColor;
  if (options.path) return "#ffffff";
  if (options.dimmed) return "#34404c";
  return options.baseColor;
}
