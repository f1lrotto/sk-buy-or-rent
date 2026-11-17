// Calculator state ⇄ URL query string, so any scenario can be shared as a link.
import type { Inputs, RefixPath } from './calc';

// URL key → input key. Percent inputs are stored in the URL as percent numbers (3.74, not 0.0374).
const NUM: Record<string, [keyof Inputs, boolean]> = {
	a: ['area', false],
	p: ['priceM2', false],
	n: ['rentM2', false],
	d: ['down', true],
	t: ['term', false],
	s: ['stay', false],
	r: ['rate', true],
	f: ['fixation', false],
	bc: ['buyCost', true],
	sc: ['sellCost', true],
	m: ['maintenance', false],
	pt: ['propertyTax', false],
	i: ['insurance', false],
	pg: ['priceGrowth', true],
	rg: ['rentGrowth', true],
	inf: ['inflation', true],
	ir: ['investReturn', true]
};
const BOOL: Record<string, keyof Inputs> = { yb: 'youngBonus', it: 'investTax', st: 'saleTax' };

export function readOverrides(params: URLSearchParams): Partial<Inputs> {
	const out: Record<string, unknown> = {};
	for (const [k, [key, isPct]] of Object.entries(NUM)) {
		const v = params.get(k);
		if (v !== null && Number.isFinite(+v)) out[key] = isPct ? +v / 100 : +v;
	}
	for (const [k, key] of Object.entries(BOOL)) {
		const v = params.get(k);
		if (v !== null) out[key] = v === '1';
	}
	const refix = params.get('rf');
	if (refix && ['same', 'up1', 'down1', 'custom'].includes(refix)) out.refix = refix as RefixPath;
	const rr = params.get('rr');
	if (rr) out.refixRates = rr.split('_').map((x) => +x / 100).filter(Number.isFinite);
	return out as Partial<Inputs>;
}

export function writeOverrides(o: Partial<Inputs>, extra: Record<string, string> = {}): string {
	const q = new URLSearchParams(extra);
	for (const [k, [key, isPct]] of Object.entries(NUM)) {
		const v = o[key];
		if (typeof v === 'number') q.set(k, String(+(isPct ? v * 100 : v).toFixed(4)));
	}
	for (const [k, key] of Object.entries(BOOL)) if (typeof o[key] === 'boolean') q.set(k, o[key] ? '1' : '0');
	if (o.refix) q.set('rf', o.refix);
	if (o.refixRates?.length) q.set('rr', o.refixRates.map((r) => +(r * 100).toFixed(3)).join('_'));
	const s = q.toString();
	return s ? `?${s}` : '';
}
