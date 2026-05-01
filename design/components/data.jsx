// Data — covers every spec entity: Currencies, StorageLocations, StorageAccounts,
// IncomeSources, ExpenseCategories (with budget + tags + frequency), Transactions (income+expense),
// Recurring, Snapshots, Catalog suggestions.

const MONTHS_12 = ['May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr'];

const trends = {
  balance: [5800,6020,6180,6460,6820,6980,7210,7790,8080,8410,8620,8890],
  income:  [2100,2240,2180,2360,2520,2480,2610,2790,2880,3010,3120,3280],
  expense: [1820,1940,2010,1960,2090,2140,2250,2180,2310,2430,2520,2590],
  profit:  [280,300,170,400,430,340,360,610,570,580,600,690],
};

const BASE_CCY = 'USD';
const RATES_AS_OF = '2026-04-19';   // last refreshed
const TODAY       = '2026-04-22';   // → 3 days stale → warn

const currencies = [
  { code: 'USD', name: 'US Dollar',       symbol: '$', rate: 1.0000, isBase: true,  manual:false },
  { code: 'EUR', name: 'Euro',            symbol: '€', rate: 1.0820, isBase: false, manual:false },
  { code: 'GBP', name: 'British Pound',   symbol: '£', rate: 1.2640, isBase: false, manual:false },
  { code: 'BYN', name: 'Belarus. Rouble', symbol: 'Br',rate: 0.3090, isBase: false, manual:true  },
];

// Helper: convert any (amount, ccy) → base USD using the rates table.
const toBase = (amount, ccy) => {
  const r = currencies.find(c => c.code === ccy);
  return amount * (r ? r.rate : 1);
};

const storageLocations = [
  { id: 1, name: 'Revolut', accounts: [
    { id: 11, ccy: 'USD', balance: 4820.15, growth: +180 },
    { id: 12, ccy: 'EUR', balance: 770.00,  growth: -40  },
  ]},
  { id: 2, name: 'Wise',    accounts: [
    { id: 21, ccy: 'USD', balance: 2730.00, growth: +320 },
  ]},
  { id: 3, name: 'Cash',    accounts: [
    { id: 31, ccy: 'USD', balance: 134.56,  growth: -22  },
  ]},
];

const accounts = storageLocations.flatMap(l => l.accounts.map(a => ({ ...a, location: l.name })));

const categoriesExp = [
  { id:'groceries', name:'Groceries',     icon:'cart',      color:'var(--accent-soft)',  fg:'var(--accent-ink)',  budgeted:900,  actual:842.30, frequency:'monthly', tags:['food','essentials']         },
  { id:'rent',      name:'Rent',          icon:'home',      color:'#e8e4f7',             fg:'#4b3a8c',            budgeted:1200, actual:1200,   frequency:'monthly', tags:['housing','fixed']           },
  { id:'transport', name:'Transport',     icon:'car',       color:'#e4eef7',             fg:'#2e5478',            budgeted:300,  actual:218.40, frequency:'monthly', tags:['mobility']                  },
  { id:'coffee',    name:'Coffee',        icon:'coffee',    color:'#f3e6d7',             fg:'#7a4b1a',            budgeted:120,  actual:142.80, frequency:'monthly', tags:['food','non-essential']      },
  { id:'subs',      name:'Subscriptions', icon:'tv',        color:'#f7e4ec',             fg:'#8c2f50',            budgeted:70,   actual:68.94,  frequency:'monthly', tags:['digital','recurring']       },
  { id:'health',    name:'Health',        icon:'heart',     color:'#ffe4e4',             fg:'#a33a3a',            budgeted:200,  actual:112.00, frequency:'monthly', tags:['wellbeing']                 },
  { id:'insurance', name:'Insurance',     icon:'piggy',     color:'#eee4d4',             fg:'#6b4a1a',            budgeted:480,  actual:480,    frequency:'annual',  tags:['fixed','protection']        },
];
const categoriesInc = [
  { id:'salary',    name:'Salary',    icon:'briefcase', color:'var(--income-soft)', fg:'var(--income-ink)' },
  { id:'freelance', name:'Freelance', icon:'zap',       color:'#e4f2eb',            fg:'#1f6a43' },
  { id:'dividend',  name:'Dividends', icon:'trend',     color:'#e0efe6',            fg:'#275c41' },
];

