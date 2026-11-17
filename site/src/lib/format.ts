// Slovak number formatting: space as thousands separator, comma as decimal point, real minus sign.

const nf = (digits: number) =>
	new Intl.NumberFormat('sk-SK', { minimumFractionDigits: digits, maximumFractionDigits: digits });

export function num(v: number, digits = 0): string {
	return nf(digits).format(v).replace('-', '−');
}
export function eur(v: number, digits = 0): string {
	return `${num(v, digits)} €`;
}
export function pct(v: number, digits = 1, sign = false): string {
	const s = num(v * 100, digits);
	return `${sign && v > 0 ? '+' : ''}${s} %`;
}

const MONTHS = ['január', 'február', 'marec', 'apríl', 'máj', 'jún', 'júl', 'august', 'september', 'október', 'november', 'december'];
/** "2026-10" → "október 2026"; quarters and other strings pass through. */
export function period(p: string): string {
	const m = /^(\d{4})-(\d{2})$/.exec(p);
	return m ? `${MONTHS[+m[2] - 1]} ${m[1]}` : p;
}

/** "14 mesiacov", "2 roky a 3 mesiace" */
export function months(n: number): string {
	const y = Math.floor(n / 12);
	const m = n % 12;
	const mw = (k: number) => (k === 1 ? 'mesiac' : k >= 2 && k <= 4 ? 'mesiace' : 'mesiacov');
	const yw = (k: number) => (k === 1 ? 'rok' : k >= 2 && k <= 4 ? 'roky' : 'rokov');
	if (n < 24) return `${n} ${mw(n)}`;
	return m ? `${y} ${yw(y)} a ${m} ${mw(m)}` : `${y} ${yw(y)}`;
}

/** "v Žilinskom kraji", "v meste Žilina", "v mestskej časti Bratislava – Petržalka" */
export function inPlace(p: { name: string; level: string }): string {
	if (p.level === 'kraj') {
		const adj = p.name.replace(' kraj', '');
		const loc = adj.endsWith('ý') ? adj.slice(0, -1) + 'om' : adj.endsWith('y') ? adj.slice(0, -1) + 'om' : adj;
		return `v ${loc} kraji`;
	}
	return p.level === 'mesto' ? `v meste ${p.name}` : `v mestskej časti ${p.name}`;
}

/** Locative after "po": "po 18 mesiacoch", "po 2 rokoch a 1 mesiaci" */
export function monthsAfter(n: number): string {
	const y = Math.floor(n / 12);
	const m = n % 12;
	const mw = (k: number) => (k === 1 ? 'mesiaci' : 'mesiacoch');
	const yw = (k: number) => (k === 1 ? 'roku' : 'rokoch');
	if (n < 24) return `${n} ${mw(n)}`;
	return m ? `${y} ${yw(y)} a ${m} ${mw(m)}` : `${y} ${yw(y)}`;
}
