<script lang="ts">
	import '@fontsource-variable/geist';
	import '../app.css';
	import { page } from '$app/state';
	import { onNavigate } from '$app/navigation';

	let { children, data } = $props();
	const links = [
		['/', 'Kalkulačka'],
		['/hypoteka', 'Hypotéka', ' a sadzby'],
		['/mapa', 'Mapa', ' a vývoj'],
		['/metodika', 'Metodika']
	];
	const stale = $derived(Object.values(data.latest.sources).filter((s) => s.stale));
	const wide = $derived(page.url.pathname === '/');

	// Pages cross-fade; the header keeps its own view-transition name, so it stays put.
	onNavigate((nav) => {
		if (!document.startViewTransition || nav.from?.url.pathname === nav.to?.url.pathname) return;
		return new Promise((resolve) => {
			document.startViewTransition(async () => {
				resolve();
				await nav.complete;
			});
		});
	});
</script>

<header>
	<a class="brand" href="/">Kúpiť či prenajať</a>
	<nav>
		{#each links as [href, label, more]}
			<a {href} aria-current={page.url.pathname === href ? 'page' : undefined}>{label}{#if more}<span class="more">{more}</span>{/if}</a>
		{/each}
	</nav>
	<span class="updated">Údaje k {new Date(data.latest.generated).toLocaleDateString('sk-SK')}</span>
</header>

{#if stale.length}
	<p class="banner">
		Niektoré zdroje sa tento mesiac nepodarilo aktualizovať ({stale.map((s) => s.name).join(', ')}). Zobrazujeme ich posledné platné údaje.
		<a href="/metodika#aktualizacia">Podrobnosti</a>
	</p>
{/if}

<main class:wide>
	{@render children()}
</main>

<footer class:wide>
	<p>
		Údaje: NBS, ŠÚ SR, ECB, Eurostat, Realitná únia SR, realitymap.sk, Deloitte, ŠNA, GKÚ. Ceny a nájmy sú ponukové, nie realizované. Nejde o
		finančné poradenstvo. <a href="/metodika">Metodika</a>
	</p>
</footer>

<style>
	header {
		position: sticky;
		top: 0;
		z-index: 20;
		height: var(--header);
		display: flex;
		align-items: center;
		gap: 32px;
		padding: 0 24px;
		background: var(--bg);
		border-bottom: 1px solid var(--line);
		view-transition-name: header;
	}
	:global(::view-transition-old(header)),
	:global(::view-transition-new(header)) {
		animation: none;
	}
	.brand {
		font-weight: 600;
		letter-spacing: -0.015em;
		color: var(--fg);
		text-decoration: none;
		white-space: nowrap;
	}
	nav {
		display: flex;
		gap: 22px;
	}
	nav a {
		color: var(--muted);
		text-decoration: none;
		white-space: nowrap;
	}
	nav a[aria-current='page'] {
		color: var(--fg);
	}
	@media (hover: hover) {
		nav a:hover {
			color: var(--fg);
		}
	}
	.updated {
		margin-left: auto;
		font-size: 13px;
		color: var(--muted);
		white-space: nowrap;
	}
	.banner {
		margin: 0;
		padding: 8px 24px;
		font-size: 13px;
		background: var(--warn-bg);
		border-bottom: 1px solid var(--line);
	}
	main {
		max-width: 1000px;
		margin: 0 auto;
		padding: 44px 32px 24px;
	}
	main.wide {
		max-width: none;
		padding: 0;
	}
	footer {
		max-width: 1000px;
		margin: 32px auto 0;
		padding: 0 32px 40px;
		font-size: 12px;
		line-height: 1.5;
		color: var(--muted);
	}
	footer p {
		margin: 0;
		padding-top: 20px;
		border-top: 1px solid var(--line);
		max-width: 680px;
	}
	/* On the calculator the footer sits under the results column, right of the inputs. */
	footer.wide {
		max-width: none;
		margin: 0;
		padding: 0 56px 40px calc(328px + 56px);
	}
	@media (max-width: 960px) {
		header {
			gap: 16px;
			padding: 0 16px;
			overflow-x: auto;
		}
		.brand,
		.updated {
			display: none;
		}
		nav {
			gap: 16px;
		}
		main {
			padding: 32px 20px 16px;
		}
		footer,
		footer.wide {
			padding: 0 20px 32px;
		}
	}
	@media (max-width: 560px) {
		nav .more {
			display: none;
		}
	}
</style>
