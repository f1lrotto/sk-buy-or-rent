// Rent vs buy and mortgage maths. Pure functions, no UI. All rates are fractions (0.0374 = 3.74 %).

export type RefixPath = 'same' | 'up1' | 'down1' | 'custom';

export interface Inputs {
	area: number; // m²
	priceM2: number; // € per m²
	rentM2: number; // € per m² a month
	down: number; // share of price paid up front
	term: number; // loan term in years
	stay: number; // planned stay in years: horizon for the answer and the flip point
	rate: number; // mortgage rate for the first fixation
	fixation: number; // years per fixation
	refix: RefixPath;
	refixRates: number[]; // custom rate for each later fixation (refix = 'custom')
	buyCost: number; // purchase costs, share of price
	sellCost: number; // selling costs, share of value
	maintenance: number; // € per m² a month
	propertyTax: number; // € per m² a year
	insurance: number; // € a year
	priceGrowth: number; // a year
	rentGrowth: number; // a year
	inflation: number; // a year, for maintenance, tax and insurance
	investReturn: number; // a year, for whoever invests the monthly difference
	youngBonus: boolean; // §33a tax bonus on interest
	investTax: boolean; // tax portfolio gains (off = ETF held over a year, exempt)
	saleTax: boolean; // tax the gain on a flat sold within the holding period
}

export interface Rules {
	bonusShare: number; // 0.5
	bonusMaxYear: number; // 1200
	bonusYears: number; // 5
	gainTax: number; // income tax + health insurance on taxable gains
	flatHoldingYears: number; // 5
}

export const DEFAULT_RULES: Rules = {
	bonusShare: 0.5,
	bonusMaxYear: 1200,
	bonusYears: 5,
	gainTax: 0.19 + 0.16,
	flatHoldingYears: 5
};

export const DEFAULTS: Omit<Inputs, 'priceM2' | 'rentM2' | 'rate' | 'rentGrowth'> = {
	area: 60,
	down: 0.2,
	term: 30,
	stay: 10,
	fixation: 5,
	refix: 'same',
	refixRates: [],
	buyCost: 0.015,
	sellCost: 0.03,
	maintenance: 1.0,
	propertyTax: 0.5,
	insurance: 80,
	priceGrowth: 0.03,
	inflation: 0.025,
	investReturn: 0.05,
	youngBonus: false,
	investTax: false,
	saleTax: true
};

/** Monthly annuity payment. At 0 % the formula divides by zero, so the payment is the loan over the months. */
export function payment(loan: number, rate: number, months: number): number {
	if (months <= 0) return 0;
	const i = rate / 12;
	return i === 0 ? loan / months : (loan * i) / (1 - (1 + i) ** -months);
}

/** Rate for fixation number k (0 = the first one). */
export function rateFor(inp: Pick<Inputs, 'rate' | 'refix' | 'refixRates'>, k: number): number {
	if (k === 0) return inp.rate;
	switch (inp.refix) {
		case 'up1':
			return inp.rate + 0.01;
		case 'down1':
			return Math.max(0, inp.rate - 0.01);
		case 'custom':
			return inp.refixRates[k - 1] ?? inp.refixRates.at(-1) ?? inp.rate;
		default:
			return inp.rate;
	}
}

export interface Month {
	m: number;
	balance: number;
	payment: number;
	interest: number;
	ownerCost: number; // payment + running costs − young-buyer bonus
	rent: number;
	value: number; // flat value
	owner: number; // owner's net worth if they sold this month
	renter: number; // renter's net worth if they cashed out this month
}

export interface Result {
	price: number;
	loan: number;
	firstPayment: number;
	ownerCost0: number;
	rent0: number;
	months: Month[];
	breakEven: number | null; // first month owner ≥ renter
	totalInterest: number;
	bonusTotal: number;
}

