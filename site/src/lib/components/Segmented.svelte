<script lang="ts" generics="T extends string">
	// A segmented control (Bits UI ToggleGroup) whose white thumb slides to the chosen option.
	import { ToggleGroup } from 'bits-ui';

	let { value, options, onchange, label }: { value: T; options: [T, string][]; onchange: (v: T) => void; label: string } = $props();

	let root = $state<HTMLElement | null>(null);
	let thumb = $state({ x: 0, w: 0 });
	let ready = $state(false);

	$effect(() => {
		void value;
		const el = root;
		if (!el) return;
		const place = () => {
			const on = el.querySelector<HTMLElement>('[data-state="on"]');
			if (on) thumb = { x: on.offsetLeft, w: on.offsetWidth };
		};
		place();
		// The first placement does not slide in from the left edge.
		const raf = requestAnimationFrame(() => (ready = true));
		const ro = new ResizeObserver(place);
		ro.observe(el);
		return () => {
			cancelAnimationFrame(raf);
			ro.disconnect();
		};
	});
</script>

<ToggleGroup.Root type="single" {value} onValueChange={(v) => v && onchange(v as T)} bind:ref={root} class="seg {ready ? 'ready' : ''}" aria-label={label}>
	<span class="seg-thumb" style:width="{thumb.w}px" style:transform="translateX({thumb.x}px)" hidden={!thumb.w}></span>
	{#each options as [v, l] (v)}
		<ToggleGroup.Item value={v} class="seg-item">{l}</ToggleGroup.Item>
	{/each}
</ToggleGroup.Root>
