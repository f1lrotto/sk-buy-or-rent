<script lang="ts">
	// Dependency-free SVG line chart. The readout above it is the legend at rest and the values under the pointer on hover;
	// `pin` keeps a crosshair at one point when nothing is hovered. Lines morph to new values and can draw in once.
	import { onMount, untrack } from 'svelte';
	import { Tween, prefersReducedMotion } from 'svelte/motion';
	import { calm, EASE } from '#lib/motion.ts';
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
		tick,
		height = 240,
		marker,
		pin,
		title,
		yMin,
		yMax,
		endLabels = true,
		xTickEvery,
		drawIn = false
	}: {
		x: string[];
		series: Series[];
		format?: (v: number) => string;
		/** Axis label format; defaults to `format`. */
		tick?: (v: number) => string;
		height?: number;
		marker?: Marker;
		/** Index shown in the readout and crosshair when nothing is hovered. */
		pin?: number;
		/** Readout title for an index; defaults to its x label. */
		title?: (i: number) => string;
		yMin?: number;
		yMax?: number;
		endLabels?: boolean;
		xTickEvery?: number;
		drawIn?: boolean;
	} = $props();

	let width = $state(640);
	let hover = $state<number | null>(null);
	const padL = 64;
	const padT = $derived(marker ? 26 : 10);
	const padB = 24;
	const padR = $derived(endLabels ? 112 : 8);

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

	// Everything that moves when the data changes is tweened together; a change of shape snaps.
	const target = $derived({
		v: series.map((s) => s.values.map((v) => v ?? NaN)),
		y0: Math.min(lo, ticks[0] ?? lo),
		y1: Math.max(hi, ticks.at(-1) ?? hi),
		m: marker?.at ?? 0
	});
	const shapeOf = (t: { v: number[][] }) => t.v.map((s) => s.length).join();
	const tw = new Tween(untrack(() => target), { duration: 450, easing: (t) => 1 - (1 - t) ** 4 });
	$effect(() => {
		const t = target;
		tw.set(t, { duration: shapeOf(t) === shapeOf(untrack(() => tw.current)) && !calm() ? 450 : 0 });
	});
	const cur = $derived(tw.current);

	const n = $derived(Math.max(1, x.length - 1));
	const sx = (i: number) => padL + (i / n) * (width - padL - padR);
	const sy = (v: number) => padT + (1 - (v - cur.y0) / (cur.y1 - cur.y0 || 1)) * (height - padT - padB);
	const path = (vals: number[]) => {
		let d = '';
		let pen = false;
		for (let i = 0; i < vals.length; i++) {
			const v = vals[i];
			if (!Number.isFinite(v)) {
				pen = false;
				continue;
			}
			d += `${pen ? 'L' : 'M'}${sx(i).toFixed(1)},${sy(v).toFixed(1)}`;
			pen = true;
		}
		return d;
	};
	const every = $derived(xTickEvery ?? Math.max(1, Math.ceil(x.length / Math.max(2, Math.floor((width - padL - padR) / 70)))));
	// end labels, nudged apart so they never overlap
	const labels = $derived.by(() => {
		const ls = series
			.map((s, k) => {
				const i = s.values.findLastIndex((v) => v !== null);
				return i < 0 ? null : { name: s.name, color: s.color, y: sy(cur.v[k][i]), x: sx(i) };
			})
			.filter((l) => l !== null)
			.sort((a, b) => a.y - b.y);
		for (let i = 1; i < ls.length; i++) if (ls[i].y - ls[i - 1].y < 14) ls[i].y = ls[i - 1].y + 14;
		return ls;
	});

	const at = $derived(hover ?? (pin !== undefined ? Math.min(pin, x.length - 1) : null));
	const isContext = (s: Series) => s.color === 'var(--context)';

	function move(e: PointerEvent) {
		const r = (e.currentTarget as SVGElement).getBoundingClientRect();
		const px = ((e.clientX - r.left) / r.width) * width;
		hover = Math.max(0, Math.min(x.length - 1, Math.round(((px - padL) / (width - padL - padR)) * n)));
	}
	function key(e: KeyboardEvent) {
		const stepKey = Math.max(1, Math.round(x.length / 30));
		const i = at ?? -1;
		if (e.key === 'ArrowLeft') hover = Math.max(0, (i < 0 ? x.length : i) - stepKey);
		else if (e.key === 'ArrowRight') hover = Math.min(x.length - 1, i + stepKey);
		else if (e.key === 'Escape') hover = null;
		else return;
		e.preventDefault();
	}

	// Lines draw in once, when the chart first scrolls into view.
	let svg: SVGSVGElement;
	let waiting = $state(false);
	onMount(() => {
		if (!drawIn || prefersReducedMotion.current) return;
		waiting = true;
		const io = new IntersectionObserver(
			([e]) => {
				if (!e.isIntersecting) return;
				io.disconnect();
				waiting = false;
				for (const p of svg.querySelectorAll<SVGPathElement>('path.line')) {
					const L = p.getTotalLength();
					p.animate([{ strokeDasharray: `${L} ${L}`, strokeDashoffset: L }, { strokeDasharray: `${L} ${L}`, strokeDashoffset: 0 }], { duration: 900, easing: EASE });
				}
				for (const m of svg.querySelectorAll('.after'))
					m.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 240, delay: 650, fill: 'backwards', easing: 'ease-out' });
			},
			{ threshold: 0.4 }
		);
		io.observe(svg);
		return () => io.disconnect();
	});