export function simulate(inp: Inputs, rules: Rules = DEFAULT_RULES, horizonMonths?: number): Result {
	const n = 12 * inp.term;
	const horizon = horizonMonths ?? n;
	const price = inp.priceM2 * inp.area;
	const loan = price * (1 - inp.down);
	const rent0 = inp.rentM2 * inp.area;
	const running0 = inp.maintenance * inp.area + (inp.propertyTax * inp.area) / 12 + inp.insurance / 12;
	const monthlyReturn = (1 + inp.investReturn) ** (1 / 12) - 1;
	const fixMonths = Math.max(1, Math.round(12 * inp.fixation));

	let balance = loan;
	let rate = inp.rate;
	let pay = payment(loan, rate, n);
	const firstPayment = pay;
	// The renter invests what the buyer spent up front; each side invests whatever it saves each month.
	let renter = price * inp.down + price * inp.buyCost;
	let renterIn = renter;
	let ownerPf = 0;
	let ownerIn = 0;
	let bonusYear = 0;
	let bonusTotal = 0;
	let totalInterest = 0;
	const months: Month[] = [];
	let breakEven: number | null = null;

	for (let m = 1; m <= horizon; m++) {
		const year = Math.floor((m - 1) / 12);
		if (m > 1 && (m - 1) % fixMonths === 0 && balance > 0) {
			rate = rateFor(inp, (m - 1) / fixMonths);
			pay = payment(balance, rate, n - (m - 1));
		}
		let interest = 0;
		let thisPay = 0;
		if (balance > 0) {
			interest = (balance * rate) / 12;
			thisPay = Math.min(pay, balance + interest);
			balance = Math.max(0, balance + interest - thisPay);
		}
		totalInterest += interest;

		let bonus = 0;
		if (inp.youngBonus && year < rules.bonusYears) {
			if ((m - 1) % 12 === 0) bonusYear = 0;
			bonus = Math.min(interest * rules.bonusShare, rules.bonusMaxYear - bonusYear);
			bonusYear += bonus;
			bonusTotal += bonus;
		}
		const ownerCost = thisPay + running0 * (1 + inp.inflation) ** year - bonus;
		const rent = rent0 * (1 + inp.rentGrowth) ** year;

		renter *= 1 + monthlyReturn;
		ownerPf *= 1 + monthlyReturn;
		if (ownerCost > rent) {
			renter += ownerCost - rent;
			renterIn += ownerCost - rent;
		} else {
			ownerPf += rent - ownerCost;
			ownerIn += rent - ownerCost;
		}

		const value = price * (1 + inp.priceGrowth) ** (m / 12);
		let saleProceeds = value * (1 - inp.sellCost);
		const gain = saleProceeds - price * (1 + inp.buyCost);
		if (inp.saleTax && m < 12 * rules.flatHoldingYears && gain > 0) saleProceeds -= gain * rules.gainTax;
		const taxPf = (pf: number, paidIn: number) =>
			inp.investTax && pf > paidIn ? pf - (pf - paidIn) * rules.gainTax : pf;
		const owner = saleProceeds - balance + taxPf(ownerPf, ownerIn);
		const renterNet = taxPf(renter, renterIn);
		if (breakEven === null && owner >= renterNet) breakEven = m;
		months.push({ m, balance, payment: thisPay, interest, ownerCost, rent, value, owner, renter: renterNet });
	}
	return {
		price,
		loan,
		firstPayment,
		ownerCost0: firstPayment + running0,
		rent0,
		months,
		breakEven,
		totalInterest,
		bonusTotal
	};
}

/** Does buying catch up with renting within the planned stay? */
export function buyingWins(inp: Inputs, rules: Rules = DEFAULT_RULES): boolean {
	return simulate(inp, rules, Math.round(12 * inp.stay)).breakEven !== null;
}

export type FlipKey = 'priceGrowth' | 'investReturn' | 'rate' | 'rentGrowth';

/** The value of `key` at which the answer over the planned stay changes, found by bisection between lo and hi. */
export function flip(inp: Inputs, key: FlipKey, lo: number, hi: number, rules: Rules = DEFAULT_RULES): number | null {
	const wins = (v: number) => buyingWins({ ...inp, [key]: v }, rules);
	const wLo = wins(lo);
	if (wLo === wins(hi)) return null;
	for (let i = 0; i < 40; i++) {
		const mid = (lo + hi) / 2;
		if (wins(mid) === wLo) lo = mid;
		else hi = mid;
	}
	return (lo + hi) / 2;
}

export interface Flips {
	priceGrowth: number | null; // buying stops winning when prices grow less than this
	investReturn: number | null; // buying stops winning when investments return more than this
	rate: number | null; // buying stops winning above this mortgage rate
	quoted: 'priceGrowth' | 'investReturn' | null; // the one closer to its current value
}

export function flips(inp: Inputs, rules: Rules = DEFAULT_RULES): Flips {
	const priceGrowth = flip(inp, 'priceGrowth', -0.3, 0.15, rules);
	const investReturn = flip(inp, 'investReturn', -0.05, 0.4, rules);
	const rate = flip(inp, 'rate', 0, 0.15, rules);
	const dP = priceGrowth === null ? Infinity : Math.abs(priceGrowth - inp.priceGrowth);
	const dR = investReturn === null ? Infinity : Math.abs(investReturn - inp.investReturn);
	const quoted = dP === Infinity && dR === Infinity ? null : dP <= dR ? 'priceGrowth' : 'investReturn';
	return { priceGrowth, investReturn, rate, quoted };
}

