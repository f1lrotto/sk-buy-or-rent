<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { flip } from 'svelte/animate';
	import { replaceState } from '$app/navigation';
	import { Collapsible, Command, Popover, Slider, Switch } from 'bits-ui';
	import { DEFAULTS, DEFAULT_RULES, flips, sensitivity, simulate, type FlipKey, type Inputs, type RefixPath } from '#lib/calc.ts';
	import { LEVEL_LABEL, SOURCE_SHORT, type Place } from '#lib/data.ts';
	import { eur, inPlace, monthsAfter, num, pct, period } from '#lib/format.ts';
	import { readOverrides, writeOverrides } from '#lib/state.ts';
	import { calm, direct, fadeOnChange } from '#lib/motion.ts';
	import Field from '#lib/components/Field.svelte';
	import FooterNote from '#lib/components/FooterNote.svelte';
	import LineChart from '#lib/components/LineChart.svelte';
	import Roll from '#lib/components/Roll.svelte';
	import Segmented from '#lib/components/Segmented.svelte';

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
		pickerOpen = false;
		if (id === placeId) return;
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
	const edited = (k: keyof Inputs) => k in o && o[k] !== base[k];

	const res = $derived(simulate(inp, rules));
	const stayM = $derived(Math.round(12 * inp.stay));
	const be = $derived(res.breakEven);
	const winsInStay = $derived(be !== null && be <= stayM);
	const fl = $derived(flips(inp, rules));
	const ecbRate = latest.defaults.rate / 100;

	const yearsWord = (n: number) => (n === 1 ? 'rok' : n >= 2 && n <= 4 ? 'roky' : 'rokov');
	const beText = (b: number | null) => (b === null ? `nad ${inp.term} r.` : b < 24 ? `${b} mes.` : `${num(b / 12, 1)} r.`);
	const src = (key: string, per?: string) => `${SOURCE_SHORT[key] ?? key}${per ? `, ${period(per)}` : ''}`;

	// ---------- the answer ----------
	const variant = $derived(winsInStay ? 'win' : be !== null ? 'late' : 'never');
	const where = $derived(inPlace(place)[0].toUpperCase() + inPlace(place).slice(1));
	const flipSentence = $derived.by(() => {
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
	});

	// ---------- monthly costs ----------
	let year = $state<'1' | '10'>('1');
	const row = $derived(res.months[Math.min(res.months.length - 1, 12 * (+year - 1))]);
	const running = $derived(Math.max(0, row.ownerCost - row.payment));
	const barMax = $derived(Math.max(row.ownerCost, row.rent));
	const diff = $derived(row.ownerCost - row.rent);

	// ---------- break-even by mortgage rate ----------
	const RATES = Array.from({ length: 33 }, (_, i) => i * 0.0025);
	const stripBe = $derived(RATES.map((r) => simulate({ ...inp, rate: r }, rules).breakEven));
	const stripTop = $derived(Math.min(12 * inp.term, Math.max(2 * stayM, ...stripBe.filter((b) => b !== null))));
	const onBar = $derived(Math.round(inp.rate / 0.0025));
	let hoverRate = $state<number | null>(null);

	// ---------- net worth ----------
	const chartX = $derived([0, ...res.months.map((m) => m.m)].map((m) => (m === 0 ? 'dnes' : m % 12 === 0 ? `${m / 12}. r.` : `${num(m / 12, 1)} r.`)));

	// ---------- what decides ----------
	const SENS_LABEL: Record<FlipKey, string> = {
		priceGrowth: 'Rast cien bytov',
		rentGrowth: 'Rast nájomného',
		investReturn: 'Výnos investícií',
		rate: 'Úroková sadzba'
	};
	const sens = $derived(sensitivity(inp, rules));
	const sensAxis = $derived.by(() => {
		const vals = sens.flatMap((s) => [s.minus, s.base, s.plus]).filter((v) => v !== null);
		const raw = Math.max(12, ...vals) * 1.08;
		const step = [3, 6, 12, 24, 36, 60, 120].find((s) => raw / s <= 5) ?? 120;
		const max = Math.ceil(raw / step) * step;
		return { max, ticks: Array.from({ length: max / step + 1 }, (_, i) => i * step) };
	});
	const sx = (v: number | null) => `${(Math.min(v ?? sensAxis.max, sensAxis.max) / sensAxis.max) * 100}%`;
	const spread = (s: { minus: number | null; plus: number | null }) => Math.abs((s.plus ?? sensAxis.max) - (s.minus ?? sensAxis.max));
	// most influential first; lo and hi are the ends of each row's range
	const sensRows = $derived(
		[...sens]
			.sort((a, b) => spread(b) - spread(a))
			.map((s) => {
				const ends = [s.minus ?? sensAxis.max, s.plus ?? sensAxis.max];
				return { ...s, lo: Math.min(...ends), hi: Math.max(...ends) };
			})
	);
	const tickText = (v: number) => (v === 0 ? '0' : v < 24 ? `${v} mes.` : `${num(v / 12)} r.`);

	// ---------- place picker ----------
	let pickerOpen = $state(false);
	let cmdValue = $state('');
	$effect(() => {
		if (pickerOpen) cmdValue = untrack(() => placeId);
	});
	const fold = (s: string) => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
	const filterPlaces = (_: string, search: string, keywords?: string[]) => (fold(keywords?.join(' ') ?? '').includes(fold(search.trim())) ? 1 : 0);

	let ownerCostsOpen = $state(false);
	const refixCount = $derived(Math.max(0, Math.ceil(inp.term / inp.fixation) - 1));