// Transactions store original currency + amount; UI converts to base for sums.
const transactions = [
  { id:1, date:'2026-04-20', type:'income',  category:'freelance', account:'Wise · USD',    ccy:'USD', amount:  360.00, note:'Upwork #482' },
  { id:2, date:'2026-04-19', type:'expense', category:'groceries', account:'Revolut · EUR', ccy:'EUR', amount:  -68.40, note:'Lidl' },
  { id:3, date:'2026-04-17', type:'income',  category:'salary',    account:'Wise · USD',    ccy:'USD', amount: 3200.00, note:'Northwind' },
  { id:4, date:'2026-04-16', type:'expense', category:'coffee',    account:'Cash · USD',    ccy:'USD', amount:   -4.80, note:'Blue Bottle' },
  { id:5, date:'2026-04-14', type:'expense', category:'rent',      account:'Revolut · USD', ccy:'USD', amount:-1200.00, note:'April rent' },
  { id:6, date:'2026-04-12', type:'income',  category:'dividend',  account:'Wise · USD',    ccy:'USD', amount:   28.14, note:'Aave' },
  { id:7, date:'2026-04-10', type:'expense', category:'transport', account:'Revolut · EUR', ccy:'EUR', amount:  -42.20, note:'Metro' },
  { id:8, date:'2026-04-08', type:'expense', category:'subs',      account:'Wise · USD',    ccy:'USD', amount:   -9.99, note:'Spotify' },
  { id:9, date:'2026-04-05', type:'expense', category:'health',    account:'Revolut · USD', ccy:'USD', amount:  -52.00, note:'Pharmacy' },
  { id:10,date:'2026-04-02', type:'expense', category:'groceries', account:'Revolut · EUR', ccy:'EUR', amount:  -84.10, note:'Carrefour' },
];

// Recurring expenses with explicit frequency for annualization.
const recurring = [
  { id:1, name:'Rent',      amount:1200,  nextDate:'May 01', icon:'home',  category:'rent',      frequency:'monthly' },
  { id:2, name:'Spotify',   amount:9.99,  nextDate:'May 08', icon:'tv',    category:'subs',      frequency:'monthly' },
  { id:3, name:'Gym',       amount:42.0,  nextDate:'May 12', icon:'heart', category:'health',    frequency:'monthly' },
  { id:4, name:'iCloud+',   amount:2.99,  nextDate:'May 18', icon:'phone', category:'subs',      frequency:'monthly' },
  { id:5, name:'Insurance', amount:480,   nextDate:'Aug 01', icon:'piggy', category:'insurance', frequency:'annual'  },
];

// Snapshots — same date is one "Set" (group) per spec; a row per (date, location, ccy).
const snapshots = [
  { id:1, date:'2026-04-21', location:'Revolut', ccy:'USD', balance:4820.15 },
  { id:2, date:'2026-04-21', location:'Revolut', ccy:'EUR', balance:770.00  },
  { id:3, date:'2026-04-21', location:'Wise',    ccy:'USD', balance:2730.00 },
  { id:4, date:'2026-04-21', location:'Cash',    ccy:'USD', balance:134.56  },
  { id:5, date:'2026-03-31', location:'Revolut', ccy:'USD', balance:4640.00 },
  { id:6, date:'2026-03-31', location:'Revolut', ccy:'EUR', balance:810.00  },
  { id:7, date:'2026-03-31', location:'Wise',    ccy:'USD', balance:2410.00 },
  { id:8, date:'2026-03-31', location:'Cash',    ccy:'USD', balance:156.00  },
  { id:9, date:'2026-02-28', location:'Revolut', ccy:'USD', balance:4380.00 },
  { id:10,date:'2026-02-28', location:'Revolut', ccy:'EUR', balance:790.00  },
  { id:11,date:'2026-02-28', location:'Wise',    ccy:'USD', balance:2240.00 },
  { id:12,date:'2026-02-28', location:'Cash',    ccy:'USD', balance:178.00  },
];

// Catalog of common items, surfaced as autocomplete in the New / Edit modals.
const catalog = {
  expense: [
    { name:'Rent',         category:'rent',      typical:1200 },
    { name:'Spotify',      category:'subs',      typical:9.99 },
    { name:'Netflix',      category:'subs',      typical:14.99 },
    { name:'iCloud+',      category:'subs',      typical:2.99 },
    { name:'Gym',          category:'health',    typical:42 },
    { name:'Pharmacy',     category:'health',    typical:50 },
    { name:'Lidl',         category:'groceries', typical:75 },
    { name:'Carrefour',    category:'groceries', typical:80 },
    { name:'Metro',        category:'transport', typical:42 },
    { name:'Blue Bottle',  category:'coffee',    typical:5 },
  ],
  income: [
    { name:'Northwind salary', category:'salary',    typical:3200 },
    { name:'Upwork',           category:'freelance', typical:360 },
    { name:'Aave dividends',   category:'dividend',  typical:28 },
  ],
};

window.DATA = {
  MONTHS_12, BASE_CCY, RATES_AS_OF, TODAY, trends,
  currencies, storageLocations, accounts,
  categoriesExp, categoriesInc, transactions, recurring, snapshots,
  catalog, toBase,
};
