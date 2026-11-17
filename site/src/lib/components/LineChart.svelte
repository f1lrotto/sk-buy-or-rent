<script lang="ts">
	// Small dependency-free SVG line chart with hover readout and direct end labels.
	import { num } from '#lib/format.ts';

	export interface Series {
		name: string;
		values: (number | null)[];
		color?: string;
		dashed?: boolean;
		width?: number;
	}
	interface Marker {
		at: number;
		label: string;
	}

	let {
		x,
		series,
		format = (v: number) => num(v),
		height = 220,
		marker,
		yMin,
		yMax,
		endLabels = true,
		xTickEvery
	}: {
		x: string[];
		series: Series[];
		format?: (v: number) => string;
		height?: number;
		marker?: Marker;
		yMin?: number;
		yMax?: number;
		endLabels?: boolean;
		xTickEvery?: number;
	} = $props();

	let width = $state(640);
	let hover = $state<number | null>(null);
	const padL = 64;
	const padR = $derived(endLabels ? 110 : 12);
	const padT = 10;
	const padB = 24;

	const all = $derived(series.flatMap((s) => s.values.filter((v): v is number => v !== null && Number.isFinite(v))));
	const lo = $derived(yMin ?? Math.min(...all));
	const hi = $derived(yMax ?? Math.max(...all));
	const ticks = $derived.by(() => {
		const span = hi - lo || 1;
		const step0 = span / 4;
		const mag = 10 ** Math.floor(Math.log10(step0));
		const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= step0) ?? step0;
		const out: number[] = [];
		for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(10));
		return out;
	});
	const y0 = $derived(Math.min(lo, ticks[0] ?? lo));
	const y1 = $derived(Math.max(hi, ticks.at(-1) ?? hi));
	const sx = (i: number) => padL + (i / Math.max(1, x.length - 1)) * (width - padL - padR);
	const sy = (v: number) => padT + (1 - (v - y0) / (y1 - y0 || 1)) * (height - padT - padB);
	const path = (vals: (number | null)[]) => {
		let d = '';
		let pen = false;
		vals.forEach((v, i) => {
			if (v === null || !Number.isFinite(v)) {
				pen = false;
				return;
			}
			d += `${pen ? 'L' : 'M'}${sx(i).toFixed(1)},${sy(v).toFixed(1)}`;
			pen = true;
		});
		return d;
	};
	const every = $derived(xTickEvery ?? Math.max(1, Math.ceil(x.length / Math.max(2, Math.floor((width - padL - padR) / 70)))));
	// end labels, nudged apart so they never overlap
	const labels = $derived.by(() => {
		const ls = series
			.map((s) => {
				const i = s.values.findLastIndex((v) => v !== null);
				return i < 0 ? null : { name: s.name, color: s.color, y: sy(s.values[i] as number), x: sx(i) };
			})
			.filter((l) => l !== null)
			.sort((a, b) => a.y - b.y);
		for (let i = 1; i < ls.length; i++) if (ls[i].y - ls[i - 1].y < 14) ls[i].y = ls[i - 1].y + 14;
		return ls;
	});

	function move(e: PointerEvent) {
		const r = (e.currentTarget as SVGElement).getBoundingClientRect();
		const px = ((e.clientX - r.left) / r.width) * width;
		const i = Math.round(((px - padL) / (width - padL - padR)) * (x.length - 1));
		hover = Math.max(0, Math.min(x.length - 1, i));
	}
	function key(e: KeyboardEvent) {
		if (e.key === 'ArrowLeft') hover = Math.max(0, (hover ?? x.length) - 1);
		else if (e.key === 'ArrowRight') hover = Math.min(x.length - 1, (hover ?? -1) + 1);
		else if (e.key === 'Escape') hover = null;
	}
</script>

<div class="chart" bind:clientWidth={width}>
	<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions (arrow keys step through the data) -->
	<svg
		viewBox="0 0 {width} {height}"
		{height}
		role="img"
		aria-label={series.map((s) => s.name).join(', ')}
		tabindex="0"
		onpointermove={move}
		onpointerleave={() => (hover = null)}
		onkeydown={key}
	>
		{#each ticks as t}
			<line x1={padL} x2={width - padR} y1={sy(t)} y2={sy(t)} class="grid" />
			<text x={padL - 6} y={sy(t) + 4} text-anchor="end" class="tick">{format(t)}</text>
		{/each}
		{#each x as label, i}
			{#if i % every === 0}
				<text x={sx(i)} y={height - 6} text-anchor="middle" class="tick">{label}</text>
			{/if}
		{/each}
		{#if marker}
			<line x1={sx(marker.at)} x2={sx(marker.at)} y1={padT} y2={height - padB} class="marker" />
			<text x={sx(marker.at) + 4} y={padT + 10} class="tick">{marker.label}</text>
		{/if}
		{#each series as s}
			<path
				d={path(s.values)}
				fill="none"
				stroke={s.color ?? 'var(--muted)'}
				stroke-width={s.width ?? 2}
				stroke-dasharray={s.dashed ? '4 3' : undefined}
				stroke-linejoin="round"
			/>
		{/each}
		{#if endLabels}
			{#each labels as l}
				<text x={width - padR + 6} y={l.y + 4} class="end" fill={l.color ?? 'var(--muted)'}>{l.name}</text>
			{/each}
		{/if}
		{#if hover !== null}
			<line x1={sx(hover)} x2={sx(hover)} y1={padT} y2={height - padB} class="cross" />
			{#each series as s}
				{#if s.values[hover] !== null && s.values[hover] !== undefined}
					<circle cx={sx(hover)} cy={sy(s.values[hover] as number)} r="3.5" fill={s.color ?? 'var(--muted)'} />
				{/if}
			{/each}
		{/if}
	</svg>
	<div class="readout small" aria-live="polite">
		{#if hover !== null}
			<b>{x[hover]}</b>
			{#each series as s}
				{#if s.values[hover] !== null && s.values[hover] !== undefined}
					<span><i style="background:{s.color ?? 'var(--muted)'}"></i>{s.name}: {format(s.values[hover] as number)}</span>
				{/if}
			{/each}
		{:else}
			<span class="muted">Prejdite myšou alebo prstom po grafe pre presné hodnoty.</span>
		{/if}
	</div>
</div>

<style>
	.chart {
		width: 100%;
		min-width: 0;
	}
	svg {
		display: block;
		width: 100%;
		touch-action: pan-y;
	}
	.grid {
		stroke: var(--line);
	}
	.tick {
		font-size: 11px;
		fill: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.end {
		font-size: 11px;
	}
	.marker {
		stroke: var(--fg);
		stroke-dasharray: 3 3;
	}
	.cross {
		stroke: var(--muted);
	}
	.readout {
		min-height: 22px;
		display: flex;
		gap: 12px;
		flex-wrap: wrap;
	}
	.readout i {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 2px;
		margin-right: 4px;
	}
</style>
