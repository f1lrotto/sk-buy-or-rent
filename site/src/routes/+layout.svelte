<script lang="ts">
	import { page } from '$app/state';
	import '../app.css';

	let { children, data } = $props();
	const links = [
		['/', 'Kúpiť či prenajať'],
		['/hypoteka', 'Hypotéka a sadzby'],
		['/mapa', 'Mapa a vývoj'],
		['/metodika', 'Metodika']
	];
	const stale = $derived(Object.values(data.latest.sources).filter((s) => s.stale));
</script>

<header>
	<nav>
		<a class="brand" href="/">Kúpiť či prenajať</a>
		<div class="links">
			{#each links.slice(1) as [href, label]}
				<a {href} aria-current={page.url.pathname === href ? 'page' : undefined}>{label}</a>
			{/each}
		</div>
	</nav>
</header>

<main>
	{#if stale.length}
		<p class="banner">
			Niektoré zdroje sa tento mesiac nepodarilo aktualizovať ({stale.map((s) => s.name).join(', ')}). Zobrazujeme ich posledné
			platné údaje. <a href="/metodika#aktualizacia">Podrobnosti</a>
		</p>
	{/if}
	{@render children()}
</main>

<footer>
	<p>
		Údaje: NBS, ŠÚ SR, ECB, Eurostat, Realitná únia SR, realitymap.sk, Deloitte, ŠNA, GKÚ. Aktualizované
		{new Date(data.latest.generated).toLocaleDateString('sk-SK')}. Ceny a nájmy sú ponukové, nie realizované.
		Nejde o finančné poradenstvo. <a href="/metodika">Metodika</a>
	</p>
</footer>

<style>
	header {
		border-bottom: 1px solid var(--line);
		background: var(--bg);
		position: sticky;
		top: 0;
		z-index: 10;
	}
	nav {
		max-width: var(--max);
		margin: 0 auto;
		padding: 10px 16px;
		display: flex;
		gap: 16px;
		align-items: center;
		flex-wrap: wrap;
	}
	.brand {
		font-weight: 600;
		color: var(--fg);
		text-decoration: none;
	}
	.links {
		display: flex;
		gap: 14px;
		flex-wrap: wrap;
		font-size: 14px;
	}
	.links a {
		color: var(--muted);
		text-decoration: none;
	}
	.links a[aria-current='page'],
	.links a:hover {
		color: var(--fg);
	}
	main {
		max-width: var(--max);
		margin: 0 auto;
		padding: 16px;
	}
	.banner {
		background: var(--warn-bg);
		border-radius: 8px;
		padding: 8px 12px;
		font-size: 14px;
	}
	footer {
		max-width: var(--max);
		margin: 32px auto 0;
		padding: 16px;
		border-top: 1px solid var(--line);
		font-size: 13px;
		color: var(--muted);
	}
</style>
