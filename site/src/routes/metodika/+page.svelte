<script lang="ts">
	import { eur, num, pct, period } from '#lib/format.ts';

	let { data } = $props();
	const { latest, rules, rates } = data;
	const S = latest.sources;
	const zil = latest.places.find((p) => p.id === 'za')!;
	const order = ['nbs', 'su_index', 'wage', 'ecb', 'cp041', 'ru', 'rm_sale', 'rm_rent', 'rm_towns', 'deloitte', 'sna'];
	const towns = latest.places.filter((p) => p.level !== 'kraj');
	const fetched = (s: { fetched?: string }) => (s.fetched ? new Date(s.fetched).toLocaleDateString('sk-SK') : '–');
</script>

<svelte:head><title>Metodika | Kúpiť či prenajať</title></svelte:head>

<article>
	<h1>Ako počítame</h1>
	<p>
		Táto stránka vysvetľuje, odkiaľ pochádzajú čísla v kalkulačkách, ako ich spracúvame a kde majú limity. Uvádzame len to, čo výpočet skutočne robí.
		Dáta sme naposledy aktualizovali {new Date(latest.generated).toLocaleDateString('sk-SK')}.
	</p>
	<nav class="toc small">
		<ol>
			<li><a href="#zdroje">Odkiaľ pochádzajú údaje</a></li>
			<li><a href="#aktualizacia">Ako často sa údaje aktualizujú</a></li>
			<li><a href="#kombinacia">Ako kombinujeme zdroje</a></li>
			<li><a href="#kontrola">Kontrola údajov a výpadky</a></li>
			<li><a href="#vzorka">Veľkosť vzorky a označenie kvality</a></li>
			<li><a href="#priemery">Vyhladenie a priemery</a></li>
			<li><a href="#vypocet">Výpočet</a></li>
			<li><a href="#predpoklady">Predvolené predpoklady</a></li>
			<li><a href="#sadzby">Sadzby a ponuky bánk</a></li>
			<li><a href="#dostupnost">Pravidlá NBS pre hypotéky</a></li>
			<li><a href="#dane">Dane a štátna podpora</a></li>
			<li><a href="#limity">Obmedzenia</a></li>
			<li><a href="#zmeny">Zmeny metodiky a opravy</a></li>
		</ol>
	</nav>

	<h2 id="zdroje">1. Odkiaľ pochádzajú údaje</h2>
	<p>
		Na Slovensku neexistuje verejný register skutočných predajných cien bytov. Kataster kúpne ceny eviduje, no podľa § 68 katastrálneho zákona ich
		nezverejňuje. Žiadny oficiálny zdroj nezverejňuje ani výšku nájomného za kraje či mestá. Preto kombinujeme oficiálne štatistiky so stavovskými a
		komerčnými zdrojmi a pri každom čísle uvádzame, odkiaľ je.
	</p>
	<div class="scroll">
		<table>
			<thead><tr><th>Zdroj</th><th>Čo z neho berieme</th><th>Typ</th></tr></thead>
			<tbody>
				<tr><td><a href={S.nbs.url}>NBS</a></td><td>Ponukové ceny bytov €/m² za kraje, štvrťročne od 2002. NBS ich zostavuje z databázy NARKS a inzercie United Classifieds.</td><td>oficiálny</td></tr>
				<tr><td><a href={S.su_index.url}>ŠÚ SR, sp3801qr</a></td><td>Index realizačných cien z kúpnych zmlúv v katastri, kraje od 2022. Dáva len zmeny, nie €/m².</td><td>oficiálny</td></tr>
				<tr><td><a href={S.wage.url}>ŠÚ SR, np3112qr</a></td><td>Priemerná nominálna mesačná mzda za kraje, štvrťročne. Za mestá a okresy ŠÚ SR štvrťročné mzdy nezverejňuje.</td><td>oficiálny</td></tr>
				<tr><td><a href={S.ecb.url}>ECB MIR</a></td><td>Priemerné sadzby nových úverov na bývanie na Slovensku, spolu a podľa fixácie. Údaje do ECB posiela NBS.</td><td>oficiálny</td></tr>
				<tr><td><a href={S.cp041.url}>Eurostat HICP CP041</a></td><td>Index skutočne platených nájmov za celé Slovensko; predvolený rast nájomného.</td><td>oficiálny</td></tr>
				<tr><td><a href={rules.sna_rent_cap.url}>Štátna nájomná agentúra</a></td><td>Vzorec maximálneho nájomného v štátom podporených bytoch; zobrazujeme ho ako porovnanie.</td><td>oficiálny</td></tr>
				<tr><td><a href={S.ru.url}>Realitná únia SR</a></td><td>Ponukové ceny starších a novších bytov v krajských mestách mesačne a rebríček 30 miest štvrťročne.</td><td>stavovský</td></tr>
				<tr><td><a href={S.rm_rent.url}>realitymap.sk</a></td><td>Ponukové nájomné a ceny za kraje a mestá, mesačne od mája 2023, s počtom inzerátov.</td><td>komerčný</td></tr>
				<tr><td><a href={S.deloitte.url}>Deloitte Rent Index</a></td><td>Priemerné ponukové nájomné za byt v 9 mestách, štvrťročne; porovnanie.</td><td>komerčný</td></tr>
				<tr><td>GKÚ SR</td><td>Hranice krajov, okresov a obcí pre mapu a priradenie miest ku krajom.</td><td>oficiálny</td></tr>
			</tbody>
		</table>
	</div>
	<p><strong>Všetky ceny a nájmy sú ponukové</strong>, teda za koľko sa byt ponúka, nie za koľko sa predal alebo prenajal.</p>

	<h2 id="aktualizacia">2. Ako často sa údaje aktualizujú</h2>
	<p>
		Skript stiahne všetky automatické zdroje 15. dňa v mesiaci, uloží si ich surové kópie a z nich prepočíta dáta webu. Deloitte Rent Index (PDF) a
		ponuky bánk zapisujeme ručne. Oficiálne zdroje vychádzajú s oneskorením, preto pri každom čísle uvádzame obdobie, za ktoré platí.
	</p>
	<div class="scroll">
		<table>
			<thead><tr><th>Zdroj</th><th>Frekvencia</th><th>Najnovšie obdobie</th><th>Stiahnuté</th><th>Stav</th></tr></thead>
			<tbody>
				{#each order.filter((k) => S[k]) as k}
					<tr>
						<td>{S[k].name}</td>
						<td>{S[k].frequency}</td>
						<td>{period(S[k].period)}</td>
						<td>{fetched(S[k])}</td>
						<td class:bad={S[k].stale}>{S[k].stale ? `zastarané: ${S[k].error ?? ''}` : 'aktuálne'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<h2 id="kombinacia">3. Ako kombinujeme zdroje</h2>
	<ul>
		<li><strong>Kraje:</strong> cena z NBS, nájom z realitymap.sk, mzda z ŠÚ SR. Pre porovnanie ukazujeme cenu z realitymap.sk a strop ŠNA.</li>
		<li>
			<strong>Krajské mestá:</strong> cena z Realitnej únie (priemer starších 2- a 3-izbových bytov), nájom z realitymap.sk. Pre porovnanie ukazujeme cenu z
			realitymap.sk a nájom z Deloitte.
		</li>
		<li><strong>Ďalšie mestá z rebríčka Realitnej únie:</strong> cena starších 3-izbových bytov z rebríčka, nájom z realitymap.sk.</li>
		<li><strong>Ostatné okresné mestá a mestské časti:</strong> cena aj nájom z realitymap.sk, lebo iný zdroj pre ne neexistuje.</li>
		<li><strong>Mzda pre mestá</strong> je mzda celého kraja.</li>
	</ul>
	<p>
		Zdroje sa systematicky líšia. Realitná únia počíta len staršie byty, realitymap.sk všetky inzeráty vrátane novostavieb, preto je realitymap.sk v cenách
		vyššie: v septembri 2026 v 30 mestách rebríčka Realitnej únie v mediáne o 11 %. Napríklad pre Žilinský kraj uvádza NBS {eur(zil.price.value)}/m² za {zil.price.period} a realitymap.sk
		{eur(zil.price.checks?.[0]?.value ?? 0)}/m². Deloitte uvádza nájom za byt, nie za m², a jeho byty sú v priemere menšie ako 60 m².
	</p>

	<h2 id="kontrola">4. Kontrola údajov a výpadky</h2>
	<ul>
		<li>Každá hodnota sa smie od predchádzajúceho mesiaca alebo štvrťroka zmeniť najviac o 25 %. Mzdy porovnávame s rovnakým štvrťrokom pred rokom, lebo sú sezónne.</li>
		<li>Krajské zdroje musia mať všetkých 8 krajov.</li>
		<li>Ak zdroj kontrolou neprejde alebo sa ho nepodarí načítať, web ponechá jeho posledné platné údaje a označí ho ako zastaraný v tabuľke vyššie a v hlavičke webu.</li>
		<li>Ponuky bánk staršie ako 45 dní zobrazujeme sivou farbou.</li>
	</ul>

	<h2 id="vzorka">5. Veľkosť vzorky a označenie kvality</h2>
	<ul>
		<li><strong>Štandardný údaj:</strong> v každom z posledných 3 mesiacov aspoň 50 inzerátov na predaj a 30 na prenájom.</li>
		<li><strong>Orientačný údaj:</strong> aspoň 20 na predaj a 10 na prenájom; v kalkulačke je označený.</li>
		<li><strong>Nezobrazujeme:</strong> menej inzerátov. Pre také miesto použite kraj; hodnoty nikdy nedopĺňame odhadom.</li>
	</ul>
	<p>
		Teraz zobrazujeme {towns.length} miest a mestských častí, z toho {towns.filter((t) => t.quality === 'indicative').length} orientačne. Pri každom nájme
		uvádzame počet inzerátov za posledný mesiac.
	</p>

	<h2 id="priemery">6. Vyhladenie a priemery</h2>
	<p>
		Nájom a cenu z realitymap.sk berieme ako priemer posledných 3 mesiacov, lebo počty inzerátov z mesiaca na mesiac kolíšu. realitymap.sk zverejňuje
		aritmetický priemer ceny za m², nie medián, takže drahé byty ho mierne zvyšujú. NBS a Realitná únia zverejňujú priemery za svoje vzorky. Cenu za m² rátajú
		všetky zdroje pre každý inzerát zvlášť.
	</p>

	<h2 id="vypocet">7. Výpočet</h2>
	<table class="calc">
		<tbody>
			<tr><td>Cena bytu</td><td><code>P = cena za m² × plocha</code></td></tr>
			<tr><td>Úver</td><td><code>L = P × (1 − vlastné zdroje)</code></td></tr>
			<tr><td>Splátka</td><td><code>M = L·i / (1 − (1+i)^−n)</code>, <code>i = sadzba/12</code>, <code>n = 12 × roky</code>; pri 0 % <code>M = L / n</code></td></tr>
			<tr><td>Nová fixácia</td><td>Splátka sa prepočíta zo zostatku úveru na zvyšné mesiace pri novej sadzbe.</td></tr>
			<tr><td>Náklady vlastníka</td><td>Splátka + údržba + daň z nehnuteľnosti + poistenie; ostatné náklady rastú s infláciou.</td></tr>
			<tr><td>Nájom</td><td>Nájom za m² × plocha, rastie tempom rastu nájomného raz ročne.</td></tr>
			<tr><td>Roky mzdy</td><td><code>P / (12 × priemerná mzda)</code></td></tr>
			<tr><td>Pomer ceny k nájmu</td><td><code>cena za m² / (12 × nájom za m²)</code>; hrubý výnos je jeho prevrátená hodnota.</td></tr>
		</tbody>
	</table>
	<p>
		<strong>Čistý majetok, mesiac po mesiaci.</strong> Nájomca na začiatku investuje vlastné zdroje a náklady na kúpu, ktoré by inak zaplatil. Každý mesiac
		ten, kto platí menej, investuje rozdiel s očakávaným výnosom. Majetok vlastníka je hodnota bytu po nákladoch na predaj, mínus zostatok úveru, plus jeho
		investície. <strong>Bod zlomu</strong> je prvý mesiac, v ktorom majetok vlastníka dosiahne majetok nájomcu.
	</p>
	<p>
		<strong>Bod zlomu predpokladov.</strong> Pre rast cien a pre výnos investícií zvlášť hľadáme bisekciou hodnotu, pri ktorej sa odpoveď počas plánovanej doby
		bývania zmení. Odpoveď uvádza ten, ktorý je bližšie k súčasnému predpokladu. Rátame s plánovanou dobou bývania, nie s dobou splácania: za 30 rokov kúpa
		dobehne nájom takmer vždy, čo nič nehovorí človeku, ktorý sa môže o 10 rokov sťahovať.
	</p>
	<p>
		<strong>Príklad:</strong> Žilinský kraj, cena NBS 2 342 €/m² (Q3 2026), nájom 11,23 €/m², 60 m², 20 % vlastných zdrojov, 3,74 % na 30 rokov. Splátka 520 €,
		náklady vlastníka 589 €, nájom 674 €. Kúpa dobehne nájom v 14. mesiaci a pri pobyte 10 rokov vyhrá nájom, len ak ceny bytov klesajú rýchlejšie ako
		približne 2 % ročne. Tento príklad overujú automatické testy kalkulačky.
	</p>

	<h2 id="predpoklady">8. Predvolené predpoklady</h2>
	<div class="scroll">
		<table>
			<thead><tr><th>Predpoklad</th><th class="r">Hodnota</th><th>Prečo</th></tr></thead>
			<tbody>
				<tr><td>Plocha bytu</td><td class="r">60 m²</td><td>Typický 2- až 3-izbový byt</td></tr>
				<tr><td>Vlastné zdroje</td><td class="r">20 %</td><td>Štandardný limit LTV 80 %</td></tr>
				<tr><td>Doba splácania</td><td class="r">30 rokov</td><td>Limit NBS</td></tr>
				<tr><td>Plánovaná doba bývania</td><td class="r">10 rokov</td><td>Obdobie odpovede</td></tr>
				<tr><td>Úroková sadzba</td><td class="r">{pct(latest.defaults.rate / 100, 2)}</td><td>ECB, priemer nových úverov, {period(latest.defaults.rate_period)}</td></tr>
				<tr><td>Fixácia</td><td class="r">5 rokov</td><td>Predvolená voľba; ďalšie fixácie s rovnakou sadzbou</td></tr>
				<tr><td>Náklady na kúpu / predaj</td><td class="r">1,5 % / 3 %</td><td>Poplatky, znalec, kataster / realitná kancelária</td></tr>
				<tr><td>Údržba a fond opráv</td><td class="r">1 €/m² mesačne</td><td>Odhad</td></tr>
				<tr><td>Daň z nehnuteľnosti</td><td class="r">0,5 €/m² ročne</td><td>Líši sa podľa obce</td></tr>
				<tr><td>Poistenie</td><td class="r">80 € ročne</td><td>Odhad</td></tr>
				<tr><td>Rast cien bytov</td><td class="r">3 % ročne</td><td>Konzervatívne pod dlhodobým priemerom NBS (6–8 % od 2002), ktorý zobrazujeme vedľa</td></tr>
				<tr><td>Rast nájomného</td><td class="r">{pct(latest.defaults.rent_growth)}</td><td>10-ročný priemer Eurostat CP041</td></tr>
				<tr><td>Inflácia nákladov</td><td class="r">2,5 % ročne</td><td>Mierne nad cieľom ECB</td></tr>
				<tr><td>Výnos investícií</td><td class="r">5 % ročne</td><td>Zmiešané portfólio; voľby 2,5 % a 7 %</td></tr>
			</tbody>
		</table>
	</div>

	<h2 id="sadzby">9. Sadzby a ponuky bánk</h2>
	<p>
		Priemer ECB je sadzba nových úverov na bývanie dohodnutých v danom mesiaci, vážená ich objemom. Údaje zbiera NBS od bánk. Sadzby bánk sú
		inzerované sadzby „od“, ktoré dostanú najlepší klienti; zapisujeme ich ručne a pri každej uvádzame dátum overenia. Teraz zobrazujeme
		{rates.banks.offers.length} ponúk.
	</p>

	<h2 id="dostupnost">10. Pravidlá NBS pre hypotéky</h2>
	<p>{rules.nbs_limits.text}</p>
	<p class="cap">
		Zdroj: <a href={rules.nbs_limits.url}>{rules.nbs_limits.source}</a>. Životné minimum: {rules.subsistence_minimum.source}. Výsledok je orientačný, nejde o
		rozhodnutie banky.
	</p>

	<h2 id="dane">11. Dane a štátna podpora</h2>
	<ul>
		<li><strong>Daňový bonus pre mladých:</strong> {rules.young_buyer_bonus.text} (<a href={rules.young_buyer_bonus.url}>{rules.young_buyer_bonus.source}</a>)</li>
		<li><strong>Predaj bytu:</strong> {rules.flat_sale_exemption.text} (<a href={rules.flat_sale_exemption.url}>{rules.flat_sale_exemption.source}</a>)</li>
		<li><strong>Investície:</strong> {rules.securities_exemption.text} (<a href={rules.securities_exemption.url}>{rules.securities_exemption.source}</a>)</li>
		<li><strong>Prenájom:</strong> {rules.rental_income.text} (<a href={rules.rental_income.url}>{rules.rental_income.source}</a>)</li>
	</ul>
	<p>
		<strong>Zjednodušenia:</strong> zdaniteľný zisk zdaňujeme sadzbou {pct(rules.income_tax.bands[0][1], 0)} plus zdravotné poistenie
		{pct(rules.income_tax.health_insurance_other_income, 0)}; vyššie pásma dane a oslobodenie 500 € neuplatňujeme. Bonus pre mladých počítame mesačne z
		úrokov namiesto ročného zúčtovania. Neriešime úver zo ŠFRB, stavebné sporenie ani odklad splátok pri narodení dieťaťa. Pravidlá platia k
		{new Date(rules.as_of).toLocaleDateString('sk-SK')} pre daňový rok {rules.tax_year}.
	</p>

	<h2 id="limity">12. Obmedzenia</h2>
	<ul>
		<li>Ponukové ceny nie sú realizačné. Za posledný rok sa ponukové ceny NBS a realizačné ceny ŠÚ SR v krajoch líšili až o niekoľko percentuálnych bodov (pozri <a href="/mapa">mapu</a>).</li>
		<li>Ponukové nájmy nie sú platené nájmy. Platené nájmy (Eurostat) vzrástli za posledný rok o {pct(latest.defaults.paid_rent_yoy)}; porovnanie s ponukovými nájmami je na <a href="/mapa">mape</a>.</li>
		<li>V menších mestách je málo inzerátov a čísla kolíšu.</li>
		<li>Mzdy sú krajské priemery, nie mzdy v meste ani medián.</li>
		<li>Výsledok veľmi závisí od rastu cien a výnosu investícií; preto ukazujeme bod zlomu a citlivosť.</li>
		<li>Kalkulačka slúži na orientáciu a nenahrádza finančné poradenstvo, znalecký posudok ani ponuku banky.</li>
	</ul>

	<h2 id="zmeny">13. Zmeny metodiky a opravy</h2>
	<ul>
		<li><strong>v1, november 2026:</strong> prvá verzia. Ceny z NBS a Realitnej únie, nájmy z realitymap.sk, porovnania z Deloitte a ŠNA.</li>
	</ul>
	<p>
		Našli ste chybné číslo? Napíšte nám cez
		<a href="https://github.com/f1lrotto/sk-buy-or-rent/issues">GitHub</a>. Uveďte miesto, číslo a zdroj, s ktorým ho porovnávate.
	</p>
</article>

<style>
	article {
		max-width: 720px;
	}
	article :global(p),
	article :global(li) {
		line-height: 1.6;
	}
	.toc {
		margin: 24px 0 8px;
		padding: 14px 0;
		border-top: 1px solid var(--line);
		border-bottom: 1px solid var(--line);
	}
	.toc ol {
		columns: 2;
		column-gap: 32px;
		margin: 0;
		padding-left: 20px;
		color: var(--muted);
	}
	.toc li {
		padding: 2px 0;
	}
	.toc a {
		color: var(--fg-2);
		text-decoration: none;
	}
	@media (hover: hover) {
		.toc a:hover {
			color: var(--fg);
			text-decoration: underline;
		}
	}
	@media (max-width: 600px) {
		.toc ol {
			columns: 1;
		}
	}
	h2[id] {
		scroll-margin-top: calc(var(--header) + 16px);
	}
	.bad {
		color: var(--bad);
	}
	code {
		font-size: 13px;
		background: var(--soft);
		padding: 1px 4px;
		border-radius: 4px;
	}
	.calc td:first-child {
		white-space: nowrap;
		color: var(--muted);
	}
</style>
