<script lang="ts">
  // A display's extra region (settings.extra_region): a box on its meter face (MeterFace) round the
  // smaller digits beside the others, read on its own and added as more decimals (a water meter's
  // litres after its m³). Drag the box to move it, its handle to size it.
  import { app } from '../app.svelte';
  import type { ExtraRegion, ReadPreview } from '../types';
  import { EXTRA_REGION_NEW } from '../ui';
  import Icon from './Icon.svelte';
  import MeterFace from './MeterFace.svelte';

  type Drag = { mode: 'move' | 'size'; start: [number, number]; orig: ExtraRegion };

  let {
    preview,
    region = $bindable(),
    decimals,
  }: { preview: ReadPreview | null; region: ExtraRegion | null; decimals: number } = $props();

  const limits = $derived(app.config!.reading_extra_region);
  const reach = $derived(app.config!.reading_dials.dial_reach);
  const box = $derived(preview?.face_box ?? null);
  const regionWidth = $derived(preview?.region_width ?? 1);
  // What it read on its own: only shown while it was read with this many digits.
  const read = $derived(preview?.extra ?? null);

  let face = $state<MeterFace>();
  let drag: Drag | null = null;

  const round = (n: number) => Math.round(n * 1e4) / 1e4;
  const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, n));

  /** The box kept on the face shown and within the limits the backend takes. */
  function kept(r: ExtraRegion): ExtraRegion {
    const [x0, y0, x1, y1] = box!;
    const left = Math.max(x0, -reach);
    const top = Math.max(y0, -reach);
    const right = Math.min(x1, regionWidth + reach);
    const bottom = Math.min(y1, 1 + reach);
    const w = clamp(r.w, limits.extra_region_min, right - left);
    const h = clamp(r.h, limits.extra_region_min, bottom - top);
    return {
      x: round(clamp(r.x, left, right - w)),
      y: round(clamp(r.y, top, bottom - h)),
      w: round(w),
      h: round(h),
      digits: clamp(Math.round(r.digits), 1, limits.max_extra_digits),
    };
  }

  function start(e: PointerEvent, mode: Drag['mode']) {
    if (!box || !face || !region) return;
    face.capture(e);
    drag = { mode, start: face.planePoint(e), orig: { ...region } };
  }

  function move(p: [number, number]) {
    if (!drag) return;
    const { orig } = drag;
    const dx = p[0] - drag.start[0];
    const dy = p[1] - drag.start[1];
    region = kept(drag.mode === 'move' ? { ...orig, x: orig.x + dx, y: orig.y + dy } : { ...orig, w: orig.w + dx, h: orig.h + dy });
  }

  function end() {
    drag = null;
  }

  /** A new box at the region's top right, where a meter shows its smaller digits. */
  function add() {
    if (!box) return;
    const { gap, w, h, digits } = EXTRA_REGION_NEW;
    region = kept({ x: regionWidth + gap, y: 0, w, h, digits });
  }

  function setDigits(value: number) {
    if (region && Number.isFinite(value)) region = kept({ ...region, digits: value });
  }

  /** What the last small digit is worth, in the unit: ×0.001 for three after whole m³. */
  const last = $derived(region ? (10 ** -(decimals + region.digits)).toFixed(decimals + region.digits) : '');
</script>

{#if preview?.face && box}
  <div class="col" style="gap:var(--space-2)">
    <MeterFace bind:this={face} preview={{ ...preview, face: preview.face, face_box: box }} testid="extra-region-editor" onmove={move} onend={end}>
      {#snippet shapes()}
        {#if region}
          <rect
            x={region.x}
            y={region.y}
            width={region.w}
            height={region.h}
            class="extra"
            onpointerdown={(e) => start(e, 'move')}
            role="presentation"
            data-testid="extra-region"
          />
        {/if}
      {/snippet}
      {#snippet overlay()}
        {#if region}
          {@const top = face?.at(region.x + region.w / 2, region.y)}
          {@const corner = face?.at(region.x + region.w, region.y + region.h)}
          <span class="label" style:left={top?.left} style:top={top?.top}>{region.digits} small digit{region.digits === 1 ? '' : 's'}</span>
          <span
            class="handle"
            style:left={corner?.left}
            style:top={corner?.top}
            onpointerdown={(e) => start(e, 'size')}
            title="Drag to size the box"
            role="presentation"
            data-testid="extra-region-size"
          ></span>
        {/if}
      {/snippet}
    </MeterFace>
    <p class="help">
      Put the box round the smaller digits only, a little room around them: drag it to move it, its handle to size it.
      The dashed box is the region with the big digits.
    </p>
    {#if region}
      <div class="row wrap extra-row" data-testid="extra-region-row">
        <label class="row digits">
          Digits
          <input
            class="input mono"
            type="number"
            min="1"
            max={limits.max_extra_digits}
            value={region.digits}
            onchange={(e) => setDigits(Number(e.currentTarget.value))}
            data-testid="extra-region-digits"
          />
        </label>
        <span class="xsmall muted grow">
          {#if !read}
            Not read yet
          {:else if read.text.replace(/\D/g, '').length !== region.digits}
            <span class="warn-text">Read <span class="mono">“{read.text || '—'}”</span>: not {region.digits} digits</span>
          {:else}
            Read <span class="mono">{read.text}</span> — the last one ×{last}
          {/if}
        </span>
        <button class="btn sm ghost" onclick={() => (region = null)} aria-label="Remove the box of small digits">
          <Icon name="trash" size={14} />
        </button>
      </div>
    {:else}
      <div class="row wrap" style="gap:8px">
        <button class="btn sm" onclick={add} data-testid="extra-region-add">
          <Icon name="plus" size={14} /> Add a box
        </button>
        <span class="xsmall faint">No box: the number is read from the region only.</span>
      </div>
    {/if}
  </div>
{:else}
  <p class="small muted">The display shows here once it has been read.</p>
{/if}

<style>
  .extra {
    fill: var(--c-accent);
    fill-opacity: 0.12;
    stroke: var(--c-accent);
    stroke-width: 2px;
    vector-effect: non-scaling-stroke;
    pointer-events: all;
    cursor: move;
  }
  .label {
    position: absolute;
    transform: translate(-50%, -115%);
    padding: 0 6px;
    border-radius: var(--radius-pill);
    background: var(--c-accent);
    color: var(--c-accent-ink);
    font: 700 var(--fs-xs) / 1.5 var(--font-mono);
    pointer-events: none;
    white-space: nowrap;
  }
  .handle {
    position: absolute;
    width: var(--handle);
    height: var(--handle);
    transform: translate(-50%, -50%);
    box-sizing: border-box;
    border-radius: 999px;
    background: var(--c-bg);
    border: 2px solid var(--c-accent);
    cursor: nwse-resize;
    touch-action: none;
  }
  .help {
    margin: 0;
    font-size: var(--fs-sm);
    color: var(--c-faint);
  }
  .extra-row {
    gap: 8px;
    align-items: center;
    padding: 6px 8px;
    border: 1px solid var(--c-border);
    border-radius: var(--radius-sm);
  }
  .digits {
    gap: 6px;
    align-items: center;
    font-size: var(--fs-sm);
  }
  .digits input {
    width: 4.5em;
  }
  .grow {
    flex: 1 1 8em;
  }
  .warn-text {
    color: var(--c-warn);
  }
</style>
