<script lang="ts">
	// Text whose digits roll to their new values, like NumberFlow, and which can also hold words ("2 rokoch a 3 mesiacoch").
	// At rest it is plain text, so prerendered HTML and copied text read normally. The digit strips exist only while
	// a number rolls, clipped to the line. A change of shape (another digit count, other words) fades in instead.
	import type { Attachment } from 'svelte/attachments';
	import { calm, EASE } from '#lib/motion.ts';

	let { text }: { text: string } = $props();

	const items = $derived.by(() => {
		let i = 0;
		return (text.match(/\d+|\D+/g) ?? []).map((t) => (/\d/.test(t) ? { digits: [...t].map((c) => ({ d: +c, i: i++ })) } : { w: t }));
	});
	const shape = $derived(items.map((t) => ('w' in t ? 'w' : `d${t.digits.length}`)).join());

	let el: HTMLSpanElement;
	let rolling = $state(false);
	let from = $state(''); // digits before the roll started
	let prev: { text: string; shape: string; widths: number[] } | null = null;
	let timer: ReturnType<typeof setTimeout> | undefined;

	$effect(() => {
		const now = { text, shape, widths: [...el.querySelectorAll('.ph')].map((p) => p.getBoundingClientRect().width) };
		const was = prev;
		prev = now;
		if (!was || was.text === now.text) return;
		if (calm()) {
			rolling = false;
			return;
		}
		if (was.shape !== now.shape) {
			rolling = false;
			el.animate([{ opacity: 0.2 }, { opacity: 1 }], { duration: 220, easing: EASE });
			return;
		}
		from = was.text.replace(/\D/g, '');
		rolling = true;
		clearTimeout(timer);
		timer = setTimeout(() => (rolling = false), 600);
		// a 1 is narrower than an 8, so each digit's box follows the strip
		el.querySelectorAll<HTMLElement>('.dg').forEach((dg, i) => {
			if (was.widths[i] !== now.widths[i])
				dg.animate([{ width: `${was.widths[i]}px` }, { width: `${now.widths[i]}px` }], { duration: 550, easing: EASE });
		});
	});
	$effect(() => () => clearTimeout(timer));

	/** Slides a strip from where it is (or from digit `a`) to digit `b`. */
	function spin(a: number, b: number): Attachment<HTMLElement> {
		return (node) => {
			const running = node.getAnimations();
			const start = running.length ? getComputedStyle(node).transform : `translateY(${-a * 10}%)`;
			running.forEach((x) => x.cancel());
			node.animate([{ transform: start }, { transform: `translateY(${-b * 10}%)` }], { duration: 550, easing: EASE, fill: 'forwards' });
		};
	}
</script>

<span class="roll" class:rolling bind:this={el}
	>{#each items as it}{#if 'w' in it}<span class="w">{it.w}</span>{:else}{#each it.digits as g}<span class="dg"
				><span class="ph">{g.d}</span>{#if rolling}<span class="st" aria-hidden="true" {@attach spin(+(from[g.i] ?? g.d), g.d)}
						>{#each { length: 10 }, n}<span>{n}</span>{/each}</span
					>{/if}</span
			>{/each}{/if}{/each}</span
>

<style>
	.roll {
		white-space: nowrap;
	}
	.dg {
		display: inline-block;
		position: relative;
	}
	.st {
		position: absolute;
		top: 0;
		left: 0;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		user-select: none;
	}
	/* space between digits on the strip, so only one shows in the line while rolling */
	.st span {
		padding-bottom: 0.6em;
	}
	.rolling .ph {
		visibility: hidden;
	}
	.rolling .dg {
		clip-path: inset(-0.15em -0.1em);
		-webkit-mask-image: linear-gradient(transparent, #000 0.2em, #000 calc(100% - 0.2em), transparent);
		mask-image: linear-gradient(transparent, #000 0.2em, #000 calc(100% - 0.2em), transparent);
	}
</style>