</script>

<svelte:head>
	<title>Kúpiť či prenajať byt {inPlace(place)}? | Kalkulačka</title>
</svelte:head>

{#snippet chevron(size = 16)}
	<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"
		><path d="m6 9 6 6 6-6" /></svg
	>
{/snippet}

<div class="shell">
	<aside aria-label="Vstupy">
		<Popover.Root bind:open={pickerOpen}>
			<Popover.Trigger class="place-btn">
				<span class="pn">{place.name}</span><span class="pl">{LEVEL_LABEL[place.level]}</span>{@render chevron()}
			</Popover.Trigger>
			<Popover.Portal>
				<!-- fixed: the trigger sits in a sticky sidebar; an absolute layer is focused at the page top and scrolls the window there -->
				<Popover.Content class="pop" strategy="fixed" sideOffset={6} align="start" collisionPadding={12}>
					<Command.Root filter={filterPlaces} bind:value={cmdValue} label="Miesto">
						<label class="q">
							<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"
								><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg
							>
							<Command.Input placeholder="Hľadať kraj, mesto alebo mestskú časť" />
						</label>
						<Command.List class="list">
							<Command.Viewport>
								<Command.Empty class="empty">Nič sa nenašlo.</Command.Empty>
								{#each groups as [label, ps] (label)}
									<Command.Group value={label}>
										<Command.GroupHeading class="gh">{label}</Command.GroupHeading>
										<Command.GroupItems>
											{#each ps as p (p.id)}
												<Command.Item class="opt" value={p.id} keywords={[p.name]} onSelect={() => choose(p.id)}>
													<span>{p.name}</span>
													{#if p.id === placeId}
														<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"
															><path d="M20 6 9 17l-5-5" /></svg
														>
													{/if}
													{#if p.quality === 'indicative'}<span class="i">orientačné</span>{/if}
												</Command.Item>
											{/each}
										</Command.GroupItems>
									</Command.Group>
								{/each}
							</Command.Viewport>
						</Command.List>
					</Command.Root>
				</Popover.Content>
			</Popover.Portal>
		</Popover.Root>
		{#if place.quality === 'indicative'}
			<p class="chip warn quality" title="Menej ako 50 inzerátov na predaj alebo 30 na prenájom v niektorom z posledných 3 mesiacov">
				Orientačné údaje, v ponukách je málo inzerátov.
			</p>
		{/if}

		<div class="group">
			<h2 class="gt">Byt</h2>
			<Field label="Cena za m²" unit="€" step={10} value={inp.priceM2} base={base.priceM2} set={(v) => set('priceM2', v)} edited={edited('priceM2')} reset={() => reset('priceM2')}>
				{#snippet source()}
					{src(place.price.source, place.price.period)}{place.price.note ? `, ${place.price.note}` : ''}
					{#each place.price.checks ?? [] as c}
						<br />Pre porovnanie {src(c.source)}: {eur(c.value)}/m²
					{/each}
				{/snippet}
			</Field>
			<Field label="Nájomné za m²" unit="€/mes." step={0.1} digits={2} value={inp.rentM2} base={base.rentM2} set={(v) => set('rentM2', v)} edited={edited('rentM2')} reset={() => reset('rentM2')}>
				{#snippet source()}
					{src(place.rent.source, place.rent.period)}, ponukové{place.rent.n ? `, ${num(place.rent.n)} inzerátov` : ''}
					{#each place.rent.checks ?? [] as c}
						<br />Pre porovnanie {src(c.source, c.period)}: {c.per === 'byt' ? `${eur(c.value)} za byt` : `${num(c.value, 2)}\u00a0€/m²`}{c.note ? ` (${c.note})` : ''}
					{/each}
				{/snippet}
			</Field>
			<Field label="Rozloha bytu" unit="m²" value={inp.area} base={base.area} set={(v) => set('area', v)} edited={edited('area')} reset={() => reset('area')}>
				{#snippet source()}Typický 2- až 3-izbový byt{/snippet}
			</Field>
			<Field label="Plánované bývanie" unit="r." value={inp.stay} base={base.stay} set={(v) => set('stay', v)} edited={edited('stay')} reset={() => reset('stay')}>
				{#snippet source()}Obdobie, pre ktoré platí odpoveď{/snippet}
			</Field>
		</div>

		<div class="group">
			<h2 class="gt">Hypotéka</h2>
			<Field label="Vlastné zdroje" unit="%" value={inp.down * 100} base={base.down * 100} set={(v) => set('down', v / 100)} edited={edited('down')} reset={() => reset('down')}>
				{#snippet source()}Banky bežne požadujú 20 % (LTV 80 %){/snippet}
			</Field>
			<Field label="Doba splácania" unit="r." value={inp.term} base={base.term} set={(v) => set('term', v)} edited={edited('term')} reset={() => reset('term')}>
				{#snippet source()}NBS povoľuje najviac 30 rokov{/snippet}
			</Field>
			<div class="frow">
				<label for="fix">Fixácia</label>
				<select id="fix" value={String(inp.fixation)} onchange={(e) => set('fixation', +e.currentTarget.value)}>
					{#each [1, 3, 5, 10] as f}<option value={String(f)}>{f} {yearsWord(f)}</option>{/each}
				</select>
			</div>
			<div class="frow">
				<label for="refix">Sadzba po fixácii</label>
				<select id="refix" value={inp.refix} onchange={(e) => set('refix', e.currentTarget.value as RefixPath)}>
					<option value="same">Rovnaká</option>
					<option value="up1">+1 p. b.</option>
					<option value="down1">−1 p. b.</option>
					<option value="custom">Vlastná</option>
				</select>
			</div>
			{#if inp.refix === 'custom'}
				{#each Array.from({ length: refixCount }) as _, k}
					<Field
						label="Od {k * inp.fixation + inp.fixation + 1}. roka"
						unit="%"
						step={0.1}
						digits={2}
						value={(inp.refixRates[k] ?? inp.refixRates.at(-1) ?? inp.rate) * 100}
						set={(v) => {
							const rr = [...inp.refixRates];
							while (rr.length <= k) rr.push(rr.at(-1) ?? inp.rate);
							rr[k] = v / 100;
							set('refixRates', rr);
						}}
					/>
				{/each}
			{/if}
		</div>

		<div class="group">
			<h2 class="gt">Predpoklady</h2>
			<Field label="Rast cien bytov" unit="%" step={0.1} value={inp.priceGrowth * 100} base={base.priceGrowth * 100} set={(v) => set('priceGrowth', v / 100)} edited={edited('priceGrowth')} reset={() => reset('priceGrowth')}>
				{#snippet source()}
					NBS: {pct(place.growth.nbs_cagr)} ročne od roku {place.growth.from} (kraj){place.growth.su_yoy !== undefined && place.growth.su_yoy !== null
						? `, realizačné ceny za rok ${pct(place.growth.su_yoy, 1, true)} (ŠÚ SR)`
						: ''}
				{/snippet}
			</Field>
			<Field label="Rast nájomného" unit="%" step={0.1} digits={2} value={inp.rentGrowth * 100} base={base.rentGrowth * 100} set={(v) => set('rentGrowth', v / 100)} edited={edited('rentGrowth')} reset={() => reset('rentGrowth')}>
				{#snippet source()}Eurostat, priemer 10 rokov do {period(latest.defaults.rent_growth_period)}, skutočne platené nájmy{/snippet}
			</Field>
			<Field label="Výnos investícií" unit="%" step={0.1} value={inp.investReturn * 100} base={base.investReturn * 100} set={(v) => set('investReturn', v / 100)} edited={edited('investReturn')} reset={() => reset('investReturn')}>
				{#snippet source()}
					<button class="link" onclick={() => set('investReturn', 0.025)}>Termínovaný vklad 2,5 %</button>,
					<button class="link" onclick={() => set('investReturn', 0.07)}>akciový index 7 %</button>
				{/snippet}
			</Field>
			<Field label="Inflácia nákladov" unit="%" step={0.1} value={inp.inflation * 100} base={base.inflation * 100} set={(v) => set('inflation', v / 100)} edited={edited('inflation')} reset={() => reset('inflation')}>
				{#snippet source()}Pre údržbu, daň a poistenie{/snippet}
			</Field>
		</div>

		<Collapsible.Root bind:open={ownerCostsOpen} class="group">
			<Collapsible.Trigger class="gt toggle">
				<h2>Náklady vlastníka</h2>
				{@render chevron(14)}
			</Collapsible.Trigger>
			<Collapsible.Content class="coll">
				<Field label="Údržba a fond opráv" unit="€/m²" step={0.1} digits={2} value={inp.maintenance} base={base.maintenance} set={(v) => set('maintenance', v)} edited={edited('maintenance')} reset={() => reset('maintenance')}>
					{#snippet source()}Mesačne{/snippet}
				</Field>
				<Field label="Daň z nehnuteľnosti" unit="€/m²" step={0.1} digits={2} value={inp.propertyTax} base={base.propertyTax} set={(v) => set('propertyTax', v)} edited={edited('propertyTax')} reset={() => reset('propertyTax')}>
					{#snippet source()}Ročne, líši sa podľa obce{/snippet}
				</Field>
				<Field label="Poistenie" unit="€" step={10} value={inp.insurance} base={base.insurance} set={(v) => set('insurance', v)} edited={edited('insurance')} reset={() => reset('insurance')}>
					{#snippet source()}Ročne{/snippet}
				</Field>
				<Field label="Náklady na kúpu" unit="%" step={0.1} value={inp.buyCost * 100} base={base.buyCost * 100} set={(v) => set('buyCost', v / 100)} edited={edited('buyCost')} reset={() => reset('buyCost')}>
					{#snippet source()}Poplatky, znalec, kataster{/snippet}
				</Field>
				<Field label="Náklady na predaj" unit="%" step={0.1} value={inp.sellCost * 100} base={base.sellCost * 100} set={(v) => set('sellCost', v / 100)} edited={edited('sellCost')} reset={() => reset('sellCost')}>
					{#snippet source()}Realitná kancelária a poplatky{/snippet}
				</Field>
			</Collapsible.Content>
		</Collapsible.Root>

		<div class="group">
			<h2 class="gt">Dane a štátna podpora</h2>
			<div class="sw">
				<label for="sw-yb">Daňový bonus pre mladých</label>
				<Switch.Root id="sw-yb" class="switch" checked={inp.youngBonus} onCheckedChange={(v) => set('youngBonus', v)}><Switch.Thumb class="thumb" /></Switch.Root>
				<p>
					{pct(rules.bonusShare, 0)} úrokov, najviac {eur(rules.bonusMaxYear)} ročne počas {rules.bonusYears} rokov. Do {rulesCfg.young_buyer_bonus.max_age} rokov, príjem
					do {eur(rulesCfg.young_buyer_bonus.income_limit_monthly)} mesačne. {rulesCfg.young_buyer_bonus.source}.
					{#if inp.youngBonus}<span class="on">Bonus spolu {eur(res.bonusTotal)}.</span>{/if}
				</p>
			</div>
			<div class="sw">
				<label for="sw-it">Zdaniť zisk z investícií</label>
				<Switch.Root id="sw-it" class="switch" checked={inp.investTax} onCheckedChange={(v) => set('investTax', v)}><Switch.Thumb class="thumb" /></Switch.Root>
				<p>{pct(rules.gainTax, 0)} vrátane zdravotného poistenia. ETF na burze držané dlhšie ako rok sú oslobodené ({rulesCfg.securities_exemption.source}).</p>
			</div>
			<div class="sw">
				<label for="sw-st">Zdaniť predaj bytu do {rules.flatHoldingYears} rokov</label>
				<Switch.Root id="sw-st" class="switch" checked={inp.saleTax} onCheckedChange={(v) => set('saleTax', v)}><Switch.Thumb class="thumb" /></Switch.Root>
				<p>{rulesCfg.flat_sale_exemption.source}.</p>
			</div>
		</div>
	</aside>

	<div class="results">
		<section class="answer" aria-live="polite">
			<h1 {@attach fadeOnChange(variant + place.id)}>
				{#if variant === 'never'}
					{where} sa kúpa bytu neoplatí viac ako nájom počas celej doby splácania.
				{:else}
					{where}
					{variant === 'win' ? 'sa kúpa oplatí viac ako nájom po' : 'kúpa dobehne nájom až po'}
					<span class={variant}><Roll text={monthsAfter(be!)} /></span>{variant === 'win' ? '.' : ', neskôr, ako tu plánujete bývať.'}
				{/if}
			</h1>
			<p class="lede">{flipSentence}</p>
		</section>

		<section>
			<div class="sh">
				<h2>Mesačné náklady</h2>
				<Segmented label="Rok" value={year} options={[['1', '1. rok'], ['10', '10. rok']]} onchange={(v) => (year = v)} />
			</div>
			<div class="mrow">
				<span class="ml">Vlastník</span>
				<div class="mbar" aria-hidden="true">
					<i class="pay" style:width="{(Math.min(row.payment, row.ownerCost) / barMax) * 100}%"></i><i class="run" style:width="calc({(running / barMax) * 100}% - 2px)"></i>
				</div>
				<span class="mv"><Roll text={eur(row.ownerCost)} /></span>
			</div>
			<div class="mrow">
				<span class="ml">Nájomca</span>
				<div class="mbar" aria-hidden="true"><i class="rent" style:width="{(row.rent / barMax) * 100}%"></i></div>
				<span class="mv"><Roll text={eur(row.rent)} /></span>
			</div>
			<p class="cap">
				Splátka <b>{eur(row.payment)}</b>, z toho úroky {eur(row.interest)}. Údržba, daň a poistenie <b>{eur(running)}</b>.
				{#if Math.abs(diff) < 1}
					Obaja platia rovnako.
				{:else}
					{diff > 0 ? 'Nájomca' : 'Vlastník'} platí o <b>{eur(Math.abs(diff))}</b> menej a rozdiel investuje s výnosom {pct(inp.investReturn)} ročne.
				{/if}
				Byt stojí {eur(res.price)}, úver je {eur(res.loan)}.
			</p>
		</section>

		<section>
			<div class="sh">
				<h2>Úroková sadzba</h2>
				<span class="rv"><Roll text={pct(inp.rate, 2)} /></span>
			</div>
			<div class="strip">
				{#each RATES as r, i}
					{@const b = stripBe[i]}
					<button
						class="bar {b !== null && b <= stayM ? 'win' : 'late'}"
						class:on={i === onBar}
						style:left="{(i / 32) * 100}%"
						style:height="{(Math.min(b ?? stripTop, stripTop) / stripTop) * 100}%"
						aria-label="{pct(r, 2)}: {beText(b)}"
						onclick={() => set('rate', r)}
						onpointerenter={() => (hoverRate = i)}
						onpointerleave={() => (hoverRate = null)}
						onfocus={() => (hoverRate = i)}
						onblur={() => (hoverRate = null)}
					></button>
				{/each}
				<div class="stayline" style:bottom="{Math.min(1, stayM / stripTop) * 100}%">
					<span>{num(inp.stay)} {yearsWord(inp.stay)} bývania</span>
				</div>
			</div>
			<Slider.Root
				type="single"
				class="slider"
				value={inp.rate}
				min={0}
				max={0.08}
				step={0.0001}
				onValueChange={(v) => {
					direct();
					set('rate', v);
				}}
			>
				<span class="track"><Slider.Range class="range" /></span>
				<Slider.Thumb index={0} class="thumb" aria-label="Úroková sadzba hypotéky" />
			</Slider.Root>
			<div class="scale">
				<span style:left="0">0 %</span>
				<span class="ecb" style:left="calc(8px + (100% - 16px) * {ecbRate / 0.08})">priemer {pct(ecbRate, 2)}</span>
				<span style:right="0">8 %</span>
			</div>
			<p class="cap">
				{#if hoverRate !== null}
					{#if stripBe[hoverRate] === null}
						Pri sadzbe <b>{pct(RATES[hoverRate], 2)}</b> kúpa nedobehne nájom počas splácania.
					{:else}
						Pri sadzbe <b>{pct(RATES[hoverRate], 2)}</b> kúpa dobehne nájom po {monthsAfter(stripBe[hoverRate]!)}.
					{/if}
				{:else}
					Stĺpce ukazujú, kedy kúpa dobehne nájom pri každej sadzbe. Priemer nových hypoték je {pct(ecbRate, 2)} (ECB, {period(latest.defaults.rate_period)}).
					{#if fl.rate !== null}
						{winsInStay ? 'Kúpa prestane vyhrávať' : 'Kúpa začne vyhrávať'} pri sadzbe <b>{pct(fl.rate, 2)}</b>.
					{/if}
				{/if}
			</p>
		</section>

		<section>
			<div class="sh"><h2>Čistý majetok vlastníka a nájomcu</h2></div>
			<LineChart
				x={chartX}
				series={[
					{ name: 'Vlastník', values: [res.price * (1 - inp.sellCost) - res.loan, ...res.months.map((m) => m.owner)], color: 'var(--own)' },
					{ name: 'Nájomca', values: [res.price * (inp.down + inp.buyCost), ...res.months.map((m) => m.renter)], color: 'var(--rent)' }
				]}
				format={(v) => eur(v)}
				tick={(v) => (v === 0 ? '0 €' : `${num(v / 1000)} tis. €`)}
				title={(i) => (i === 0 ? 'Dnes' : `Po ${monthsAfter(i)}`)}
				pin={stayM}
				marker={be !== null ? { at: be, label: `Kúpa dobehne nájom po ${beText(be)}` } : undefined}
				endLabels={false}
				xTickEvery={60}
				height={280}
				drawIn
			/>
			<p class="cap">
				Vlastník: hodnota bytu po nákladoch na predaj (a dani pri predaji do {rules.flatHoldingYears} rokov) mínus zostatok úveru plus investované úspory. Nájomca:
				investované vlastné zdroje a mesačné úspory.
			</p>
		</section>

		<section>
			<div class="sh"><h2>Čo rozhoduje</h2></div>
			<div class="sens">
				{#each sensRows as s (s.key)}
					<div class="srow" animate:flip={{ duration: calm() ? 0 : 320, easing: (t) => 1 - (1 - t) ** 4 }}>
						<span class="sl">{SENS_LABEL[s.key]}<span>{pct(inp[s.key], s.key === 'rate' ? 2 : 1)}</span></span>
						<div class="plot" aria-hidden="true">
							<i class="span" style:left={sx(s.lo)} style:width="calc({sx(s.hi)} - {sx(s.lo)})"></i>
							<i class="base" style:left={sx(s.base)}></i>
							<i class="dotm" style:left={sx(s.minus)}></i>
							<i class="dotp" style:left={sx(s.plus)}></i>
						</div>
						<div class="sv">
							<span><i class="dotm"></i>{beText(s.minus)}</span>
							<span><i class="dotp"></i>{beText(s.plus)}</span>
						</div>
					</div>
				{/each}
			</div>
			<div class="axis" aria-hidden="true">
				<span></span>
				<div class="ticks">
					{#each sensAxis.ticks as t}<span style:left={sx(t)}>{tickText(t)}</span>{/each}
				</div>
				<span></span>
			</div>
			<div class="legend">
				<span><i class="dotm"></i>o 1 p. b. menej</span>
				<span><i class="dotp"></i>o 1 p. b. viac</span>
				<span><i class="tk"></i>teraz</span>
			</div>
			<p class="cap">Po koľkých mesiacoch kúpa dobehne nájom, ak sa jeden predpoklad zmení o 1 percentuálny bod. Najvplyvnejšie predpoklady sú hore.</p>
		</section>

		<!-- In the results column, not the layout, so the sticky inputs panel reaches the page end. -->
		<footer><FooterNote /></footer>
	</div>
</div>

<style>
	.shell {
		display: grid;
		grid-template-columns: 328px minmax(0, 1fr);
	}

	/* ---------- inputs ---------- */
	aside {
		position: sticky;
		top: var(--header);
		height: calc(100vh - var(--header));
		overflow: auto;
		padding: 20px 20px 48px;
		background: var(--panel);
		border-right: 1px solid var(--line);
		overscroll-behavior: contain;
	}
	aside :global(.place-btn) {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 8px;
		height: 40px;
		padding: 0 12px;
		border: 0;
		border-radius: 8px;
		background: var(--field);
		box-shadow:
			var(--ring),
			0 1px 2px rgb(0 0 0 / 0.04);
		text-align: left;
		transition: transform 100ms var(--ease);
	}
	aside :global(.place-btn .pn) {
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	aside :global(.place-btn .pl) {
		font-size: 13px;
		color: var(--muted);
		white-space: nowrap;
	}
	aside :global(.place-btn svg) {
		flex: none;
		margin-left: auto;
		color: var(--muted);
		transition: transform 200ms var(--ease);
	}
	aside :global(.place-btn[data-state='open'] svg) {
		transform: rotate(180deg);
	}
	@media (hover: hover) {
		aside :global(.place-btn:hover) {
			box-shadow:
				var(--ring-hover),
				0 1px 2px rgb(0 0 0 / 0.04);
		}
	}
	.quality {
		margin: 10px 2px 0;
	}

	/* the place popover is portalled to <body> */
	:global(.pop) {
		z-index: 50;
		width: var(--bits-floating-anchor-width);
		min-width: 288px;
		overflow: hidden;
		border-radius: 10px;
		background: var(--field);
		box-shadow: var(--shadow-pop);
		transform-origin: var(--bits-floating-transform-origin);
	}
	:global(.pop[data-state='open']) {
		animation: pop-in 160ms var(--ease);
	}
	:global(.pop[data-state='closed']) {
		animation: pop-out 120ms var(--ease) forwards;
	}
	@keyframes pop-in {
		from {
			opacity: 0;
			transform: translateY(-4px) scale(0.97);
		}
	}
	@keyframes pop-out {
		to {
			opacity: 0;
			transform: scale(0.98);
		}
	}
	:global(.pop .q) {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 0 12px;
		border-bottom: 1px solid var(--line);
		color: var(--muted);
	}
	:global(.pop .q input) {
		all: unset;
		flex: 1;
		height: 40px;
		color: var(--fg);
	}
	:global(.pop .q input::placeholder) {
		color: var(--faint);
	}
	:global(.pop .list) {
		max-height: min(340px, calc(var(--bits-floating-available-height) - 56px));
		overflow: auto;
		padding: 4px;
		scroll-padding: 32px 0 4px;
	}
	:global(.pop .gh) {
		position: sticky;
		top: -4px;
		z-index: 1;
		padding: 8px 8px 4px;
		font-size: 12px;
		color: var(--muted);
		background: var(--field);
	}
	:global(.pop .opt) {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 8px;
		border-radius: 6px;
		cursor: pointer;
	}
	:global(.pop .opt[data-selected]) {
		background: var(--soft);
	}
	:global(.pop .opt .i) {
		margin-left: auto;
		font-size: 12px;
		color: var(--muted);
	}
	:global(.pop .empty) {
		padding: 16px 8px;
		color: var(--muted);
	}

	aside :global(.group) {
		padding: 14px 0 10px;
		border-top: 1px solid var(--line);
	}
	aside > :global(.group:first-of-type) {
		margin-top: 8px;
		border-top: 0;
	}
	.gt,
	aside :global(.gt h2) {
		margin: 0 0 6px;
		font-size: 13px;
		font-weight: 500;
		letter-spacing: 0;
	}
	aside :global(button.gt) {
		display: flex;
		align-items: center;
		width: 100%;
		margin: 0;
		padding: 0;
		border: 0;
		background: none;
		text-align: left;
	}
	aside :global(button.gt h2) {
		margin: 0;
	}
	aside :global(button.gt svg) {
		margin-left: auto;
		color: var(--muted);
		transform: rotate(-90deg);
		transition: transform 220ms var(--ease);
	}
	aside :global(button.gt[data-state='open'] svg) {
		transform: none;
	}
	aside :global(button.gt:active) {
		transform: none;
	}
	aside :global(.coll) {
		overflow: hidden;
		padding-top: 6px;
	}
	aside :global(.coll[data-state='open']) {
		animation: coll-open 240ms var(--ease);
	}
	aside :global(.coll[data-state='closed']) {
		animation: coll-close 180ms var(--ease);
	}
	@keyframes coll-open {
		from {
			height: 0;
			opacity: 0;
		}
		to {
			height: var(--bits-collapsible-content-height);
		}
	}
	@keyframes coll-close {
		from {
			height: var(--bits-collapsible-content-height);
		}
		to {
			height: 0;
			opacity: 0;
		}
	}
	.frow {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 128px;
		column-gap: 12px;
		align-items: center;
		padding: 5px 0 9px;
	}
	.frow label {
		font-size: 13px;
		color: var(--fg-2);
	}
	.frow select {
		height: 30px;
		text-align: right;
		text-align-last: right;
	}
	.sw {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		column-gap: 12px;
		padding: 6px 0;
	}
	.sw label {
		font-size: 13px;
		color: var(--fg-2);
	}
	.sw :global(.switch) {
		grid-row: 1 / 3;
		grid-column: 2;
		align-self: start;
		margin-top: 1px;
	}
	.sw p {
		margin: 2px 0 0;
		font-size: 12px;
		line-height: 1.4;
		color: var(--muted);
	}
	.sw .on {
		color: var(--fg-2);
	}

	/* ---------- results ---------- */
	.results {
		min-width: 0;
		max-width: 900px;
		margin-inline: auto;
		padding: 44px 56px 40px;
	}
	footer {
		margin-top: 16px;
	}
	section {
		padding: 32px 0;
		border-top: 1px solid var(--line);
	}
	.answer {
		padding: 0 0 36px;
		border: 0;
	}
	h1 {
		font-size: 34px;
		margin: 0;
		max-width: 760px;
	}
	h1 .win {
		color: var(--own);
	}
	h1 .late {
		color: var(--rent);
	}
	.lede {
		margin: 14px 0 0;
		max-width: 640px;
		font-size: 16px;
		color: var(--fg-2);
	}
	.sh {
		display: flex;
		align-items: center;
		gap: 16px;
		min-height: 30px;
		margin-bottom: 18px;
	}
	.sh h2 {
		margin: 0;
		font-size: 15px;
	}
	.sh > :global(:last-child:not(h2)) {
		margin-left: auto;
	}

	.mrow {
		display: grid;
		grid-template-columns: 80px minmax(0, 1fr) 96px;
		align-items: center;
		gap: 16px;
		padding: 6px 0;
	}
	.ml {
		color: var(--fg-2);
	}
	.mbar {
		display: flex;
		height: 12px;
	}
	.mbar i {
		display: block;
		height: 100%;
		transition: width 450ms var(--ease);
	}
	.mbar i:first-child {
		border-radius: 3px 0 0 3px;
	}
	.mbar i:last-child {
		border-radius: 0 3px 3px 0;
	}
	.mbar i:only-child {
		border-radius: 3px;
	}
	.mbar .pay {
		background: var(--own);
	}
	.mbar .run {
		margin-left: 2px;
		background: var(--own-tint);
	}
	.mbar .rent {
		background: var(--rent);
	}
	.mv {
		text-align: right;
		font-size: 16px;
		font-weight: 500;
		font-variant-numeric: tabular-nums;
	}

	.rv {
		font-size: 22px;
		font-weight: 500;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
	}
	.strip {
		position: relative;
		height: 84px;
		margin: 0 8px 8px;
	}
	.bar {
		position: absolute;
		bottom: 0;
		width: calc(100% / 33 - 3px);
		min-height: 2px;
		padding: 0;
		border: 0;
		border-radius: 2px 2px 0 0;
		transform: translateX(-50%);
		transition: height 350ms var(--ease);
	}
	.bar:active {
		transform: translateX(-50%) scale(0.97);
		transform-origin: bottom;
	}
	.bar.win {
		background: var(--own-tint);
	}
	.bar.late {
		background: var(--rent-tint);
	}
	.bar.on.win {
		background: var(--own);
	}
	.bar.on.late {
		background: var(--rent);
	}
	@media (hover: hover) {
		.bar.win:not(.on):hover {
			background: color-mix(in oklab, var(--own) 55%, var(--bg));
		}
		.bar.late:not(.on):hover {
			background: color-mix(in oklab, var(--rent) 58%, var(--bg));
		}
	}
	.stayline {
		position: absolute;
		left: -8px;
		right: -8px;
		border-top: 1px dashed var(--faint);
		pointer-events: none;
		transition: bottom 350ms var(--ease);
	}
	.stayline span {
		position: absolute;
		left: 8px;
		bottom: 3px;
		padding-right: 6px;
		font-size: 11px;
		color: var(--muted);
		background: var(--bg);
	}
	.scale {
		position: relative;
		height: 18px;
		margin-top: 4px;
		font-size: 12px;
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.scale span {
		position: absolute;
		top: 0;
		white-space: nowrap;
	}
	.scale .ecb {
		transform: translateX(-50%);
		color: var(--fg-2);
	}
	.scale .ecb::before {
		content: '';
		position: absolute;
		left: 50%;
		top: -9px;
		width: 1px;
		height: 6px;
		background: var(--faint);
	}

	.sens {
		display: grid;
	}
	.srow,
	.axis {
		display: grid;
		grid-template-columns: 200px minmax(0, 1fr) 150px;
		gap: 20px;
	}
	.srow {
		align-items: center;
		height: 40px;
		border-top: 1px solid var(--line-2);
		background: var(--bg);
	}
	.srow:first-child {
		border-top: 0;
	}
	.sl {
		color: var(--fg-2);
		white-space: nowrap;
	}
	.sl span {
		margin-left: 6px;
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.plot {
		position: relative;
		height: 16px;
	}
	.plot > * {
		position: absolute;
		top: 50%;
		transition:
			left 400ms var(--ease),
			width 400ms var(--ease);
	}
	.plot .span {
		height: 2px;
		margin-top: -1px;
		background: color-mix(in oklab, var(--fg) 16%, var(--bg));
	}
	.plot .base {
		width: 1px;
		height: 16px;
		margin-top: -8px;
		background: var(--fg);
	}
	.dotm,
	.dotp {
		display: inline-block;
		width: 9px;
		height: 9px;
		border-radius: 50%;
	}
	.dotm {
		background: var(--bg);
		box-shadow: inset 0 0 0 1.5px var(--fg-2);
	}
	.dotp {
		background: var(--fg-2);
	}
	.plot .dotm,
	.plot .dotp {
		margin: -4.5px 0 0 -4.5px;
	}
	.sv {
		display: flex;
		justify-content: flex-end;
		gap: 14px;
		color: var(--fg-2);
		font-variant-numeric: tabular-nums;
	}
	.sv span {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		white-space: nowrap;
	}
	.axis {
		height: 24px;
		border-top: 1px solid var(--line);
	}
	.ticks {
		position: relative;
		font-size: 11px;
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.ticks span {
		position: absolute;
		top: 4px;
		transform: translateX(-50%);
		white-space: nowrap;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 16px;
		margin-top: 10px;
		font-size: 12px;
		color: var(--muted);
	}
	.legend span {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.legend .tk {
		width: 1px;
		height: 12px;
		background: var(--fg);
	}

	@media (max-width: 960px) {
		.shell {
			grid-template-columns: minmax(0, 1fr);
		}
		/* One column: the answer first, then the inputs, then the details. */
		aside {
			position: static;
			height: auto;
			border-right: 0;
			border-block: 1px solid var(--line);
		}
		.results {
			display: contents;
		}
		section,
		footer {
			margin-inline: 20px;
		}
		footer {
			padding-bottom: 32px;
		}
		.answer {
			order: -1;
			padding: 32px 0 28px;
		}
		h1 {
			font-size: 28px;
		}
		.mrow {
			grid-template-columns: 64px minmax(0, 1fr) 80px;
			gap: 12px;
		}
	}
	/* Phones: label and values share a line, the range plot gets the full width below. */
	@media (max-width: 600px) {
		.srow {
			grid-template-columns: minmax(0, 1fr) auto;
			grid-template-areas: 'l v' 'p p';
			row-gap: 6px;
			height: auto;
			padding: 10px 0 12px;
		}
		.sl {
			grid-area: l;
		}
		.sv {
			grid-area: v;
		}
		.plot {
			grid-area: p;
		}
		.axis {
			grid-template-columns: minmax(0, 1fr);
		}
		.axis > span {
			display: none;
		}
	}
</style>
