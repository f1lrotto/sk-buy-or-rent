<script lang="ts">
	import { onMount } from 'svelte';
	import { replaceState } from '$app/navigation';
	import { Slider } from 'bits-ui';
	import { affordability, amortisation, payment, type RefixPath } from '#lib/calc.ts';
	import { eur, num, pct, period } from '#lib/format.ts';
	import { writeOverrides } from '#lib/state.ts';
	import { direct } from '#lib/motion.ts';
	import Field from '#lib/components/Field.svelte';
	import LineChart from '#lib/components/LineChart.svelte';
	import Roll from '#lib/components/Roll.svelte';

	let { data } = $props();
	const rates = data.rates;
	const lim = data.rules.nbs_limits;
	const zm = data.rules.subsistence_minimum;

	let price = $state(200000);
	let downPct = $state(20);
	let term = $state(30);
	let fixation = $state(5);
	let rate = $state(rates.rate);
	let refix = $state<RefixPath>('same');
	let income = $state(2400);
	let adults = $state(2);
	let kids = $state(0);
	let otherPay = $state(0);
	let otherDebt = $state(0);

	onMount(() => {
		const q = new URLSearchParams(location.search);
		const n = (k: string, f: (v: number) => void) => q.get(k) !== null && Number.isFinite(+q.get(k)!) && f(+q.get(k)!);
		n('cena', (v) => (price = v));
		n('d', (v) => (downPct = v));
		n('t', (v) => (term = v));
		n('f', (v) => (fixation = v));
		n('r', (v) => (rate = v));
	});
	$effect(() => {
		const q = new URLSearchParams({ cena: String(price), d: String(downPct), t: String(term), f: String(fixation), r: String(rate) });
		replaceState(`${location.pathname}?${q}`, {});
	});

	const loan = $derived(price * (1 - downPct / 100));
	const am = $derived(amortisation(loan, { rate: rate / 100, term, fixation, refix, refixRates: [] }));
	const pay0 = $derived(am.payments[0].payment);
	const zero = $derived(payment(loan, 0, 12 * term));
	const grid = Array.from({ length: 29 }, (_, i) => i * 0.25);
	const subsistence = $derived(zm.first_adult + Math.max(0, adults - 1) * zm.other_adult + kids * zm.child);
	const aff = $derived(
		affordability({ loan, price, rate: rate / 100, fixation, netIncome: income, otherPayments: otherPay, subsistence, otherDebt }, lim)
	);

	const ecb = rates.ecb;
	const ecbCodes = ['F', 'I', 'O', 'P'].filter((c) => ecb[c]);
	const x5 = ecb.A.series.map(([p]) => p);
	const fixLabel = (f: number) => `${f} ${f === 1 ? 'rok' : f < 5 ? 'roky' : 'rokov'}`;
	const bankRows = [...rates.banks.offers].sort((a, b) => a.rate - b.rate);
	function useOffer(r: number, f: number) {
		rate = r;
		fixation = f;
		document.getElementById('kalkulacka')?.scrollIntoView({ behavior: 'smooth' });
	}
	const rentBuyLink = $derived(`/${writeOverrides({ rate: rate / 100, down: downPct / 100, term, fixation, refix })}`);
	const SERIES = ['var(--series-3)', 'var(--series-4)', 'var(--series-5)', 'var(--series-6)'];
</script>

<svelte:head><title>Hypotekárna kalkulačka a aktuálne sadzby | Kúpiť či prenajať</title></svelte:head>

<h1>Hypotéka: splátka, úroky a aktuálne sadzby</h1>
<p class="lede">
	Priemerná sadzba nových hypoték na Slovensku je <b>{pct(rates.rate / 100, 2)}</b> (ECB, {period(rates.period)}).
</p>

