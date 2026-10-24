import { expect, test } from "bun:test";
import { lazyModule } from "./lazy-module";

test("shares an in-flight module load between callers", async () => {
  let loads = 0;
  let resolve!: (value: { name: string }) => void;
  const load = lazyModule(
    () =>
      new Promise<{ name: string }>((complete) => {
        loads++;
        resolve = complete;
      }),
  );

  const first = load();
  const second = load();
  expect(first).toBe(second);
  expect(loads).toBe(1);

  resolve({ name: "force graph" });
  await expect(first).resolves.toEqual({ name: "force graph" });
});

test("allows a failed module load to be retried", async () => {
  let loads = 0;
  const load = lazyModule(async () => {
    loads++;
    if (loads === 1) throw new Error("chunk unavailable");
    return "loaded";
  });

  await expect(load()).rejects.toThrow("chunk unavailable");
  await expect(load()).resolves.toBe("loaded");
  expect(loads).toBe(2);
});
