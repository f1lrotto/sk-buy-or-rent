import type { Areas, History } from '#lib/data.ts';

export async function load({ fetch }) {
	const [history, areas] = await Promise.all(['history', 'areas'].map((f) => fetch(`/data/${f}.json`).then((r) => r.json())));
	return { history: history as History, areas: areas as Areas };
}
