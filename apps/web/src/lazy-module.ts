export function lazyModule<T>(load: () => Promise<T>): () => Promise<T> {
  let pending: Promise<T> | undefined;

  return () => {
    if (pending) return pending;

    pending = load().catch((error: unknown) => {
      pending = undefined;
      throw error;
    });
    return pending;
  };
}
