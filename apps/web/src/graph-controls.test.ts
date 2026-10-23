import { expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { configureNavigation } from "./navigation-controls";

const require = createRequire(import.meta.url);
const graphPath = require.resolve("3d-force-graph");
const graphRequire = createRequire(graphPath);
const { PerspectiveCamera } = await import(
  pathToFileURL(graphRequire.resolve("three").replace(/three\.cjs$/, "three.module.js")).href
);
const { OrbitControls } = await import(
  pathToFileURL(graphRequire.resolve("three/examples/jsm/controls/OrbitControls.js")).href
);
const source = readFileSync(graphPath, "utf8");
const start = source.indexOf("dragControls.addEventListener('dragend', ");
const end = source.indexOf("\n        });", start);
if (start < 0 || end < 0) throw new Error("Review the dependency drag-end regression harness");
// Execute the installed dependency's real listener with real OrbitControls.
// The only substitutes are the DOM, renderer and force simulation.
const makeDragEnd = new Function(
  "getGraphObj",
  "controls",
  "state",
  "PointerEvent",
  "renderer",
  `return ${source.slice(start + "dragControls.addEventListener('dragend', ".length, end)}\n}`,
);

class Pointer extends Event {
  constructor(type: string, init: Record<string, unknown>) {
    super(type);
    Object.assign(this, init);
  }
}

for (const pointerType of ["mouse", "touch"]) {
  test(`primary ${pointerType} pans in 2D after returning from 3D`, () => {
    const ownerDocument = new EventTarget();
    const element = Object.assign(new EventTarget(), {
      ownerDocument,
      style: {},
      clientWidth: 1000,
      clientHeight: 800,
      getRootNode: () => ownerDocument,
      getBoundingClientRect: () => ({
        left: 0,
        top: 0,
        width: 1000,
        height: 800,
      }),
      setPointerCapture: () => {},
      releasePointerCapture: () => {},
    });
    const camera = new PerspectiveCamera();
    camera.position.set(0, 0, 700);
    const controls = new OrbitControls(camera, element);
    for (const dimensions of [2, 3, 2] as const) {
      configureNavigation(controls, dimensions);
      const target = controls.target.clone();
      const position = camera.position.clone();
      const event = (type: string, x: number) =>
        new Pointer(type, {
          pointerId: 7,
          pointerType,
          button: 0,
          clientX: x,
          clientY: 200,
          pageX: x,
          pageY: 200,
        });
      element.dispatchEvent(event("pointerdown", 200));
      ownerDocument.dispatchEvent(event("pointermove", 280));
      ownerDocument.dispatchEvent(event("pointerup", 280));
      expect(camera.position.distanceTo(position)).toBeGreaterThan(0);
      if (dimensions === 2) expect(controls.target.distanceTo(target)).toBeGreaterThan(0);
      else expect(controls.target.distanceTo(target)).toBe(0);
    }
    controls.dispose();
  });
}

for (const pointerTypes of [["mouse"], ["touch"], ["touch", "touch"]]) {
  test(`node release clears ${pointerTypes.join(" + ")} pointers before navigation resumes`, () => {
    const ownerDocument = new EventTarget();
    const element = Object.assign(new EventTarget(), {
      ownerDocument,
      style: {},
      clientWidth: 1000,
      clientHeight: 800,
      getRootNode: () => ownerDocument,
      getBoundingClientRect: () => ({
        left: 0,
        top: 0,
        width: 1000,
        height: 800,
      }),
      setPointerCapture: () => {},
      releasePointerCapture: () => {},
    });
    const controls = new OrbitControls(new PerspectiveCamera(), element);
    pointerTypes.forEach((pointerType, index) =>
      element.dispatchEvent(
        new Pointer("pointerdown", {
          pointerId: 7 + index,
          pointerType,
          button: 0,
          clientX: 200,
          clientY: 200,
          pageX: 200,
          pageY: 200,
        }),
      ),
    );
    expect(controls._pointers).toEqual(pointerTypes.map((_, index) => 7 + index));
    controls.enabled = false;
    let ended = false;
    const forceGraph = {
      d3AlphaTarget: () => forceGraph,
      resetCountdown: () => forceGraph,
    };
    const node = {
      x: 10,
      y: 20,
      z: 0,
      fx: 10,
      fy: 20,
      fz: 0,
      __initialFixedPos: {},
      __initialPos: { x: 0, y: 0, z: 0 },
      __dragged: true,
    };
    const dragEnd = makeDragEnd(
      (object: unknown) => object,
      controls,
      {
        enableNavigationControls: true,
        forceGraph,
        onNodeDragEnd: () => {
          ended = true;
        },
      },
      Pointer,
      { domElement: { classList: { remove: () => {} } } },
    );
    dragEnd({ object: { __data: node } });
    expect(ended).toBe(true);
    expect(controls.enabled).toBe(true);
    expect(controls._pointers).toEqual([]);
    expect(controls.state).toBe(-1);
    expect(node.fx).toBeUndefined();
    expect(node.fy).toBeUndefined();
    const position = controls.object.position.clone();
    ownerDocument.dispatchEvent(
      new Pointer("pointermove", {
        pointerId: 7,
        pointerType: pointerTypes[0],
        clientX: 500,
        clientY: 500,
        pageX: 500,
        pageY: 500,
      }),
    );
    expect(controls.object.position.equals(position)).toBe(true);
    controls.dispose();
  });
}
