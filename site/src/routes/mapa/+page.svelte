<script lang="ts">
	import { goto } from '$app/navigation';
	import { KRAJ_SHORT, SOURCE_SHORT, type Place } from '#lib/data.ts';
	import { eur, num, pct, period } from '#lib/format.ts';
	import LineChart from '#lib/components/LineChart.svelte';
	import Roll from '#lib/components/Roll.svelte';
	import Segmented from '#lib/components/Segmented.svelte';

	let { data } = $props();
	const { latest, history: h, areas } = data;
	const places = latest.places;
	const kraje = places.filter((p) => p.level === 'kraj');
	const cities = places.filter((p) => p.level === 'mesto' && areas.points[p.id]);

	type Layer = 'years' | 'ptr' | 'rent';
	const LAYERS: Record<Layer, { short: string; label: string; value: (p: Place) => number; fmt: (v: number) => string; note: string }> = {
		years: {
			short: 'Roky mzdy na byt',
			label: 'Roky hrubej mzdy na byt 60 m²',
			value: (p) => (p.price.value * 60) / (12 * p.wage.value),
			fmt: (v) => `${num(v, 1)} r.`,
			note: 'Cena bytu 60 m² delená ročnou priemernou hrubou mzdou v kraji (mestá používajú mzdu kraja).'
		},
		ptr: {
			short: 'Cena k nájmu',
			label: 'Pomer ceny k ročnému nájmu',
			value: (p) => p.price.value / (12 * p.rent.value),
			fmt: (v) => num(v, 1),
			note: 'Koľko rokov nájmu stojí byt. Hrubý výnos z prenájmu je 100 delené týmto číslom.'
		},
		rent: {
			short: 'Nájomné za m²',
			label: 'Ponukové nájomné za m²',
			value: (p) => p.rent.value,
			fmt: (v) => `${num(v, 2)} €`,
			note: 'Priemer posledných 3 mesiacov z inzerátov (realitymap.sk), bez energií.'
		}
	};
	let layer = $state<Layer>('years');
	let selected = $state('ZA');
	let hoverId = $state<string | null>(null);

	const L = $derived(LAYERS[layer]);
	const vals = $derived([...kraje, ...cities].map((p) => L.value(p)).sort((a, b) => a - b));
	const breaks = $derived([0.2, 0.4, 0.6, 0.8].map((q) => vals[Math.floor(q * (vals.length - 1))]));
	// a neutral ramp: lighter is cheaper, darker is less affordable
	const RAMP = [10, 24, 42, 62, 86].map((k) => `color-mix(in oklab, var(--fg) ${k}%, var(--bg))`);
	const color = (v: number) => RAMP[breaks.filter((b) => v > b).length];
	const krajById = new Map(kraje.map((k) => [k.kraj, k]));
	const shown = $derived(places.find((p) => p.id === hoverId) ?? krajById.get(selected)!);

	// ---------- history ----------
	const K = h.kraje;
	const krajIdx = (k: string) => K.indexOf(k) + 1;
	// annual mean wage per kraj from single quarters
	const wageYear = new Map<string, number[][]>();
	for (const row of h.wage_quarterly) {
		const y = String(row[0]).slice(0, 4);
		if (!wageYear.has(y)) wageYear.set(y, K.map(() => []));
		K.forEach((_, i) => row[i + 1] !== null && wageYear.get(y)![i].push(row[i + 1] as number));
	}
	const wageMean = (y: string, i: number) => {
		const a = wageYear.get(y)?.[i];
		return a?.length ? a.reduce((s, v) => s + v, 0) / a.length : null;
	};
	const yearsRows = h.nbs_annual
		.map((r) => ({ y: String(r[0]), vals: K.map((_, i) => r[i + 1] as number) }))
		.filter((r) => wageMean(r.y, 0) !== null);
	const yearsX = yearsRows.map((r) => r.y);
	const yearsSeries = $derived(
		K.map((k, i) => ({
			name: KRAJ_SHORT[k],
			values: yearsRows.map((r) => {
				const w = wageMean(r.y, i);
				return w ? (r.vals[i] * 60) / (12 * w) : null;
			}),
			color: k === selected ? 'var(--own)' : 'var(--context)',
			width: k === selected ? 2.5 : 1.5
		})).sort((a, b) => (a.color === 'var(--own)' ? 1 : 0) - (b.color === 'var(--own)' ? 1 : 0))
	);

	const rentX = h.rm_rent_monthly.map((r) => String(r[0]));
	const rentSeries = $derived(
		K.map((k) => ({
			name: KRAJ_SHORT[k],
			values: h.rm_rent_monthly.map((r) => r[krajIdx(k)] as number),
			color: k === selected ? 'var(--own)' : 'var(--context)',
			width: k === selected ? 2.5 : 1.5
		})).sort((a, b) => (a.color === 'var(--own)' ? 1 : 0) - (b.color === 'var(--own)' ? 1 : 0))
	);
	// asking rents (mean of kraje) vs rents actually paid (Eurostat CP041), both indexed to the first month
	const cp = new Map(h.cp041_monthly);
	const askMean = h.rm_rent_monthly.map((r) => K.reduce((s, _, i) => s + (r[i + 1] as number), 0) / K.length);
	const paid = rentX.map((p) => cp.get(p) ?? null);
	const paid0 = paid.find((v) => v !== null)!;
	const idxSeries = [
		{ name: 'Ponukové', values: askMean.map((v) => (100 * v) / askMean[0]), color: 'var(--rent)' },
		{ name: 'Platené', values: paid.map((v) => (v === null ? null : (100 * v) / paid0)), color: 'var(--own)' }
	];
	const nbsQ = h.nbs_quarterly.at(-1)!;
	const suQ = h.su_index_quarterly.at(-1)!;
