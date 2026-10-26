import { expect, test } from "bun:test";
import {
  compactModelLabel,
  createLabelPool,
  displayNodeColor,
  shouldShowLabel,
} from "./graph-labels";

test("model labels remove duplicate title prefixes and truncate deterministically", () => {
  expect(compactModelLabel("Same title: Finite labeled repository graph")).toBe(
    "Finite labeled repository graph",
  );
  expect(compactModelLabel("Same title: A very long mathematical model name", 20)).toBe(
    "A very long mathema…",
  );
  expect(compactModelLabel("Short model")).toBe("Short model");
});

test("node colors retain domain colors unless intentionally dimmed or selected", () => {
  expect(displayNodeColor({ baseColor: "#66dbc5" })).toBe("#66dbc5");
  expect(displayNodeColor({ baseColor: "#66dbc5", dimmed: true })).toBe("#34404c");
  expect(displayNodeColor({ baseColor: "#66dbc5", path: true })).toBe("#ffffff");
  expect(displayNodeColor({ baseColor: "#66dbc5", savedPathColor: "#e7bb7d" })).toBe("#e7bb7d");
});

test("clearing a graph cancels queued allocations before their frame runs", () => {
  const frames: (() => void)[] = [];
  let allocations = 0;
  const pool = createLabelPool<{ id: string }, object>({
    schedule: (run) => frames.push(run),
    create: () => {
      allocations++;
      return {};
    },
    update: () => {},
    dispose: () => {},
  });
  pool.sync([{ id: "removed" }]);
  pool.clear();
  frames.shift()!();
  expect(allocations).toBe(0);
  expect(frames).toHaveLength(0);
});

test("only requested labels allocate resources, in bounded batches", () => {
  const frames: (() => void)[] = [];
  const created: string[] = [];
  const disposed: string[] = [];
  const pool = createLabelPool<{ id: string }, { id: string }>({
    schedule: (run) => frames.push(run),
    create: (item) => {
      created.push(item.id);
      return item;
    },
    update: () => {},
    dispose: (item) => disposed.push(item.id),
    batchSize: 2,
  });
  pool.sync([{ id: "a" }, { id: "b" }, { id: "c" }]);
  expect(created).toEqual([]);
  frames.shift()!();
  expect(created).toEqual(["a", "b"]);
  pool.sync([{ id: "a" }, { id: "d" }]);
  expect(disposed).toEqual(["b"]);
  frames.shift()!();
  expect(created).toEqual(["a", "b", "d"]);
  expect(frames).toHaveLength(0);
  pool.clear();
  expect(disposed).toEqual(["b", "a", "d"]);
});

test("repeated sync reuses resources and pending callbacks use the newest graph", () => {
  const frames: (() => void)[] = [];
  const created: string[] = [];
  const updates: string[] = [];
  const pool = createLabelPool<{ id: string; color: string }, { id: string }>({
    schedule: (run) => frames.push(run),
    create: (item) => {
      created.push(item.id);
      return { id: item.id };
    },
    update: (_resource, item) => updates.push(item.color),
    dispose: () => {},
  });
  pool.sync([{ id: "old", color: "white" }]);
  pool.clear();
  pool.sync([{ id: "new", color: "mint" }]);
  expect(frames).toHaveLength(1);
  frames.shift()!();
  pool.sync([{ id: "new", color: "white" }]);
  expect(created).toEqual(["new"]);
  expect(updates).toEqual(["mint", "white"]);
  expect(frames).toHaveLength(0);
});

test("mobile label mode keeps selected and searched nodes without showing the highlighted neighborhood", () => {
  const options = {
    allNames: false,
    mobile: true,
    selectedId: "selected",
    highlighted: new Set(["selected", "neighbor"]),
    searchMatches: new Set<string>(),
  };
  expect(shouldShowLabel({ ...options, id: "selected" })).toBe(true);
  expect(shouldShowLabel({ ...options, id: "neighbor" })).toBe(false);
  expect(
    shouldShowLabel({
      ...options,
      id: "search",
      searchMatches: new Set(["search"]),
    }),
  ).toBe(true);
  expect(shouldShowLabel({ ...options, id: "neighbor", mobile: false })).toBe(true);
});
