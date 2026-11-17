import { describe, expect, it } from 'vitest';
import { affordability, amortisation, DEFAULTS, flips, payment, simulate, type Inputs } from './calc';

// The spec's worked example: Žilinský kraj, NBS Q3 2026 price, realitymap Oct 2026 rent, ECB Sep 2026 rate.
const zilina: Inputs = { ...DEFAULTS, priceM2: 2342.21, rentM2: 11.23, rate: 0.0374, rentGrowth: 0.03 };

describe('payment', () => {
	it('matches the spec example and a bank-style figure', () => {
		expect(Math.round(payment(112426, 0.0374, 360))).toBe(520);
		// NBS DSTI example: €168,423.72 at 3.7 % over 30 years is €775.23 a month
		expect(payment(168423.72, 0.037, 360)).toBeCloseTo(775.23, 1);
	});
	it('divides the loan evenly at 0 %', () => {
		expect(payment(112426, 0, 360)).toBeCloseTo(312.29, 2);
	});
});

describe('rent vs buy simulation', () => {
	it('reproduces the Žilinský kraj example', () => {
		const r = simulate(zilina);
		expect(Math.round(r.firstPayment)).toBe(520);
		expect(Math.round(r.ownerCost0)).toBe(589);
		expect(Math.round(r.rent0)).toBe(674);
		expect(r.breakEven).toBe(14);
	});
	it('finds the price-growth flip near −2 % a year over a 10-year stay', () => {
		const f = flips(zilina);
		expect(f.quoted).toBe('priceGrowth');
		expect(f.priceGrowth!).toBeGreaterThan(-0.023);
		expect(f.priceGrowth!).toBeLessThan(-0.018);
	});
	it('re-prices the loan at each refix on the remaining balance', () => {
		const base = simulate(zilina);
		const up = simulate({ ...zilina, refix: 'up1' });
		expect(up.months[59].payment).toBeCloseTo(base.months[59].payment, 6); // month 60: still first fixation
		expect(up.months[60].payment).toBeGreaterThan(base.months[60].payment + 30);
		// the balance after the refix must still reach zero at the end of the term
		expect(up.months.at(-1)!.balance).toBeLessThan(0.01);
	});
	it('caps the young-buyer bonus at €1,200 a year for 5 years', () => {
		const big = { ...zilina, priceM2: 5000, youngBonus: true }; // interest well above €2,400 a year
		const r = simulate(big);
		expect(r.bonusTotal).toBeCloseTo(6000, 6);
	});
	it('taxes a flat sold within 5 years, not after', () => {
		const growth = { ...zilina, priceGrowth: 0.08 };
		const taxed = simulate(growth).months;
		const untaxed = simulate({ ...growth, saleTax: false }).months;
		expect(taxed[35].owner).toBeLessThan(untaxed[35].owner - 1000);
		expect(taxed[60].owner).toBeCloseTo(untaxed[60].owner, 6);
	});
});

describe('amortisation', () => {
	it('repays the loan and splits payments into interest and principal', () => {
		const a = amortisation(112426, { rate: 0.0374, term: 30, fixation: 5, refix: 'same', refixRates: [] });
		const principal = a.rows.reduce((s, r) => s + r.principal, 0);
		expect(principal).toBeCloseTo(112426, 0);
		expect(a.rows).toHaveLength(30);
		expect(a.totalInterest).toBeCloseTo(520.12 * 360 - 112426, -2);
	});
});

describe('affordability', () => {
	it('reproduces the NBS DSTI example', () => {
		// couple with two children, net €2,400, subsistence €770.78, 3.7 % → stressed at 5.7 %
		const a = affordability(
			{ loan: 168000, price: 250000, rate: 0.037, fixation: 5, netIncome: 2400, otherPayments: 0, subsistence: 770.78, otherDebt: 0 },
			{ dsti: 0.6, stress_add: 0.02, stress_cap: 0.06, stress_add_long_fixation: 0.01, stress_years: 30, dti: 8, ltv: 0.8 }
		);
		expect(a.stressRate).toBeCloseTo(0.057, 6);
		expect(a.maxPaymentDsti).toBeCloseTo(977.53, 2);
		expect(a.maxLoanDsti).toBeCloseTo(168423.72, 0);
	});
});