export interface Sensitivity {
	key: FlipKey;
	minus: number | null;
	base: number | null;
	plus: number | null;
}

/** Break-even month when each input moves ±1 percentage point. */
export function sensitivity(inp: Inputs, rules: Rules = DEFAULT_RULES): Sensitivity[] {
	const be = (patch: Partial<Inputs>) => simulate({ ...inp, ...patch }, rules).breakEven;
	const base = be({});
	return (['priceGrowth', 'rentGrowth', 'investReturn', 'rate'] as FlipKey[]).map((key) => ({
		key,
		minus: be({ [key]: Math.max(key === 'rate' ? 0 : -1, inp[key] - 0.01) }),
		base,
		plus: be({ [key]: inp[key] + 0.01 })
	}));
}

// ---------- mortgage calculator ----------

export interface YearRow {
	year: number;
	rate: number;
	paid: number;
	interest: number;
	principal: number;
	balance: number;
}

export function amortisation(
	loan: number,
	inp: Pick<Inputs, 'rate' | 'term' | 'fixation' | 'refix' | 'refixRates'>
): { rows: YearRow[]; totalInterest: number; totalPaid: number; payments: { from: number; rate: number; payment: number }[] } {
	const n = 12 * inp.term;
	const fixMonths = Math.max(1, Math.round(12 * inp.fixation));
	let balance = loan;
	let rate = inp.rate;
	let pay = payment(loan, rate, n);
	const payments = [{ from: 1, rate, payment: pay }];
	const rows: YearRow[] = [];
	let row: YearRow = { year: 1, rate, paid: 0, interest: 0, principal: 0, balance };
	for (let m = 1; m <= n; m++) {
		if (m > 1 && (m - 1) % fixMonths === 0 && balance > 0) {
			rate = rateFor(inp, (m - 1) / fixMonths);
			pay = payment(balance, rate, n - (m - 1));
			payments.push({ from: m, rate, payment: pay });
		}
		const interest = (balance * rate) / 12;
		const thisPay = Math.min(pay, balance + interest);
		balance = Math.max(0, balance + interest - thisPay);
		row.paid += thisPay;
		row.interest += interest;
		row.principal += thisPay - interest;
		row.balance = balance;
		if (m % 12 === 0) {
			rows.push(row);
			row = { year: m / 12 + 1, rate, paid: 0, interest: 0, principal: 0, balance };
		}
	}
	const totalInterest = rows.reduce((s, r) => s + r.interest, 0);
	return { rows, totalInterest, totalPaid: loan + totalInterest, payments };
}

export interface Affordability {
	stressRate: number;
	stressPayment: number;
	maxPaymentDsti: number;
	maxLoanDsti: number;
	maxLoanDti: number;
	maxLoan: number;
	dstiOk: boolean;
	dtiOk: boolean;
	ltvOk: boolean;
}

export interface NbsLimits {
	dsti: number;
	stress_add: number;
	stress_cap: number;
	stress_add_long_fixation: number;
	stress_years: number;
	dti: number;
	ltv: number;
}

/** NBS limits for a new housing loan, indicative only. Income is the household's monthly net income. */
export function affordability(
	o: { loan: number; price: number; rate: number; fixation: number; netIncome: number; otherPayments: number; subsistence: number; otherDebt: number },
	lim: NbsLimits
): Affordability {
	const add = o.fixation > 10 ? lim.stress_add_long_fixation : lim.stress_add;
	const stressRate = Math.max(o.rate, Math.min(o.rate + add, lim.stress_cap));
	const months = 12 * lim.stress_years;
	const stressPayment = payment(o.loan, stressRate, months);
	const maxPaymentDsti = Math.max(0, lim.dsti * (o.netIncome - o.subsistence) - o.otherPayments);
	const unit = payment(1, stressRate, months);
	const maxLoanDsti = maxPaymentDsti / unit;
	const maxLoanDti = Math.max(0, lim.dti * 12 * o.netIncome - o.otherDebt);
	return {
		stressRate,
		stressPayment,
		maxPaymentDsti,
		maxLoanDsti,
		maxLoanDti,
		maxLoan: Math.min(maxLoanDsti, maxLoanDti, o.price * lim.ltv),
		dstiOk: stressPayment <= maxPaymentDsti,
		dtiOk: o.loan + o.otherDebt <= lim.dti * 12 * o.netIncome,
		ltvOk: o.loan <= o.price * lim.ltv + 0.5
	};
}
