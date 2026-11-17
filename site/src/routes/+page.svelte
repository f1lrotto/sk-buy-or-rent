<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { replaceState } from '$app/navigation';
	import { DEFAULTS, DEFAULT_RULES, flips, sensitivity, simulate, type FlipKey, type Inputs, type RefixPath } from '#lib/calc.ts';
	import { LEVEL_LABEL, SOURCE_SHORT, type Place } from '#lib/data.ts';
	import { eur, inPlace, months, monthsAfter, num, pct, period } from '#lib/format.ts';
	import { readOverrides, writeOverrides } from '#lib/state.ts';
	import Field from '#lib/components/Field.svelte';
	import LineChart from '#lib/components/LineChart.svelte';

	let { data } = $props();
	const latest = data.latest;
	const rulesCfg = data.rules;
	const rules = {
		...DEFAULT_RULES,
		bonusShare: rulesCfg.young_buyer_bonus.share_of_interest,
		bonusMaxYear: rulesCfg.young_buyer_bonus.max_per_year,
		bonusYears: rulesCfg.young_buyer_bonus.years,
		gainTax: rulesCfg.income_tax.bands[0][1] + rulesCfg.income_tax.health_insurance_other_income,
		flatHoldingYears: rulesCfg.flat_sale_exemption.holding_years
	};
	const places = latest.places;
	const byId = new Map(places.map((p) => [p.id, p]));
	const groups: [string, Place[]][] = [
		['Kraje', places.filter((p) => p.level === 'kraj')],
		['Mestá', places.filter((p) => p.level === 'mesto')],
		['Mestské časti Bratislavy a Košíc', places.filter((p) => p.level === 'mestska-cast')]
	];

	let placeId = $state(byId.has('bratislava') ? 'bratislava' : places[0].id);
	let o = $state<Partial<Inputs>>({});
	const place = $derived(byId.get(placeId) ?? places[0]);

	const base = $derived<Inputs>({
		...DEFAULTS,
		priceM2: place.price.value,
		rentM2: place.rent.value,
		rate: latest.defaults.rate / 100,
		rentGrowth: latest.defaults.rent_growth
	});
	const inp = $derived<Inputs>({ ...base, ...o });

	onMount(() => {
		const q = new URLSearchParams(location.search);
		const m = q.get('m');
		if (m && byId.has(m)) placeId = m;
		o = readOverrides(q);
	});
	let mounted = false;
	$effect(() => {
		const url = writeOverrides(o, placeId !== 'bratislava' ? { m: placeId } : {});
		if (!mounted) {
			mounted = true;
			return;
		}
		untrack(() => replaceState(location.pathname + url, {}));
	});

	function choose(id: string) {
		placeId = id;
		const { priceM2, rentM2, ...rest } = o;
		o = rest; // a new place brings its own price and rent
	}
	function set<K extends keyof Inputs>(k: K, v: Inputs[K]) {
		o = { ...o, [k]: v };
	}
	function reset(k: keyof Inputs) {
		const { [k]: _, ...rest } = o;
		o = rest;
	}

	const res = $derived(simulate(inp, rules));
	const stayM = $derived(Math.round(12 * inp.stay));
	const winsInStay = $derived(res.breakEven !== null && res.breakEven <= stayM);
	const fl = $derived(flips(inp, rules));
	const sens = $derived(sensitivity(inp, rules));

	// break-even month across mortgage rates, for the rate chart
	const rateGrid = $derived(Array.from({ length: 33 }, (_, i) => i * 0.0025));
	const beByRate = $derived(rateGrid.map((r) => simulate({ ...inp, rate: r }, rules).breakEven));

	const ecbRate = latest.defaults.rate / 100;
	const y10 = $derived(res.months[Math.min(res.months.length - 1, 12 * 9)]);
	const y1 = $derived(res.months[0]);

	const yearsWord = (n: number) => (n === 1 ? 'rok' : n >= 2 && n <= 4 ? 'roky' : 'rokov');
	function flipSentence(): string {
		const stay = `Ak tu budete bývať ${num(inp.stay)} ${yearsWord(inp.stay)}`;
		if (fl.quoted === 'priceGrowth' && fl.priceGrowth !== null) {
			const v = fl.priceGrowth;
			if (winsInStay)
				return v < 0
					? `${stay}, nájom vyhrá, iba ak ceny bytov budú klesať rýchlejšie ako ${pct(-v)} ročne.`
					: `${stay}, nájom vyhrá, ak ceny bytov porastú pomalšie ako ${pct(v)} ročne.`;
			return v < 0
				? `Kúpa by vyhrala, ak by ceny bytov klesali pomalšie ako ${pct(-v)} ročne.`
				: `Kúpa by vyhrala, ak by ceny bytov rástli rýchlejšie ako ${pct(v)} ročne.`;
		}
		if (fl.quoted === 'investReturn' && fl.investReturn !== null) {
			return winsInStay
				? `${stay}, nájom vyhrá, iba ak ušetrené peniaze vynesú viac ako ${pct(fl.investReturn)} ročne.`
				: `Kúpa by vyhrala, ak by investície vynášali menej ako ${pct(fl.investReturn)} ročne.`;
		}
		return 'Výsledok sa v rozumnom rozsahu rastu cien a výnosov nemení.';
	}

	const SENS_LABEL: Record<FlipKey, string> = {
		priceGrowth: 'Rast cien bytov',
		rentGrowth: 'Rast nájomného',
		investReturn: 'Výnos investícií',
		rate: 'Úroková sadzba'
	};
	const beText = (b: number | null) => (b === null ? `nad ${inp.term} r.` : b <= 24 ? `${b} mes.` : `${num(b / 12, 1)} r.`);
	const src = (key: string, per?: string) => `${SOURCE_SHORT[key] ?? key}${per ? `, ${period(per)}` : ''}`;
