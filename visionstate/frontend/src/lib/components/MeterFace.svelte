<script lang="ts">
  // The meter face around a reading sensor's region, straightened the way the region is read (the
  // backend's imaging.meter_face), with the region outlined: where pointer dials (DialsEditor) and an
  // extra region (ExtraRegionEditor) are placed, in units of the region's height from its top-left
  // corner. ``shapes`` are drawn in those units; ``overlay`` (handles, labels) is placed with ``at``.
  // Moves come back as points of that plane. Mouse and touch (pointer events), like the region editor.
  import type { Snippet } from 'svelte';
  import type { ReadPreview } from '../types';

  let {
    preview,
    testid,
    shapes,
    overlay,
    onmove,
    onend,
  }: {
    preview: ReadPreview & { face: string; face_box: [number, number, number, number] };
    testid: string;
    shapes: Snippet;
    overlay?: Snippet;
    onmove: (p: [number, number]) => void;
    onend: () => void;
  } = $props();

  const box = $derived(preview.face_box);
  const regionWidth = $derived(preview.region_width ?? 1);
  let surface = $state<HTMLDivElement>();

  /** Where a pointer is on the face, in units of the region's height. */
  export function planePoint(e: PointerEvent): [number, number] {
    const r = surface!.getBoundingClientRect();
    const [x0, y0, x1, y1] = box;
    return [x0 + ((e.clientX - r.left) / r.width) * (x1 - x0), y0 + ((e.clientY - r.top) / r.height) * (y1 - y0)];
  }

  /** Keep the moves of a drag that starts on a shape or handle coming to the face. */
  export function capture(e: PointerEvent) {
    e.stopPropagation();
    e.preventDefault();
    try {
      surface!.setPointerCapture(e.pointerId);
    } catch {
      /* pointer no longer active: moves still bubble to the surface */
    }
  }

  /** A point of the plane as left and top percentages of the face, for the overlay. */
  export function at(x: number, y: number): { left: string; top: string } {
    const [x0, y0, x1, y1] = box;
    return { left: `${((x - x0) / (x1 - x0)) * 100}%`, top: `${((y - y0) / (y1 - y0)) * 100}%` };
  }
</script>

<div
  class="surface"
  bind:this={surface}
  onpointermove={(e) => onmove(planePoint(e))}
  onpointerup={onend}
  onpointercancel={onend}
  role="presentation"
  data-testid={testid}
>
  <img src={preview.face} alt="The meter face, straightened" draggable="false" />
  <svg viewBox="{box[0]} {box[1]} {box[2] - box[0]} {box[3] - box[1]}" preserveAspectRatio="none" aria-hidden="true">
    <rect x="0" y="0" width={regionWidth} height="1" class="region" />
    {@render shapes()}
  </svg>
  {@render overlay?.()}
</div>

<style>
  .surface {
    --handle: 16px;
    position: relative;
    overflow: hidden;
    background: var(--c-sunken);
    border-radius: var(--radius-sm);
    user-select: none;
    -webkit-user-select: none;
    -webkit-touch-callout: none;
    touch-action: none;
  }
  @media (pointer: coarse) {
    .surface {
      --handle: 26px;
    }
  }
  img {
    display: block;
    width: 100%;
    height: auto;
    pointer-events: none;
  }
  svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }
  .region {
    fill: none;
    stroke: var(--c-accent);
    stroke-width: 2px;
    stroke-dasharray: 6 5;
    vector-effect: non-scaling-stroke;
  }
</style>
