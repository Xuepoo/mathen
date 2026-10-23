type Point = { x: number; y: number; z: number };

/** Translate the camera and orbit target together, preserving viewing angle and distance. */
export function centeredCamera(position: Point, target: Point, node: Point) {
  return {
    position: {
      x: node.x + position.x - target.x,
      y: node.y + position.y - target.y,
      z: node.z + position.z - target.z,
    },
    target: { ...node },
  };
}
