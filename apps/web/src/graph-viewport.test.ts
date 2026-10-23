import { expect, test } from "bun:test";
import { depthFor, frameNodes, seedCoordinates, worldUnitsPerPixel } from "./graph-viewport";

test("flat and invalid coordinates receive deterministic finite depth without moving valid x/y", () => {
  const nodes = [
    { id: "a", x: 20, y: -30, z: 0 },
    { id: "b", x: NaN, y: Infinity },
  ];
  seedCoordinates(nodes, 3);
  expect(nodes[0].x).toBe(20);
  expect(nodes[0].y).toBe(-30);
  expect(nodes[0].z).toBe(depthFor("a"));
  expect(nodes.every((node) => [node.x, node.y, node.z].every(Number.isFinite))).toBe(true);
  expect(nodes[0].z).not.toBe(nodes[1].z);
  seedCoordinates(nodes, 2);
  expect(nodes.every((node) => node.z === 0)).toBe(true);
});

test("perspective framing includes deep chains within an asymmetric safe viewport", () => {
  const nodes = [
    { x: -700, y: -90, z: 300 },
    { x: 800, y: 100, z: -400 },
  ];
  const viewport = { width: 390, height: 844, left: 30, right: 300, top: 220, bottom: 680 };
  const frame = frameNodes(nodes, viewport, 50);
  for (const node of nodes) {
    const units = worldUnitsPerPixel(frame.position.z - node.z, 50, viewport.height);
    const x = viewport.width / 2 + (node.x - frame.position.x) / units;
    const y = viewport.height / 2 - (node.y - frame.position.y) / units;
    expect(x).toBeGreaterThanOrEqual(viewport.left);
    expect(x).toBeLessThanOrEqual(viewport.right);
    expect(y).toBeGreaterThanOrEqual(viewport.top);
    expect(y).toBeLessThanOrEqual(viewport.bottom);
  }
});

test("screen pixel scale tracks depth and viewport height, independent of DPR", () => {
  expect(worldUnitsPerPixel(1000, 50, 900)).toBeCloseTo(2 * worldUnitsPerPixel(500, 50, 900));
  expect(worldUnitsPerPixel(500, 50, 900)).toBeGreaterThan(0);
});

test("repeated 2D/3D transitions seed genuinely noncoplanar coordinates", () => {
  const nodes = Array.from({ length: 20 }, (_, index) => ({
    id: `node-${index}`,
    x: Math.sin(index) * 100,
    y: Math.cos(index) * 100,
    z: 0,
  }));
  for (let iteration = 0; iteration < 3; iteration++) {
    seedCoordinates(nodes, 2);
    expect(nodes.every((node) => node.z === 0)).toBe(true);
    seedCoordinates(nodes, 3);
    const origin = nodes[0];
    const vectors = nodes
      .slice(1, 4)
      .map((node) => [node.x - origin.x, node.y - origin.y, node.z - origin.z]);
    const [a, b, c] = vectors;
    const volume =
      a[0] * (b[1] * c[2] - b[2] * c[1]) -
      a[1] * (b[0] * c[2] - b[2] * c[0]) +
      a[2] * (b[0] * c[1] - b[1] * c[0]);
    expect(Math.abs(volume)).toBeGreaterThan(1000);
  }
});
