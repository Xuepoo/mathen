import { expect, test } from "bun:test";
import { centeredCamera } from "./graph-camera";

test("centering an off-plane node preserves the camera offset without mutating inputs", () => {
  const position = { x: 300, y: -100, z: 800 };
  const target = { x: 50, y: 25, z: 100 };
  const node = { x: -120, y: 80, z: -40 };
  const before = JSON.stringify({ position, target, node });
  const result = centeredCamera(position, target, node);
  expect(result.target).toEqual(node);
  for (const axis of ["x", "y", "z"] as const)
    expect(result.position[axis] - result.target[axis]).toBe(position[axis] - target[axis]);
  expect(JSON.stringify({ position, target, node })).toBe(before);
});

test("centering in 2D keeps the camera facing the plane at the same zoom distance", () => {
  expect(
    centeredCamera({ x: 20, y: 40, z: 700 }, { x: 20, y: 40, z: 0 }, { x: -50, y: 90, z: 0 }),
  ).toEqual({
    position: { x: -50, y: 90, z: 700 },
    target: { x: -50, y: 90, z: 0 },
  });
});
