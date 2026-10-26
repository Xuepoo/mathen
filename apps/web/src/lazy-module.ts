export function lazyModule<T>(load: () => Promise<T>): () => Promise<T> {
  let pending: Promise<T> | undefined;

  return () => {
    if (pending) return pending;

    try {
      pending = load().catch((error: unknown) => {
        pending = undefined;
        throw error;
      });
    } catch (error) {
      pending = undefined;
      return Promise.reject(error);
    }
    return pending;
  };
}
