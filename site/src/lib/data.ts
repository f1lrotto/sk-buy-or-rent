// Types for the JSON files that pipeline/build.py writes to static/data/.

export interface Check {
	source: string;
	value: number;
	period: string;
	note?: string;
	per?: 'byt';
}
export interface Figure {
	value: number;
	source: string;
	period: string;
	note?: string;
	n?: number;
	checks?: Check[];
}
export interface Place {
	id: string;
	name: string;
	level: 'kraj' | 'mesto' | 'mestska-cast';
	kraj: string;
	okres?: string;
	price: Figure;
	rent: Figure;
	wage: Figure;
	growth: { nbs_cagr: number; from: string; nbs_yoy: number; su_yoy?: number; ru_yoy?: number };
	listings?: { sale: number; rent: number };
	quality: 'standard' | 'indicative';
}
export interface SourceStatus {
	name: string;
	url: string;
	frequency: string;
	period: string;
	stale: boolean;
	error?: string;
	fetched?: string;
}
export interface Latest {
	generated: string;
	sources: Record<string, SourceStatus>;
	defaults: { rate: number; rate_period: string; rent_growth: number; rent_growth_period: string; paid_rent_yoy: number };
	places: Place[];
	warnings: string[];
}
export interface BankOffer {
	bank: string;
	fixation: number;
	rate: number;
	max_ltv: number;
	checked: string;
	stale: boolean;
}
export interface Rates {
	period: string;
	rate: number;
	ecb: Record<string, { label: string; series: [string, number][] }>;
	ecb_total_since_2008: [string, number][];
	banks: { checked_via: string; offers: BankOffer[] };
}
export interface Rule {
	text?: string;
	source: string;
	url: string;
	[k: string]: unknown;
}
export interface Rules {
	as_of: string;
	tax_year: number;
	income_tax: Rule & { bands: [number | null, number][]; health_insurance_other_income: number };
	securities_exemption: Rule & { holding_years: number; annual_allowance: number };
	flat_sale_exemption: Rule & { holding_years: number };
	rental_income: Rule & { annual_allowance: number };
	young_buyer_bonus: Rule & { share_of_interest: number; max_per_year: number; years: number; max_age: number; income_limit_monthly: number };
	nbs_limits: Rule & {
		dsti: number;
		stress_add: number;
		stress_cap: number;
		stress_add_long_fixation: number;
		stress_years: number;
		dti: number;
		dti_young_exception: number;
		ltv: number;
		ltv_exception: number;
		max_term_years: number;
	};
	subsistence_minimum: Rule & { valid_from: string; first_adult: number; other_adult: number; child: number };
	owner_income: Rule & { revenue_share: number; overview_url: string };
	sna_rent_cap: Rule & { share_of_wage: number };
}
export interface History {
	kraje: string[];
	nbs_annual: (string | number)[][];
	nbs_quarterly: (string | number)[][];
	wage_quarterly: (string | number | null)[][];
	su_index_quarterly: (string | number | null)[][];
	rm_rent_monthly: (string | number)[][];
	rm_sale_monthly: (string | number)[][];
	cp041_monthly: [string, number][];
	towns: Record<string, { start: string; sale_m2: number[]; rent_m2: number[] }>;
}
export interface Areas {
	viewBox: string;
	source: string;
	kraje: { id: string; name: string; d: string }[];
	okresy: { id: string; name: string; kraj: string; d: string }[];
	points: Record<string, [number, number]>;
}

export const KRAJ_SHORT: Record<string, string> = {
	BA: 'Bratislavský',
	TT: 'Trnavský',
	TN: 'Trenčiansky',
	NR: 'Nitriansky',
	ZA: 'Žilinský',
	BB: 'Banskobystrický',
	PO: 'Prešovský',
	KE: 'Košický'
};

/** Short source labels shown beside every figure. */
export const SOURCE_SHORT: Record<string, string> = {
	nbs: 'NBS',
	wage: 'ŠÚ SR',
	su_index: 'ŠÚ SR',
	ecb: 'ECB',
	cp041: 'Eurostat',
	rm_sale: 'realitymap.sk',
	rm_rent: 'realitymap.sk',
	rm_towns: 'realitymap.sk',
	ru: 'Realitná únia SR',
	deloitte: 'Deloitte Rent Index',
	sna: 'ŠNA'
};

export const LEVEL_LABEL: Record<Place['level'], string> = { kraj: 'kraj', mesto: 'mesto', 'mestska-cast': 'mestská časť' };
