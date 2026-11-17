<script lang="ts">
	import { onMount } from 'svelte';
	import { replaceState } from '$app/navigation';
	import { affordability, amortisation, payment, type RefixPath } from '#lib/calc.ts';
	import { eur, num, pct, period } from '#lib/format.ts';
	import { writeOverrides } from '#lib/state.ts';
	import LineChart from '#lib/components/LineChart.svelte';

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
</script>

<svelte:head><title>Hypotekárna kalkulačka a aktuálne sadzby | Kúpiť či prenajať</title></svelte:head>

<h1>Hypotéka: splátka, úroky a aktuálne sadzby</h1>
<p class="muted">
	Priemerná sadzba nových hypoték na Slovensku je <strong>{pct(rates.rate / 100, 2)}</strong> (ECB, {period(rates.period)}).
</p>

<section id="kalkulacka" class="grid">
	<div>
		<h2>Úver</h2>
		<div class="fields">
			<label>Cena nehnuteľnosti <span class="in"><input type="number" bind:value={price} step="1000" /> €</span></label>
			<label>Vlastné zdroje <span class="in"><input type="number" bind:value={downPct} step="1" /> %</span></label>
			<label>Doba splácania <span class="in"><input type="number" bind:value={term} min="1" max="40" /> rokov</span></label>
			<label>
				Fixácia
				<select bind:value={fixation}>
					{#each [1, 3, 5, 10] as f}<option value={f}>{fixLabel(f)}</option>{/each}
				</select>
			</label>
			<label>Úroková sadzba <span class="in"><input type="number" bind:value={rate} step="0.01" min="0" /> %</span></label>
			<label>
				Po skončení fixácie
				<select bind:value={refix}>
					<option value="same">rovnaká sadzba</option>
					<option value="up1">o 1 p. b. vyššia</option>
					<option value="down1">o 1 p. b. nižšia</option>
				</select>
			</label>
		</div>
		<input class="slider" type="range" min="0" max="8" step="0.01" bind:value={rate} aria-label="Úroková sadzba" />
	</div>
	<div>
		<h2>Výsledok</h2>
		<p class="big num">{eur(pay0)} <span class="muted small">mesačne</span></p>
		<table>
			<tbody>
				<tr><td>Výška úveru</td><td class="r">{eur(loan)}</td></tr>
				<tr><td>Zaplatené úroky spolu</td><td class="r">{eur(am.totalInterest)}</td></tr>
				<tr><td>Zaplatené spolu</td><td class="r">{eur(am.totalPaid)}</td></tr>
				<tr><td>Splátka pri 0 % (len istina)</td><td class="r">{eur(zero)}</td></tr>
				<tr><td>Z prvej splátky ide na úroky</td><td class="r">{eur((loan * rate) / 1200)}</td></tr>
				{#each refix === 'same' ? [] : am.payments.slice(1, 4) as p}
					<tr><td>Splátka od {Math.ceil(p.from / 12)}. roka pri {pct(p.rate, 2)}</td><td class="r">{eur(p.payment)}</td></tr>
				{/each}
			</tbody>
		</table>
		<p><a href={rentBuyLink}>Použiť tento úver v porovnaní kúpy a nájmu →</a></p>
	</div>
</section>

<h2>Zostatok, úroky a istina po rokoch</h2>
<LineChart
	x={am.rows.map((r) => `${r.year}`)}
	series={[
		{ name: 'Zostatok úveru', values: am.rows.map((r) => r.balance), color: 'var(--own)' },
		{ name: 'Úroky za rok', values: am.rows.map((r) => r.interest * 10), color: 'var(--rent)', dashed: true },
		{ name: 'Istina za rok', values: am.rows.map((r) => r.principal * 10), color: 'var(--good)', dashed: true }
	]}
	format={(v) => `${num(v / 1000)} tis. €`}
	yMin={0}
	xTickEvery={5}
/>
<p class="small muted">Úroky a istina za rok sú pre čitateľnosť zväčšené 10-krát. Os x: rok splácania.</p>
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
<p class="small muted">Úver {eur(loan)} na {term} rokov. Zvýraznená je sadzba najbližšia vašej.</p>
<div class="rategrid">
	{#each grid as r}
		<button class="cell" class:on={Math.abs(r - Math.round(rate * 4) / 4) < 1e-9} onclick={() => (rate = r)}>
			<span class="muted small">{num(r, 2)} %</span>
			<span class="num">{eur(payment(loan, r / 100, 12 * term))}</span>
		</button>
	{/each}
</div>

<h2>Dostanem túto hypotéku?</h2>
<p class="small muted">Orientačný výpočet podľa limitov NBS ({lim.source}). Nejde o rozhodnutie banky; banky majú aj vlastné pravidlá.</p>
<div class="grid">
	<div class="fields">
		<label>Čistý príjem domácnosti <span class="in"><input type="number" bind:value={income} step="50" /> € mesačne</span></label>
		<label>Splátky iných úverov <span class="in"><input type="number" bind:value={otherPay} step="10" /> € mesačne</span></label>
		<label>Dospelí v domácnosti <input type="number" bind:value={adults} min="1" max="6" /></label>
		<label>Deti <input type="number" bind:value={kids} min="0" max="10" /></label>
		<label>Zostatok iných úverov <span class="in"><input type="number" bind:value={otherDebt} step="1000" /> €</span></label>
	</div>
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
			<tr><td>DSTI (splátky k príjmu)</td><td class="r" class:ok={aff.dstiOk} class:no={!aff.dstiOk}>{aff.dstiOk ? 'Spĺňa' : 'Nespĺňa'}</td></tr>
			<tr><td>DTI (dlh najviac {lim.dti}-násobok ročného príjmu)</td><td class="r" class:ok={aff.dtiOk} class:no={!aff.dtiOk}>{aff.dtiOk ? 'Spĺňa' : 'Nespĺňa'}</td></tr>
			<tr><td>LTV (úver najviac {pct(lim.ltv, 0)} hodnoty)</td><td class="r" class:ok={aff.ltvOk} class:no={!aff.ltvOk}>{aff.ltvOk ? 'Spĺňa' : 'Nespĺňa'}</td></tr>
			<tr><td><strong>Najvyšší úver podľa príjmu a LTV</strong></td><td class="r"><strong>{eur(aff.maxLoan)}</strong></td></tr>
		</tbody>
	</table>
</div>
<p class="small muted">
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
<LineChart
	x={x5}
	series={[
		{ name: 'Všetky', values: ecb.A.series.map(([, v]) => v), color: 'var(--own)', width: 2.5 },
		...ecbCodes.map((c, i) => ({
			name: ecb[c].label.replace('Fixácia ', '').replace('Pohyblivá a fixácia ', ''),
			values: x5.map((p) => ecb[c].series.find(([q]) => q === p)?.[1] ?? null),
			color: ['#8b5cf6', '#0d9488', '#ca8a04', '#db2777'][i],
			width: 1.5
		}))
	]}
	format={(v) => `${num(v, 1)} %`}
	xTickEvery={12}
/>
<p class="small muted">
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
					<td class="small">{new Date(b.checked).toLocaleDateString('sk-SK')}{b.stale ? ' (staršie ako 45 dní)' : ''}</td>
					<td><button class="btn" onclick={() => useOffer(b.rate, b.fixation)}>Použiť</button></td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
<p class="small muted">
	Inzerované sadzby „od“ pre najlepších klientov; skutočná sadzba závisí od LTV, príjmu a ďalších produktov banky. Zapisujeme ich ručne raz mesačne podľa
	<a href={rates.banks.checked_via}>prehľadu ponúk</a>; pred rozhodnutím si ich overte priamo v banke.
</p>

<style>
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: 32px;
	}
	@media (max-width: 820px) {
		.grid {
			grid-template-columns: minmax(0, 1fr);
			gap: 8px;
		}
	}
	.fields {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 10px 14px;
	}
	.fields label {
		font-size: 13px;
		display: block;
	}
	.in {
		display: flex;
		align-items: center;
		gap: 6px;
		color: var(--muted);
		white-space: nowrap;
	}
	.slider {
		width: 100%;
		margin-top: 12px;
		accent-color: var(--accent);
	}
	.big {
		font-size: 28px;
		margin: 4px 0 8px;
		font-weight: 600;
	}
	.rategrid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
		gap: 6px;
	}
	.cell {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		border: 1px solid var(--line);
		border-radius: 6px;
		background: var(--bg);
		padding: 6px 8px;
		font-size: 14px;
	}
	.cell:hover {
		background: var(--soft);
	}
	.cell.on {
		border-color: var(--accent);
		box-shadow: inset 0 0 0 1px var(--accent);
	}
	.ok {
		color: var(--good);
	}
	.no {
		color: var(--bad);
	}
	tr.stale td {
		color: var(--muted);
	}
	details {
		margin-top: 8px;
	}
</style>