</script>

<svelte:head>
	<title>Kúpiť či prenajať byt {inPlace(place)}? | Kalkulačka</title>
</svelte:head>

<h1>Kúpiť či prenajať byt?</h1>
<div class="pick">
	<label for="place" class="small muted">Miesto</label>
	<select id="place" value={placeId} onchange={(e) => choose((e.currentTarget as HTMLSelectElement).value)}>
		{#each groups as [label, ps]}
			<optgroup {label}>
				{#each ps as p}
					<option value={p.id}>{p.name}{p.quality === 'indicative' ? ' (orientačné)' : ''}</option>
				{/each}
			</optgroup>
		{/each}
	</select>
	<span class="chip">{LEVEL_LABEL[place.level]}</span>
	{#if place.quality === 'indicative'}
		<span class="chip warn" title="Menej ako 50 inzerátov na predaj alebo 30 na prenájom v niektorom z posledných 3 mesiacov">Orientačné, málo inzerátov</span>
	{/if}
</div>

<section class="answer" aria-live="polite">
	<p class="lead">
		{#if winsInStay}
			{inPlace(place)[0].toUpperCase() + inPlace(place).slice(1)} sa kúpa bytu s rozlohou {num(inp.area)} m² oplatí viac ako nájom
			po <strong>{monthsAfter(res.breakEven!)}</strong>.
		{:else if res.breakEven !== null}
			{inPlace(place)[0].toUpperCase() + inPlace(place).slice(1)} kúpa bytu s rozlohou {num(inp.area)} m² dobehne nájom až po
			<strong>{monthsAfter(res.breakEven)}</strong>, teda neskôr, ako tu plánujete bývať ({num(inp.stay)} {yearsWord(inp.stay)}).
		{:else}
			{inPlace(place)[0].toUpperCase() + inPlace(place).slice(1)} sa kúpa bytu s rozlohou {num(inp.area)} m² neoplatí viac ako nájom
			počas celej doby splácania.
		{/if}
	</p>
	<p class="flip">{flipSentence()}</p>
	<p class="small muted">
		Mesačne: hypotéka {eur(res.firstPayment)} + ďalšie náklady {eur(res.ownerCost0 - res.firstPayment)} oproti nájmu {eur(res.rent0)}.
		Cena bytu {eur(res.price)}, úver {eur(res.loan)}.
	</p>

	<div class="rate">
		<label for="rate" class="small">Úroková sadzba hypotéky: <strong class="num">{pct(inp.rate, 2)}</strong></label>
		<input
			id="rate"
			type="range"
			min={Math.max(0, ecbRate - 0.02)}
			max={ecbRate + 0.03}
			step="0.0005"
			value={inp.rate}
			oninput={(e) => set('rate', +(e.currentTarget as HTMLInputElement).value)}
		/>
		<div class="small muted">
			Priemer nových hypoték na Slovensku: {pct(ecbRate, 2)} (ECB, {period(latest.defaults.rate_period)}).
			{#if fl.rate !== null}
				{winsInStay ? 'Kúpa prestane vyhrávať' : 'Kúpa začne vyhrávať'} pri sadzbe {pct(fl.rate, 2)}.
			{/if}
		</div>
	</div>
</section>

<div class="grid">
	<section class="inputs">
		<h2>Byt</h2>
		<div class="fields">
			<Field label="Cena za m²" unit="€/m²" value={inp.priceM2} set={(v) => set('priceM2', v)} step={10} edited={'priceM2' in o} reset={() => reset('priceM2')}>
				{#snippet source()}
					{src(place.price.source, place.price.period)}{place.price.note ? `, ${place.price.note}` : ''}
					{#each place.price.checks ?? [] as c}
						<br />Pre porovnanie {src(c.source)}: {eur(c.value)}/m²
					{/each}
				{/snippet}
			</Field>
			<Field label="Nájomné za m²" unit="€/m² mesačne" value={inp.rentM2} set={(v) => set('rentM2', v)} step={0.1} edited={'rentM2' in o} reset={() => reset('rentM2')}>
				{#snippet source()}
					{src(place.rent.source, place.rent.period)}, ponukové{place.rent.n ? `, ${num(place.rent.n)} inzerátov` : ''}
					{#each place.rent.checks ?? [] as c}
						<br />Pre porovnanie {src(c.source, c.period)}: {c.per === 'byt' ? `${eur(c.value)} za byt` : `${num(c.value, 2)} €/m²`}{c.note ? ` (${c.note})` : ''}
					{/each}
				{/snippet}
			</Field>
			<Field label="Rozloha bytu" unit="m²" value={inp.area} set={(v) => set('area', v)} edited={'area' in o} reset={() => reset('area')}>
				{#snippet source()}Typický 2- až 3-izbový byt{/snippet}
			</Field>
			<Field label="Plánovaná doba bývania" unit="rokov" value={inp.stay} set={(v) => set('stay', v)} edited={'stay' in o} reset={() => reset('stay')}>
				{#snippet source()}Obdobie pre odpoveď a bod zlomu{/snippet}
			</Field>
		</div>

		<h2>Hypotéka</h2>
		<div class="fields">
			<Field label="Vlastné zdroje" unit="%" value={inp.down * 100} set={(v) => set('down', v / 100)} edited={'down' in o} reset={() => reset('down')}>
				{#snippet source()}Banky bežne požadujú 20 % (LTV 80 %){/snippet}
			</Field>
			<Field label="Doba splácania" unit="rokov" value={inp.term} set={(v) => set('term', v)} edited={'term' in o} reset={() => reset('term')}>
				{#snippet source()}NBS limit 30 rokov{/snippet}
			</Field>
			<Field label="Úroková sadzba" unit="%" value={inp.rate * 100} step={0.01} set={(v) => set('rate', v / 100)} edited={'rate' in o} reset={() => reset('rate')}>
				{#snippet source()}{src('ecb', latest.defaults.rate_period)}, priemer nových úverov{/snippet}
			</Field>
			<div class="field">
				<label for="fix" class="small">Fixácia</label>
				<select id="fix" value={String(inp.fixation)} onchange={(e) => set('fixation', +(e.currentTarget as HTMLSelectElement).value)}>
					{#each [1, 3, 5, 10] as f}<option value={String(f)}>{f} {f === 1 ? 'rok' : f < 5 ? 'roky' : 'rokov'}</option>{/each}
				</select>
			</div>
			<div class="field wide">
				<label for="refix" class="small">Sadzba pri ďalších fixáciách</label>
				<select id="refix" value={inp.refix} onchange={(e) => set('refix', (e.currentTarget as HTMLSelectElement).value as RefixPath)}>
					<option value="same">Rovnaká ako dnes</option>
					<option value="up1">O 1 p. b. vyššia</option>
					<option value="down1">O 1 p. b. nižšia</option>
					<option value="custom">Vlastná pre každú fixáciu</option>
				</select>
				{#if inp.refix === 'custom'}
					<div class="refix">
						{#each Array.from({ length: Math.max(0, Math.ceil(inp.term / inp.fixation) - 1) }) as _, k}
							<label class="small">
								od {k * inp.fixation + inp.fixation + 1}. roka
								<input
									type="number"
									step="0.1"
									value={+(((inp.refixRates[k] ?? inp.refixRates.at(-1) ?? inp.rate) * 100).toFixed(2))}
									onchange={(e) => {
										const rr = [...inp.refixRates];
										while (rr.length <= k) rr.push(rr.at(-1) ?? inp.rate);
										rr[k] = +(e.currentTarget as HTMLInputElement).value / 100;
										set('refixRates', rr);
									}}
								/> %
							</label>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<h2>Predpoklady do budúcnosti</h2>
		<div class="fields">
			<Field label="Rast cien bytov" unit="% ročne" step={0.1} value={inp.priceGrowth * 100} set={(v) => set('priceGrowth', v / 100)} edited={'priceGrowth' in o} reset={() => reset('priceGrowth')}>
				{#snippet source()}
					Predpoklad. NBS: {pct(place.growth.nbs_cagr)} ročne od {place.growth.from} ({LEVEL_LABEL.kraj}){place.growth.su_yoy !== undefined && place.growth.su_yoy !== null ? `, realizačné ceny za rok ${pct(place.growth.su_yoy, 1, true)} (ŠÚ SR)` : ''}
				{/snippet}
			</Field>
			<Field label="Rast nájomného" unit="% ročne" step={0.1} value={inp.rentGrowth * 100} set={(v) => set('rentGrowth', v / 100)} edited={'rentGrowth' in o} reset={() => reset('rentGrowth')}>
				{#snippet source()}Priemer 10 rokov, {src('cp041', latest.defaults.rent_growth_period)}, skutočne platené nájmy{/snippet}
			</Field>
			<Field label="Výnos investícií" unit="% ročne" step={0.1} value={inp.investReturn * 100} set={(v) => set('investReturn', v / 100)} edited={'investReturn' in o} reset={() => reset('investReturn')}>
				{#snippet source()}
					Predpoklad.
					<button class="link" onclick={() => set('investReturn', 0.025)}>Termínovaný vklad 2,5 %</button>,
					<button class="link" onclick={() => set('investReturn', 0.07)}>globálny akciový index 7 %</button>
				{/snippet}
			</Field>
			<Field label="Inflácia nákladov" unit="% ročne" step={0.1} value={inp.inflation * 100} set={(v) => set('inflation', v / 100)} edited={'inflation' in o} reset={() => reset('inflation')}>
				{#snippet source()}Predpoklad; pre údržbu, daň a poistenie{/snippet}
			</Field>
		</div>

		<details>
			<summary><h2>Náklady vlastníka</h2></summary>
			<div class="fields">
				<Field label="Údržba a fond opráv" unit="€/m² mesačne" step={0.1} value={inp.maintenance} set={(v) => set('maintenance', v)} edited={'maintenance' in o} reset={() => reset('maintenance')}>
					{#snippet source()}Predpoklad{/snippet}
				</Field>
				<Field label="Daň z nehnuteľnosti" unit="€/m² ročne" step={0.1} value={inp.propertyTax} set={(v) => set('propertyTax', v)} edited={'propertyTax' in o} reset={() => reset('propertyTax')}>
					{#snippet source()}Líši sa podľa obce; predpoklad{/snippet}
				</Field>
				<Field label="Poistenie" unit="€ ročne" value={inp.insurance} set={(v) => set('insurance', v)} edited={'insurance' in o} reset={() => reset('insurance')}>
					{#snippet source()}Predpoklad{/snippet}
				</Field>
				<Field label="Náklady na kúpu" unit="% ceny" step={0.1} value={inp.buyCost * 100} set={(v) => set('buyCost', v / 100)} edited={'buyCost' in o} reset={() => reset('buyCost')}>
					{#snippet source()}Poplatky, znalec, kataster; predpoklad{/snippet}
				</Field>
				<Field label="Náklady na predaj" unit="% hodnoty" step={0.1} value={inp.sellCost * 100} set={(v) => set('sellCost', v / 100)} edited={'sellCost' in o} reset={() => reset('sellCost')}>
					{#snippet source()}Realitná kancelária a poplatky; predpoklad{/snippet}
				</Field>
			</div>
		</details>

		<h2>Dane a štátna podpora</h2>
		<div class="toggles">
			<label>
				<input type="checkbox" checked={inp.youngBonus} onchange={(e) => set('youngBonus', (e.currentTarget as HTMLInputElement).checked)} />
				Daňový bonus pre mladých na úroky ({pct(rules.bonusShare, 0)} úrokov, najviac {eur(rules.bonusMaxYear)} ročne počas {rules.bonusYears} rokov)
				<span class="small muted">Do {rulesCfg.young_buyer_bonus.max_age} rokov, príjem do {eur(rulesCfg.young_buyer_bonus.income_limit_monthly)} mesačne. {rulesCfg.young_buyer_bonus.source}.</span>
				{#if inp.youngBonus}<span class="small">Bonus spolu: <strong>{eur(res.bonusTotal)}</strong>.</span>{/if}
			</label>
			<label>
				<input type="checkbox" checked={inp.investTax} onchange={(e) => set('investTax', (e.currentTarget as HTMLInputElement).checked)} />
				Zdaniť zisk z investícií ({pct(rules.gainTax, 0)} vrátane zdravotného poistenia)
				<span class="small muted">Vypnuté: ETF na burze držané viac ako rok sú oslobodené ({rulesCfg.securities_exemption.source}).</span>
			</label>
			<label>
				<input type="checkbox" checked={inp.saleTax} onchange={(e) => set('saleTax', (e.currentTarget as HTMLInputElement).checked)} />
				Zdaniť zisk z predaja bytu skôr ako po {rules.flatHoldingYears} rokoch
				<span class="small muted">{rulesCfg.flat_sale_exemption.source}.</span>
			</label>
		</div>
	</section>

	<section class="results">
		<h2>Mesačné náklady</h2>
		<table>
			<thead><tr><th></th><th class="r">1. rok</th><th class="r">10. rok</th></tr></thead>
			<tbody>
				<tr><td>Splátka hypotéky</td><td class="r">{eur(y1.payment)}</td><td class="r">{eur(y10.payment)}</td></tr>
				<tr>
					<td>Údržba, daň, poistenie</td>
					<td class="r">{eur(y1.ownerCost - y1.payment)}</td>
					<td class="r">{eur(y10.ownerCost - y10.payment)}</td>
				</tr>
				<tr><td><strong>Vlastník spolu</strong></td><td class="r"><strong>{eur(y1.ownerCost)}</strong></td><td class="r"><strong>{eur(y10.ownerCost)}</strong></td></tr>
				<tr><td><strong>Nájomca</strong></td><td class="r"><strong>{eur(y1.rent)}</strong></td><td class="r"><strong>{eur(y10.rent)}</strong></td></tr>
				<tr>
					<td>Z toho úroky vlastníka</td><td class="r">{eur(y1.interest)}</td><td class="r">{eur(y10.interest)}</td>
				</tr>
			</tbody>
		</table>
		<p class="small muted">Kto platí mesačne menej, rozdiel investuje s výnosom {pct(inp.investReturn)} ročne.</p>

		<h2>Čistý majetok vlastníka a nájomcu</h2>
		<LineChart
			x={[0, ...res.months.map((m) => m.m)].map((m) => (m % 12 === 0 ? `${m / 12}. r.` : `${num(m / 12, 1)} r.`))}
			series={[
				{ name: 'Vlastník', values: [res.price * (1 - inp.sellCost) - res.loan, ...res.months.map((m) => m.owner)], color: 'var(--own)' },
				{ name: 'Nájomca', values: [res.price * (inp.down + inp.buyCost), ...res.months.map((m) => m.renter)], color: 'var(--rent)' }
			]}
			format={(v) => (Math.abs(v) >= 1000 ? `${num(v / 1000)} tis. €` : eur(v))}
			marker={res.breakEven ? { at: res.breakEven, label: `zlom: ${months(res.breakEven)}` } : undefined}
			xTickEvery={60}
		/>
		<p class="small muted">
			Vlastník: hodnota bytu po nákladoch na predaj (a dani pri predaji do {rules.flatHoldingYears} rokov) mínus zostatok úveru plus investované úspory.
			Nájomca: investované vlastné zdroje a mesačné úspory.
		</p>

		<h2>Čo rozhoduje</h2>
		<p class="small muted">Mesiac, keď kúpa dobehne nájom, ak sa jeden predpoklad zmení o 1 percentuálny bod.</p>
		<table>
			<thead><tr><th></th><th class="r">−1 p. b.</th><th class="r">Teraz</th><th class="r">+1 p. b.</th></tr></thead>
			<tbody>
				{#each sens as s}
					<tr>
						<td>{SENS_LABEL[s.key]} <span class="muted small">({pct(inp[s.key], s.key === 'rate' ? 2 : 1)})</span></td>
						<td class="r">{beText(s.minus)}</td>
						<td class="r">{beText(s.base)}</td>
						<td class="r">{beText(s.plus)}</td>
					</tr>
				{/each}
			</tbody>
		</table>

		<h2>Zlom podľa úrokovej sadzby</h2>
		<LineChart
			x={rateGrid.map((r) => pct(r, 1))}
			series={[{ name: 'Mesiac zlomu', values: beByRate.map((b) => (b === null ? null : b / 12)), color: 'var(--own)' }]}
			format={(v) => `${num(v, 1)} r.`}
			marker={{ at: Math.round(inp.rate / 0.0025), label: 'vaša sadzba' }}
			endLabels={false}
			xTickEvery={4}
			yMin={0}
		/>
		<p class="small muted">Po koľkých rokoch kúpa dobehne nájom pri sadzbách od 0 % do 8 %; chýbajúca čiara znamená, že ho nedobehne počas splácania.</p>
	</section>
</div>

<style>
	.pick {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
		margin-bottom: 12px;
	}
	.pick select {
		width: auto;
		max-width: 100%;
		font-size: 16px;
		font-weight: 500;
	}
	.answer {
		border: 1px solid var(--line);
		border-radius: 10px;
		padding: 16px;
		background: var(--soft);
	}
	.lead {
		font-size: 19px;
		line-height: 1.4;
		margin: 0 0 6px;
		text-wrap: pretty;
	}
	.flip {
		margin: 0 0 8px;
		font-size: 16px;
	}
	.rate {
		margin-top: 12px;
	}
	.rate input {
		width: 100%;
		accent-color: var(--accent);
	}
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: 32px;
	}
	@media (max-width: 820px) {
		.grid {
			grid-template-columns: minmax(0, 1fr);
			gap: 0;
		}
	}
	.fields {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 10px 14px;
	}
	.field {
		min-width: 0;
	}
	.field.wide {
		grid-column: 1 / -1;
	}
	.field label {
		display: block;
		margin-bottom: 2px;
	}
	.refix {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-top: 6px;
	}
	.refix input {
		width: 70px;
	}
	details summary {
		cursor: pointer;
		list-style: revert;
	}
	details summary h2 {
		display: inline;
	}
	.toggles {
		display: grid;
		gap: 10px;
	}
	.toggles label {
		display: block;
		font-size: 14px;
	}
	.toggles span {
		display: block;
		margin-left: 24px;
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