</script>

<div class="chart" bind:clientWidth={width}>
	<div class="readout" aria-live="polite">
		{#if at !== null}
			<span class="when">{title ? title(at) : x[at]}</span>
			{#each series as s}
				{#if s.values[at] !== null && s.values[at] !== undefined}
					<span class="s" class:ctx={isContext(s)}><i style:--c={s.color ?? 'var(--muted)'} class:dashed={s.dashed}></i>{s.name} <b>{format(s.values[at] as number)}</b></span>
				{/if}
			{/each}
		{:else}
			{#each series.filter((s) => !isContext(s)) as s}
				<span class="s"><i style:--c={s.color ?? 'var(--muted)'} class:dashed={s.dashed}></i>{s.name}</span>
			{/each}
		{/if}
	</div>
	<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions (arrow keys step through the data) -->
	<svg
		bind:this={svg}
		class:waiting
		viewBox="0 0 {width} {height}"
		{height}
		role="img"
		aria-label={series.map((s) => s.name).join(', ')}
		tabindex="0"
		onpointermove={move}
		onpointerleave={() => (hover = null)}
		onkeydown={key}
		onblur={() => (hover = null)}
	>
		{#each ticks as t}
			<line x1={padL} x2={width - padR} y1={sy(t)} y2={sy(t)} class="grid" class:zero={t === 0} />
			<text x={padL - 10} y={sy(t) + 4} text-anchor="end" class="tick">{(tick ?? format)(t)}</text>
		{/each}
		{#each x as label, i}
			{#if i % every === 0}
				<text x={sx(i)} y={height - 6} text-anchor="middle" class="tick">{label}</text>
			{/if}
		{/each}
		{#if at !== null}
			<line x1={sx(at)} x2={sx(at)} y1={padT} y2={height - padB} class="cross after" />
		{/if}
		{#if marker}
			{@const mx = sx(cur.m)}
			<line x1={mx} x2={mx} y1={padT - 8} y2={height - padB} class="marker after" />
			<text x={mx > width - padR - 160 ? mx - 6 : mx + 6} y={padT - 10} text-anchor={mx > width - padR - 160 ? 'end' : 'start'} class="mlabel after"
				>{marker.label}</text
			>
		{/if}
		{#each series as s, k}
			<path
				class="line"
				d={path(cur.v[k] ?? [])}
				fill="none"
				stroke={s.color ?? 'var(--muted)'}
				stroke-width={s.width ?? 2}
				stroke-dasharray={s.dashed ? '4 3' : undefined}
				stroke-linejoin="round"
				stroke-linecap="round"
			/>
		{/each}
		{#if endLabels}
			{#each labels as l}
				<text x={width - padR + 8} y={l.y + 4} class="end" fill={l.color ?? 'var(--muted)'}>{l.name}</text>
			{/each}
		{/if}
		{#if at !== null}
			{#each series as s, k}
				{@const v = cur.v[k]?.[at]}
				{#if v !== undefined && Number.isFinite(v) && !isContext(s)}
					<circle cx={sx(at)} cy={sy(v)} r="4" fill={s.color ?? 'var(--muted)'} class="dot after" />
				{/if}
			{/each}
		{/if}
	</svg>
</div>

<style>
	.chart {
		width: 100%;
		min-width: 0;
		position: relative;
	}
	.readout {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 4px 18px;
		min-height: 22px;
		margin-bottom: 6px;
		font-size: 13px;
		color: var(--fg-2);
	}
	.readout .when {
		color: var(--muted);
		min-width: 120px;
	}
	.readout .s {
		display: inline-flex;
		align-items: baseline;
		gap: 6px;
	}
	.readout .s.ctx {
		color: var(--muted);
	}
	.readout i {
		width: 10px;
		height: 2px;
		border-radius: 1px;
		align-self: center;
		background: var(--c);
	}
	.readout i.dashed {
		background: repeating-linear-gradient(90deg, var(--c) 0 3px, transparent 3px 5px);
	}
	.readout b {
		font-weight: 500;
		color: var(--fg);
		font-variant-numeric: tabular-nums;
	}
	svg {
		display: block;
		width: 100%;
		overflow: visible;
		touch-action: pan-y;
	}
	svg:focus-visible {
		outline-offset: 6px;
	}
	.grid {
		stroke: var(--line-2);
	}
	.grid.zero {
		stroke: var(--line);
	}
	.tick {
		font-size: 11px;
		fill: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.end {
		font-size: 11px;
		font-weight: 500;
	}
	.marker {
		stroke: var(--fg);
		stroke-dasharray: 2 3;
		opacity: 0.45;
	}
	.mlabel {
		font-size: 11px;
		font-weight: 500;
		fill: var(--fg-2);
	}
	.cross {
		stroke: var(--faint);
	}
	.dot {
		stroke: var(--bg);
		stroke-width: 2;
	}
	.waiting :global(path.line),
	.waiting .after {
		opacity: 0;
	}
</style>