<section id="kalkulacka" class="calc">
	<div class="inputs">
		<Field label="Cena nehnuteľnosti" unit="€" step={1000} value={price} set={(v) => (price = v)} />
		<Field label="Vlastné zdroje" unit="%" value={downPct} set={(v) => (downPct = v)} />
		<Field label="Doba splácania" unit="r." value={term} set={(v) => (term = Math.max(1, Math.min(40, v)))} />
		<div class="frow">
			<label for="fix">Fixácia</label>
			<select id="fix" bind:value={fixation}>
				{#each [1, 3, 5, 10] as f}<option value={f}>{fixLabel(f)}</option>{/each}
			</select>
		</div>
		<div class="frow">
			<label for="refix">Sadzba po fixácii</label>
			<select id="refix" bind:value={refix}>
				<option value="same">Rovnaká</option>
				<option value="up1">+1 p. b.</option>
				<option value="down1">−1 p. b.</option>
			</select>
		</div>
		<Field label="Úroková sadzba" unit="%" step={0.01} digits={2} value={rate} set={(v) => (rate = Math.max(0, v))} />
		<Slider.Root
			type="single"
			class="slider"
			value={rate}
			min={0}
			max={8}
			step={0.01}
			onValueChange={(v) => {
				direct();
				rate = v;
			}}
		>
			<span class="track"><Slider.Range class="range" /></span>
			<Slider.Thumb index={0} class="thumb" aria-label="Úroková sadzba" />
		</Slider.Root>
	</div>

	<div class="result">
		<span class="label">Mesačná splátka</span>
		<span class="big"><Roll text={eur(pay0)} /></span>
		<div class="split" aria-hidden="true">
			<i class="own" style:width="{(loan / am.totalPaid) * 100}%"></i><i class="int" style:width="calc({(am.totalInterest / am.totalPaid) * 100}% - 2px)"></i>
		</div>
		<p class="cap">Za {term} rokov zaplatíte {eur(am.totalPaid)}: istinu {eur(loan)} a úroky <b>{eur(am.totalInterest)}</b>.</p>
		<table>
			<tbody>
				<tr><td>Výška úveru</td><td class="r">{eur(loan)}</td></tr>
				<tr><td>Zaplatené úroky spolu</td><td class="r">{eur(am.totalInterest)}</td></tr>
				<tr><td>Splátka pri 0 % (len istina)</td><td class="r">{eur(zero)}</td></tr>
				<tr><td>Z prvej splátky ide na úroky</td><td class="r">{eur((loan * rate) / 1200)}</td></tr>
				{#each refix === 'same' ? [] : am.payments.slice(1, 4) as p}
					<tr><td>Splátka od {Math.ceil(p.from / 12)}. roka pri {pct(p.rate, 2)}</td><td class="r">{eur(p.payment)}</td></tr>
				{/each}
			</tbody>
		</table>
		<p class="cap"><a href={rentBuyLink}>Porovnať kúpu a nájom s týmto úverom</a></p>
	</div>
</section>

<h2>Zostatok, úroky a istina po rokoch</h2>
<LineChart
	x={am.rows.map((r) => `${r.year}. rok`)}
	series={[
		{ name: 'Zostatok úveru', values: am.rows.map((r) => r.balance), color: 'var(--own)' },
		{ name: 'Úroky za rok ×10', values: am.rows.map((r) => r.interest * 10), color: 'var(--rent)', dashed: true },
		{ name: 'Istina za rok ×10', values: am.rows.map((r) => r.principal * 10), color: 'var(--series-4)', dashed: true }
	]}
	format={(v) => eur(v)}
	tick={(v) => (v === 0 ? '0 €' : `${num(v / 1000)} tis. €`)}
	yMin={0}
	xTickEvery={5}
	endLabels={false}
/>
<p class="cap">Úroky a istina za rok sú pre čitateľnosť zväčšené 10-krát.</p>
<details>
	<summary>Splátkový kalendár po rokoch</summary>
	<div class="scroll">
		<table>
			<thead><tr><th>Rok</th><th class="r">Sadzba</th><th class="r">Zaplatené</th><th class="r">Úroky</th><th class="r">Istina</th><th class="r">Zostatok</th></tr></thead>
			<tbody>
				{#each am.rows as r}
					<tr><td>{r.year}</td><td class="r">{pct(r.rate, 2)}</td><td class="r">{eur(r.paid)}</td><td class="r">{eur(r.interest)}</td><td class="r">{eur(r.principal)}</td><td class="r">{eur(r.balance)}</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
</details>

<h2>Splátka podľa úrokovej sadzby</h2>
<p class="cap">Úver {eur(loan)} na {term} rokov. Kliknutím sadzbu použijete; zvýraznená je najbližšia vašej.</p>
<div class="rategrid">
	{#each grid as r}
		<button class="cell" class:on={Math.abs(r - Math.round(rate * 4) / 4) < 1e-9} onclick={() => (rate = r)}>
			<span class="muted">{num(r, 2)} %</span>
			<span class="num">{eur(payment(loan, r / 100, 12 * term))}</span>
		</button>
	{/each}
</div>

<h2>Dostanem túto hypotéku?</h2>
<p class="cap">Orientačný výpočet podľa limitov NBS ({lim.source}). Nejde o rozhodnutie banky; banky majú aj vlastné pravidlá.</p>
<section class="calc afford">
	<div class="inputs">
		<Field label="Čistý príjem domácnosti" unit="€/mes." step={50} value={income} set={(v) => (income = v)} />
		<Field label="Splátky iných úverov" unit="€/mes." step={10} value={otherPay} set={(v) => (otherPay = v)} />
		<Field label="Dospelí v domácnosti" value={adults} set={(v) => (adults = Math.max(1, Math.min(6, Math.round(v))))} />
		<Field label="Deti" value={kids} set={(v) => (kids = Math.max(0, Math.min(10, Math.round(v))))} />
		<Field label="Zostatok iných úverov" unit="€" step={1000} value={otherDebt} set={(v) => (otherDebt = v)} />
	</div>
	<div class="result">
		<span class="label">Najvyšší úver podľa príjmu a LTV</span>
		<span class="big"><Roll text={eur(aff.maxLoan)} /></span>
		<table>
			<tbody>
				<tr>
					<td>Splátka so stresovou sadzbou {pct(aff.stressRate, 2)} na {lim.stress_years} rokov</td>
					<td class="r">{eur(aff.stressPayment)}</td>
				</tr>
				<tr>
					<td>Najvyššia povolená splátka: {pct(lim.dsti, 0)} z (príjem − životné minimum {eur(subsistence, 2)}) − iné splátky</td>
					<td class="r">{eur(aff.maxPaymentDsti)}</td>
				</tr>
				<tr><td>DSTI (splátky k príjmu)</td><td class="r"><span class="status" class:ok={aff.dstiOk}>{aff.dstiOk ? 'Spĺňa' : 'Nespĺňa'}</span></td></tr>
				<tr><td>DTI (dlh najviac {lim.dti}-násobok ročného príjmu)</td><td class="r"><span class="status" class:ok={aff.dtiOk}>{aff.dtiOk ? 'Spĺňa' : 'Nespĺňa'}</span></td></tr>
				<tr><td>LTV (úver najviac {pct(lim.ltv, 0)} hodnoty)</td><td class="r"><span class="status" class:ok={aff.ltvOk}>{aff.ltvOk ? 'Spĺňa' : 'Nespĺňa'}</span></td></tr>
			</tbody>
		</table>
	</div>
</section>
<p class="cap">
	Životné minimum od {new Date(zm.valid_from).toLocaleDateString('sk-SK')}: {eur(zm.first_adult, 2)} prvý dospelý, {eur(zm.other_adult, 2)} ďalší,
	{eur(zm.child, 2)} dieťa. Pri žiadateľoch nad 40 rokov, ktorí by splácali po 65. roku, je limit DTI nižší. Mladí do 35 rokov môžu v rámci výnimky
	dostať až {lim.dti_young_exception}-násobok.
</p>

<h2 id="sadzby">Aktuálne sadzby</h2>
<h3>Priemer nových hypoték podľa fixácie (ECB)</h3>
<table>
	<thead><tr><th>Fixácia</th><th class="r">{period(rates.period)}</th><th class="r">Pred rokom</th></tr></thead>
	<tbody>
		{#each ['A', ...ecbCodes] as c}
			{@const s = ecb[c].series}
			<tr>
				<td>{c === 'A' ? 'Všetky úvery' : ecb[c].label}</td>
				<td class="r">{pct(s.at(-1)![1] / 100, 2)}</td>
				<td class="r muted">{pct(s.at(-13)![1] / 100, 2)}</td>
			</tr>
		{/each}
	</tbody>
</table>
<div class="gap">
	<LineChart
		x={x5.map(period)}
		series={[
			{ name: 'Všetky', values: ecb.A.series.map(([, v]) => v), color: 'var(--own)', width: 2.5 },
			...ecbCodes.map((c, i) => ({
				name: ecb[c].label.replace('Fixácia ', '').replace('Pohyblivá a fixácia ', ''),
				values: x5.map((p) => ecb[c].series.find(([q]) => q === p)?.[1] ?? null),
				color: SERIES[i],
				width: 1.5
			}))
		]}
		format={(v) => `${num(v, 2)} %`}
		tick={(v) => `${num(v, 1)} %`}
		xTickEvery={12}
	/>
</div>
<p class="cap">
	Úrokové sadzby nových úverov domácnostiam na bývanie na Slovensku, posledných 5 rokov. Kategória „nad 10 rokov“ má málo úverov, preto kolíše.
</p>

<h3>Ponuky bánk</h3>
<div class="scroll">
	<table>
		<thead><tr><th>Banka</th><th>Fixácia</th><th class="r">Sadzba od</th><th class="r">Max. LTV</th><th>Overené</th><th></th></tr></thead>
		<tbody>
			{#each bankRows as b}
				<tr class:stale={b.stale}>
					<td>{b.bank}</td>
					<td>{fixLabel(b.fixation)}</td>
					<td class="r">{pct(b.rate / 100, 2)}</td>
					<td class="r">{b.max_ltv} %</td>
					<td class="small">{new Date(b.checked).toLocaleDateString('sk-SK')}{b.stale ? ', staršie ako 45 dní' : ''}</td>
					<td class="r"><button class="btn" onclick={() => useOffer(b.rate, b.fixation)}>Použiť</button></td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
<p class="cap">
	Inzerované sadzby „od“ pre najlepších klientov; skutočná sadzba závisí od LTV, príjmu a ďalších produktov banky. Zapisujeme ich ručne raz mesačne podľa
	<a href={rates.banks.checked_via}>prehľadu ponúk</a>; pred rozhodnutím si ich overte priamo v banke.
</p>

<style>
	.lede {
		margin: 0 0 8px;
		font-size: 16px;
		color: var(--fg-2);
	}
	.lede b {
		font-weight: 500;
		color: var(--fg);
	}
	.calc {
		display: grid;
		grid-template-columns: minmax(0, 360px) minmax(0, 1fr);
		gap: 56px;
		margin-top: 32px;
		padding-top: 28px;
		border-top: 1px solid var(--line);
	}
	.afford {
		margin-top: 20px;
	}
	.inputs :global(.slider) {
		margin: 4px 0 0;
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
		text-align-last: right;
	}
	.result {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	.label {
		font-size: 13px;
		color: var(--muted);
	}
	.big {
		margin: 2px 0 14px;
		font-size: 40px;
		line-height: 1.15;
		font-weight: 600;
		letter-spacing: -0.03em;
		font-variant-numeric: tabular-nums;
	}
	.split {
		display: flex;
		height: 12px;
	}
	.split i {
		display: block;
		height: 100%;
		transition: width 450ms var(--ease);
	}
	.split .own {
		border-radius: 3px 0 0 3px;
		background: var(--own);
	}
	.split .int {
		margin-left: 2px;
		border-radius: 0 3px 3px 0;
		background: var(--rent);
	}
	.split + .cap {
		margin: 10px 0 18px;
	}
	.result table td {
		color: var(--fg-2);
	}
	.result table td.r {
		color: var(--fg);
		white-space: nowrap;
	}
	.gap {
		margin-top: 24px;
	}
	details {
		margin-top: 20px;
	}
	details table {
		margin-top: 12px;
	}
	.rategrid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
		gap: 2px;
		margin: 16px -10px 0;
	}
	.cell {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		padding: 8px 10px;
		border: 0;
		border-radius: 6px;
		background: transparent;
		font-size: 14px;
		transition: background-color 120ms;
	}
	.cell .muted {
		font-size: 12px;
	}
	@media (hover: hover) {
		.cell:hover {
			background: var(--soft);
		}
	}
	.cell.on {
		background: color-mix(in oklab, var(--own) 12%, transparent);
	}
	.cell.on .num {
		color: var(--own);
		font-weight: 500;
	}
	.status {
		white-space: nowrap;
	}
	.status::before {
		content: '';
		display: inline-block;
		width: 6px;
		height: 6px;
		margin-right: 6px;
		vertical-align: 0.15em;
		border-radius: 50%;
		background: var(--bad);
	}
	.status.ok::before {
		background: var(--good);
	}
	tr.stale td {
		color: var(--muted);
	}
	td .btn {
		margin: -4px 0;
	}
	@media (max-width: 820px) {
		.calc {
			grid-template-columns: minmax(0, 1fr);
			gap: 24px;
		}
	}
</style>
