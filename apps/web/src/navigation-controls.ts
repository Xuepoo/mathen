type NavigationControls = {
  enableRotate: boolean;
  enablePan: boolean;
  screenSpacePanning: boolean;
  mouseButtons: {
    LEFT?: number | null;
    MIDDLE?: number | null;
    RIGHT?: number | null;
  };
  touches: { ONE?: number | null; TWO?: number | null };
};

// Three.js MOUSE: ROTATE=0, DOLLY=1, PAN=2; TOUCH: ROTATE=0, PAN=1, DOLLY_PAN=2.
export function configureNavigation(controls: NavigationControls, dimensions: 2 | 3) {
  controls.enableRotate = dimensions === 3;
  controls.enablePan = true;
  controls.screenSpacePanning = true;
  controls.mouseButtons.LEFT = dimensions === 2 ? 2 : 0;
  controls.mouseButtons.MIDDLE = 1;
  controls.mouseButtons.RIGHT = 2;
  controls.touches.ONE = dimensions === 2 ? 1 : 0;
  controls.touches.TWO = 2;
}
