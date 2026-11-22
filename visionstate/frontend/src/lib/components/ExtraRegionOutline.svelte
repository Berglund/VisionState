<script lang="ts">
  // A display's extra region (settings.extra_region) drawn over the camera picture where it is read:
  // placed in the plane the region is read in, so it follows the region's corners in perspective
  // (lib/roi planeBox). Place inside RoiEditor's overlay, which is the positioned frame, like DigitCells.
  import { planeBox } from '../roi';
  import type { ExtraRegion, Roi } from '../types';

  let { roi, region, straightened = false }: { roi: Roi | null; region: ExtraRegion; straightened?: boolean } = $props();

  // The frame's shape (its width over its height): the plane's units are pixels, so the box's place
  // along the region depends on it. Read in a timeout, not in the ResizeObserver's callback (see
  // DetectionBoxes.measure).
  let aspect = $state(0);
  function measure(node: Element) {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const observer = new ResizeObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const { width, height } = node.getBoundingClientRect();
        aspect = height > 0 ? width / height : 0;
      });
    });
    observer.observe(node);
    return () => {
      clearTimeout(timer);
      observer.disconnect();
    };
  }

  // No region: the whole frame, as the backend reads it.
  const corners = $derived(planeBox(roi ?? { x: 0, y: 0, w: 1, h: 1 }, straightened, region, aspect));
</script>

<svg class="extra" viewBox="0 0 1 1" preserveAspectRatio="none" aria-hidden="true" {@attach measure} data-testid="extra-region-outline">
  {#if corners}<polygon points={corners.map((p) => p.join(',')).join(' ')} />{/if}
</svg>

<style>
  .extra {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }
  polygon {
    fill: color-mix(in srgb, var(--c-accent) 10%, transparent);
    stroke: var(--c-accent);
    stroke-width: 2px;
    stroke-dasharray: 3 3;
    vector-effect: non-scaling-stroke;
  }
</style>
