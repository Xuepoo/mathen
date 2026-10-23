type Point = { x: number; y: number; z: number };
type LayoutNode = { id: string; x?: number; y?: number; z?: number; vz?: number };
export type SafeViewport = {
  width: number;
  height: number;
  left: number;
  right: number;
  top: number;
  bottom: number;
};

/** Stable nonzero depth breaks the planar equilibrium of a previously 2D simulation. */
export function depthFor(id: string) {
  let hash = 2166136261;
  for (const character of id) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  return (((hash >>> 0) % 201) - 100 || 1) * 3.2;
}

export function seedCoordinates(nodes: LayoutNode[], dimensions: 2 | 3) {
  nodes.forEach((node, index) => {
    const angle = index * Math.PI * (3 - Math.sqrt(5));
    const radius = 18 * Math.sqrt(index + 1);
    if (!Number.isFinite(node.x)) node.x = Math.cos(angle) * radius;
    if (!Number.isFinite(node.y)) node.y = Math.sin(angle) * radius;
    if (dimensions === 2) node.z = 0;
    else if (!Number.isFinite(node.z) || node.z === 0) node.z = depthFor(node.id);
    node.vz = 0;
  });
}

export function worldUnitsPerPixel(depth: number, fov: number, height: number) {
  return (2 * Math.max(0.01, depth) * Math.tan((fov * Math.PI) / 360)) / Math.max(1, height);
}

/** O(n) bounds and perspective constraints; space O(1). Camera looks along -Z. */
export function frameNodes(nodes: Point[], viewport: SafeViewport, fov: number) {
  let minX = Infinity,
    maxX = -Infinity,
    minY = Infinity,
    maxY = -Infinity;
  for (const node of nodes) {
    minX = Math.min(minX, node.x);
    maxX = Math.max(maxX, node.x);
    minY = Math.min(minY, node.y);
    maxY = Math.max(maxY, node.y);
  }
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  const unit = worldUnitsPerPixel(1, fov, viewport.height);
  const width = Math.max(40, viewport.right - viewport.left);
  const height = Math.max(40, viewport.bottom - viewport.top);
  const offsetX = (viewport.left + viewport.right - viewport.width) / 2;
  const offsetY = (viewport.top + viewport.bottom - viewport.height) / 2;
  let distance = 120;
  for (const node of nodes) {
    // Account for depth-dependent parallax as well as projected extent.
    distance = Math.max(
      distance,
      node.z + (2 * Math.abs((node.x - centerX) / unit + offsetX * node.z)) / width,
      node.z + (2 * Math.abs((node.y - centerY) / unit - offsetY * node.z)) / height,
    );
  }
  distance *= 1.06;
  const target = {
    x: centerX - offsetX * unit * distance,
    y: centerY + offsetY * unit * distance,
    z: 0,
  };
  return { position: { ...target, z: distance }, target };
}
