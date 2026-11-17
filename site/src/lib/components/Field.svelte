<script lang="ts">
	// A numeric input row: label on the left, value and unit on the right, and where the prefilled value comes from below.
	// Typing updates the result on the same frame; arrow keys step by `step` (Shift for ten steps).
	import type { Snippet } from 'svelte';
	import { direct } from '#lib/motion.ts';

	let {
		label,
		value,
		set,
		unit = '',
		step = 1,
		digits,
		base,
		edited = false,
		reset,
		source
	}: {
		label: string;
		value: number;
		set: (v: number) => void;
		unit?: string;
		step?: number;
		/** Decimals always shown; defaults to the decimals of `step`. */
		digits?: number;
		/** The prefilled value, shown with a reset link once the field is edited. */
		base?: number;
		edited?: boolean;
		reset?: () => void;
		source?: Snippet;
	} = $props();
	const id = $props.id();

	const min = $derived(digits ?? Math.max(0, -Math.floor(Math.log10(step) + 1e-9)));
	const fmt = (v: number) =>
		new Intl.NumberFormat('sk-SK', { minimumFractionDigits: min, maximumFractionDigits: Math.max(min, 4) }).format(v).replace('-', '−');
	const parse = (s: string) => parseFloat(s.replace(/\s/g, '').replace(',', '.').replace('−', '-')); // \s covers the no-break spaces Intl inserts

	// While the field is being typed in, it shows what was typed rather than the formatted value.
	let draft = $state<string | null>(null);

	function input(e: Event) {
		draft = (e.currentTarget as HTMLInputElement).value;
		const v = parse(draft);
		if (Number.isFinite(v)) {
			direct();
			set(v);
		}
	}
	function key(e: KeyboardEvent) {
		if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;
		e.preventDefault();
		const v = +(value + (e.key === 'ArrowUp' ? 1 : -1) * step * (e.shiftKey ? 10 : 1)).toFixed(6);
		draft = fmt(v);
		direct();
		set(v);
	}
</script>

<div class="field" class:edited>
	<label for={id}>{label}<i aria-hidden="true"></i></label>
	<div class="box">
		<input
			{id}
			type="text"
			inputmode="decimal"
			autocomplete="off"
			spellcheck="false"
			value={draft ?? fmt(value)}
			oninput={input}
			onkeydown={key}
			onblur={() => (draft = null)}
		/>
		{#if unit}<span class="unit">{unit}</span>{/if}
	</div>
	<div class="src">
		{#if edited && reset}
			{#if base !== undefined}Pôvodne {fmt(base)}{unit ? `\u00a0${unit}` : ''}.{/if}
			<button class="link" onclick={reset}>Vrátiť</button>
		{:else if source}
			{@render source()}
		{/if}
	</div>
</div>

<style>
	.field {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 128px;
		column-gap: 12px;
		align-items: center;
		padding: 5px 0;
		min-width: 0;
	}
	label {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		color: var(--fg-2);
	}
	label i {
		flex: none;
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: var(--fg);
		opacity: 0;
		scale: 0.5;
		transition:
			opacity 150ms,
			scale 200ms var(--ease);
	}
	.edited label i {
		opacity: 1;
		scale: 1;
	}
	.box {
		display: flex;
		align-items: center;
		height: 30px;
		padding: 0 8px;
		border-radius: 6px;
		background: var(--field);
		box-shadow: var(--ring);
		transition: box-shadow 120ms;
	}
	@media (hover: hover) {
		.box:hover {
			box-shadow: var(--ring-hover);
		}
	}
	.box:focus-within {
		box-shadow:
			0 0 0 1px var(--fg),
			0 0 0 3px color-mix(in oklab, var(--fg) 10%, transparent);
	}
	.box input {
		all: unset;
		width: 100%;
		min-width: 0;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.unit {
		margin-left: 6px;
		font-size: 12px;
		color: var(--muted);
		white-space: nowrap;
	}
	.src {
		grid-column: 1 / -1;
		min-height: 17px;
		margin-top: 4px;
		font-size: 12px;
		line-height: 1.4;
		color: var(--muted);
	}
	.src:empty {
		display: none;
	}
</style>
