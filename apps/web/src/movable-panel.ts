/** A title handle moves the panel; body controls and scrolling retain normal behavior. */
export function movablePanel(panel: HTMLElement) {
  let position: { x: number; y: number } | undefined;
  let drag: { id: number; x: number; y: number; left: number; top: number } | undefined;
  function place(x: number, y: number) {
    const rect = panel.getBoundingClientRect();
    position = {
      x: Math.max(8, Math.min(x, window.innerWidth - rect.width - 8)),
      y: Math.max(8, Math.min(y, window.innerHeight - rect.height - 8)),
    };
    panel.style.left = `${position.x}px`;
    panel.style.top = `${position.y}px`;
    panel.style.right = "auto";
    panel.style.bottom = "auto";
  }
  panel.addEventListener("pointerdown", (event) => {
    const handle = (event.target as Element).closest<HTMLElement>("[data-move-panel]");
    if (!handle || event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    const rect = panel.getBoundingClientRect();
    drag = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      left: rect.left,
      top: rect.top,
    };
    handle.focus();
    handle.setPointerCapture(event.pointerId);
  });
  panel.addEventListener("pointermove", (event) => {
    if (!drag || event.pointerId !== drag.id) return;
    event.stopPropagation();
    place(drag.left + event.clientX - drag.x, drag.top + event.clientY - drag.y);
  });
  for (const type of ["pointerup", "pointercancel", "lostpointercapture"])
    panel.addEventListener(type, () => {
      drag = undefined;
    });
  panel.addEventListener("keydown", (event) => {
    if (!(event.target as Element).matches("[data-move-panel]")) return;
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [-1, 0],
      ArrowRight: [1, 0],
      ArrowUp: [0, -1],
      ArrowDown: [0, 1],
    };
    if (event.key === "Home") {
      event.preventDefault();
      reset();
      return;
    }
    const move = moves[event.key];
    if (!move) return;
    event.preventDefault();
    const rect = panel.getBoundingClientRect();
    const step = event.shiftKey ? 40 : 10;
    place(rect.left + move[0] * step, rect.top + move[1] * step);
  });
  function clamp() {
    if (position && !panel.hidden) place(position.x, position.y);
  }
  function reset() {
    position = undefined;
    for (const key of ["left", "top", "right", "bottom"] as const) panel.style[key] = "";
  }
  window.addEventListener("resize", clamp);
  new ResizeObserver(clamp).observe(panel);
  return { reset, clamp };
}
