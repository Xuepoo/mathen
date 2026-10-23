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
