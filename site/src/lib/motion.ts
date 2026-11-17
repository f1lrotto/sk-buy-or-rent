// Motion rules shared by the pages: direct manipulation updates on the same frame, discrete changes animate.
import { tick } from 'svelte';
import type { Attachment } from 'svelte/attachments';
import { prefersReducedMotion } from 'svelte/motion';

export const EASE = 'cubic-bezier(0.23, 1, 0.32, 1)';

/** True while a value the user is dragging or typing is being applied. */
export const motion = { instant: false };

export const calm = () => motion.instant || prefersReducedMotion.current;

/** Call right before applying a dragged or typed value: transitions are skipped for that update. */
export async function direct() {
	if (motion.instant) return;
	motion.instant = true;
	const root = document.documentElement;
	root.classList.add('still');
	await tick();
	void root.offsetWidth;
	root.classList.remove('still');
	motion.instant = false;
}

/** Fades the element in again when `key` changes, such as when a sentence changes shape. */
export function fadeOnChange(key: unknown): Attachment<HTMLElement> {
	return (el) => {
		const prev = last.get(el);
		last.set(el, key);
		if (prev !== undefined && prev !== key && !calm())
			el.animate([{ opacity: 0.2, transform: 'translateY(4px)' }, { opacity: 1, transform: 'none' }], { duration: 240, easing: EASE });
	};
}
const last = new WeakMap<Element, unknown>();
