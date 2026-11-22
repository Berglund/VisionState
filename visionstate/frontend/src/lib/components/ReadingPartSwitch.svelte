<script lang="ts">
  // What the picture edits (the wizard and Settings): the region, or what is read beside it — a
  // counter's pointer dials (``kind`` "dials") or a display's box of smaller digits ("digits").
  let {
    editing = $bindable(),
    kind,
    count,
  }: { editing: 'region' | 'extra'; kind: 'dials' | 'digits'; count: number } = $props();
</script>

<div class="row wrap switch" role="group" aria-label="What the picture edits">
  <span class="small muted">Edit:</span>
  <button type="button" class="btn sm" class:primary={editing === 'region'} aria-pressed={editing === 'region'} onclick={() => (editing = 'region')}>
    {kind === 'dials' ? 'Counter' : 'Display'}
  </button>
  <button
    type="button"
    class="btn sm"
    class:primary={editing === 'extra'}
    aria-pressed={editing === 'extra'}
    onclick={() => (editing = 'extra')}
    data-testid={kind === 'dials' ? 'edit-dials' : 'edit-extra-region'}
  >
    {kind === 'dials' ? 'Dials' : 'Small digits'}{count ? ` (${count})` : ''}
  </button>
  {#if editing === 'region' && !count}
    <span class="xsmall faint">
      {#if kind === 'dials'}
        Has the meter pointer dials (×0.1, ×0.01 …)? Add them under <em>Dials</em>.
      {:else}
        Are the last digits smaller, beside the others (litres after m³)? Read them under <em>Small digits</em>.
      {/if}
    </span>
  {/if}
</div>

<style>
  .switch {
    gap: 8px;
  }
</style>
