<script lang="ts">
	// A numeric input that shows where its prefilled value comes from and resets to it.
	import type { Snippet } from 'svelte';

	let {
		label,
		value,
		set,
		unit = '',
		step = 1,
		min,
		max,
		edited = false,
		reset,
		source
	}: {
		label: string;
		value: number;
		set: (v: number) => void;
		unit?: string;
		step?: number;
		min?: number;
		max?: number;
		edited?: boolean;
		reset?: () => void;
		source?: Snippet;
	} = $props();
	const id = `f-${Math.random().toString(36).slice(2, 8)}`;
	const shown = $derived(+value.toFixed(4));
</script>

<div class="field">
	<label for={id}>{label}</label>
	<div class="row">
		<input
			{id}
			type="number"
			inputmode="decimal"
			value={shown}
			{step}
			{min}
			{max}
			onchange={(e) => {
				const v = parseFloat((e.currentTarget as HTMLInputElement).value.replace(',', '.'));
				if (Number.isFinite(v)) set(v);
			}}
		/>
		{#if unit}<span class="unit">{unit}</span>{/if}
	</div>
	<div class="src small muted">
		{#if edited && reset}
			<span>Upravené. <button class="link" onclick={reset}>Vrátiť predvolené</button></span>
		{:else if source}
			{@render source()}
		{/if}
	</div>
</div>

<style>
	.field {
		min-width: 0;
	}
	label {
		font-size: 13px;
		display: block;
		margin-bottom: 2px;
	}
	.row {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.unit {
		font-size: 13px;
		color: var(--muted);
		white-space: nowrap;
	}
	.src {
		min-height: 18px;
		font-size: 12px;
		line-height: 1.35;
		margin-top: 2px;
	}
	.link {
		border: 0;
		background: none;
		color: var(--accent);
		padding: 0;
		text-decoration: underline;
		font-size: 12px;
	}
</style>
