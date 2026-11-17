import type { Latest, Rates, Rules } from '#lib/data.ts';

export const prerender = true;
export const trailingSlash = 'never';

export async function load({ fetch }) {
	const [latest, rates, rules] = await Promise.all(
		['latest', 'rates', 'rules'].map((f) => fetch(`/data/${f}.json`).then((r) => r.json()))
	);
	return { latest: latest as Latest, rates: rates as Rates, rules: rules as Rules };
}