</script>

<svelte:head><title>Mapa dostupnosti bývania a vývoj cien | Kúpiť či prenajať</title></svelte:head>

<h1>Dostupnosť bývania podľa krajov a miest</h1>
<div class="layers">
	<Segmented label="Vrstva mapy" value={layer} options={Object.entries(LAYERS).map(([k, l]) => [k as Layer, l.short])} onchange={(v) => (layer = v)} />
	<span class="muted">{L.label}</span>
</div>

<div class="mapwrap">
	<svg viewBox={areas.viewBox} role="img" aria-label="Mapa Slovenska: {L.label}">
		{#each areas.kraje as k}
			{@const p = krajById.get(k.id)!}
			<path
				d={k.d}
				style:fill={color(L.value(p))}
				class="kraj"
				class:sel={k.id === selected}
				role="button"
				tabindex="0"
				aria-label="{p.name}: {L.fmt(L.value(p))}"
				onpointerenter={() => (hoverId = p.id)}
				onpointerleave={() => (hoverId = null)}
				onclick={() => (selected = k.id)}
				onkeydown={(e) => e.key === 'Enter' && (selected = k.id)}
			/>
		{/each}
		{#each areas.okresy as o}
			<path d={o.d} class="okres" />
		{/each}
		{#each cities as c}
			{@const [cx, cy] = areas.points[c.id]}
			<circle
				{cx}
				{cy}
				r={c.id === 'bratislava' || c.id === 'kosice' ? 9 : 6}
				style:fill={color(L.value(c))}
				class="city"
				role="button"
				tabindex="0"
				aria-label="{c.name}: {L.fmt(L.value(c))}"
				onpointerenter={() => (hoverId = c.id)}
				onpointerleave={() => (hoverId = null)}
				onclick={() => goto(`/?m=${c.id}`)}
				onkeydown={(e) => e.key === 'Enter' && goto(`/?m=${c.id}`)}
			/>
		{/each}
	</svg>
	<div class="info">
		<p class="name">{shown.name}</p>
		<p class="value"><Roll text={L.fmt(L.value(shown))} /></p>
		<p class="cap">
			Cena {eur(shown.price.value)}/m² ({SOURCE_SHORT[shown.price.source]}, {period(shown.price.period)}), nájom {num(shown.rent.value, 2)} €/m², mzda
			{eur(shown.wage.value)} ({period(shown.wage.period)}).
		</p>
		<p class="cap"><a href="/?m={shown.id}">Porovnať kúpu a nájom tu</a></p>
	</div>
</div>
<div class="legend">
	{#each RAMP as c, i}
		<span><i style="background:{c}"></i>{i === 0 ? `do ${L.fmt(breaks[0])}` : i === RAMP.length - 1 ? `nad ${L.fmt(breaks[3])}` : `${L.fmt(breaks[i - 1])} – ${L.fmt(breaks[i])}`}</span>
	{/each}
</div>
<p class="cap">{L.note} Kliknutím na kraj ho zvýrazníte v grafoch, kliknutím na mesto otvoríte kalkulačku. Hranice: {areas.source}.</p>

<h2>Koľko rokov práce stojí byt</h2>
<p class="cap">
	Byt 60 m² v rokoch hrubej priemernej mzdy, {yearsX[0]}–{yearsX.at(-1)}. Zvýraznený je {KRAJ_SHORT[selected]} kraj. Zdroj: NBS (ponukové ceny), ŠÚ SR (mzdy).
</p>
<div class="gap"><LineChart x={yearsX} series={yearsSeries} format={(v) => `${num(v, 1)} r.`} tick={(v) => `${num(v, 0)} r.`} xTickEvery={4} /></div>

<h2>Ponukové nájomné za m²</h2>
<p class="cap">Mesačne od {period(rentX[0])}, €/m² bez energií. Zdroj: realitymap.sk.</p>
<div class="gap"><LineChart x={rentX.map(period)} series={rentSeries} format={(v) => `${num(v, 2)} €`} tick={(v) => `${num(v, 1)} €`} xTickEvery={6} /></div>

<h2>Inzeráty verzus skutočne platené nájmy</h2>
<p class="cap">
	Index ({period(rentX[0])} = 100). Ponukové: priemer krajov z realitymap.sk. Skutočne platené: Eurostat HICP CP041 za celé Slovensko.
	Za posledný rok sa platené nájmy zvýšili o {pct(latest.defaults.paid_rent_yoy, 1)}.
</p>
<div class="gap"><LineChart x={rentX.map(period)} series={idxSeries} format={(v) => num(v, 1)} tick={(v) => num(v, 0)} xTickEvery={6} endLabels={false} /></div>

<h2>Ponukové verzus realizačné ceny</h2>
<p class="cap">
	Medziročná zmena: ponukové ceny NBS ({nbsQ[0]}) a index cien skutočných predajov z katastra ŠÚ SR ({suQ[0]}). Obdobia sa môžu líšiť o štvrťrok.
</p>
<div class="scroll gap">
	<table>
		<thead><tr><th>Kraj</th><th class="r">Ponukové (NBS)</th><th class="r">Realizačné (ŠÚ SR)</th></tr></thead>
		<tbody>
			{#each kraje as k}
				<tr>
					<td>{k.name}</td>
					<td class="r">{pct(k.growth.nbs_yoy, 1, true)}</td>
					<td class="r">{k.growth.su_yoy === undefined || k.growth.su_yoy === null ? '–' : pct(k.growth.su_yoy, 1, true)}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.layers {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px 16px;
		margin: 20px 0 16px;
		font-size: 13px;
	}
	.mapwrap {
		display: grid;
		grid-template-columns: minmax(0, 3fr) minmax(0, 1fr);
		gap: 32px;
		align-items: start;
	}
	@media (max-width: 720px) {
		.mapwrap {
			grid-template-columns: minmax(0, 1fr);
			gap: 16px;
		}
	}
	svg {
		width: 100%;
		height: auto;
		display: block;
	}
	.kraj,
	.city {
		cursor: pointer;
		transition: fill 300ms var(--ease);
	}
	.kraj {
		stroke: var(--bg);
		stroke-width: 2;
	}
	.kraj.sel {
		stroke: var(--own);
		stroke-width: 3;
		paint-order: stroke;
	}
	.okres {
		fill: none;
		stroke: var(--bg);
		stroke-width: 0.6;
		stroke-opacity: 0.5;
		pointer-events: none;
	}
	.city {
		stroke: var(--bg);
		stroke-width: 2;
	}
	@media (hover: hover) {
		.city:hover,
		.kraj:hover {
			filter: brightness(0.9);
		}
	}
	svg :focus-visible {
		outline: none;
		stroke: var(--fg);
	}
	.info {
		padding-top: 4px;
	}
	.info .name {
		margin: 0;
		font-weight: 500;
	}
	.info .value {
		margin: 2px 0 0;
		font-size: 32px;
		line-height: 1.2;
		font-weight: 600;
		letter-spacing: -0.03em;
		font-variant-numeric: tabular-nums;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 6px 16px;
		margin-top: 12px;
		font-size: 12px;
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.legend span {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.legend i {
		width: 10px;
		height: 10px;
		border-radius: 2px;
	}
	.gap {
		margin-top: 20px;
	}
</style>
