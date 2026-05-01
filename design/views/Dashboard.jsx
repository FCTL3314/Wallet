// Dashboard — hero + KPIs + trend tabs + donut breakdown + monthly summary table.
const Dashboard = ({ period, setPeriod, ccy, setCcy, openTx, goto }) => {
  const [chartMode, setChartMode] = React.useState('balance');
  const [convertTo, setConvertTo] = React.useState('USD');
  const D = window.DATA;
  const { trends, MONTHS_12, accounts, categoriesExp, transactions, recurring, currencies, RATES_AS_OF, TODAY } = D;

  // Convert all balances to the chosen base.
  const baseRate = currencies.find(c=>c.code===convertTo)?.rate || 1;
  const conv = (usd) => usd / baseRate;
  const convSym = currencies.find(c=>c.code===convertTo)?.symbol || '';

  const totalsByCcy = accounts.reduce((acc, a) => { acc[a.ccy] = (acc[a.ccy]||0) + a.balance; return acc; }, {});
  const totalUSD = accounts.reduce((s, a) => s + D.toBase(a.balance, a.ccy), 0);
  const totalShown = conv(totalUSD);
  const growthUSD = accounts.reduce((s, a) => s + (a.growth||0), 0);
  const growthPct = +((growthUSD/totalUSD)*100).toFixed(1);

  const whole = Math.floor(totalShown);
  const cents = Math.round((totalShown - whole) * 100).toString().padStart(2, '0');

  const avgIncome  = trends.income.reduce((s,v)=>s+v,0)/trends.income.length;
  const avgExpense = trends.expense.reduce((s,v)=>s+v,0)/trends.expense.length;
  const avgProfit  = trends.profit.reduce((s,v)=>s+v,0)/trends.profit.length;

  // Donut by expense category, this month.
  const PALETTE = ['#5cae93', '#9b87d6', '#6fa3d6', '#d4a373', '#d68aa3', '#e08484', '#caa66a'];
  const donutSegs = categoriesExp.map((c,i) => ({ label: c.name, value: c.actual, color: PALETTE[i % PALETTE.length], icon: c.icon }));
  const expenseTotal = donutSegs.reduce((s,x)=>s+x.value, 0);

  // Monthly summary — last 4 months.
  const summary = MONTHS_12.slice(-4).map((m, i) => {
    const idx = trends.income.length - 4 + i;
    const inc = trends.income[idx], exp = trends.expense[idx], prof = inc - exp;
    return { m, inc, exp, prof, savings: +(prof/inc*100).toFixed(1) };
  }).reverse();

  return (
    <div className="sections">
      <FilterBar period={period} setPeriod={setPeriod} ccy={ccy} setCcy={setCcy} />

      {/* HERO balance */}
      <div className="card hero">
        <div className="hero-main">
          <div className="hero-label">
            <span className="label">Total balance</span>
            <span className={`growth ${growthUSD>0?'growth--up':growthUSD<0?'growth--down':'growth--flat'}`}>
              <Icon name={growthUSD>0?'arrowUp':'arrowDown'} size={11}/>{growthPct>0?'+':''}{growthPct}%
            </span>
            <RateBadge asOf={RATES_AS_OF} today={TODAY}/>
          </div>
          <div className="hero-number">
            <span className="ccy">{convertTo}</span>
            <span>{whole.toLocaleString('en-US')}</span>
            <span className="cents">.{cents}</span>
          </div>
          <div className="hero-foot">
            <span className="convert-to">
              <span className="muted">Show in</span>
              <div className="segmented segmented--mini">
                {currencies.map(c => (
                  <button key={c.code} className={convertTo===c.code?'on':''} onClick={()=>setConvertTo(c.code)}>{c.code}</button>
                ))}
              </div>
            </span>
            <span className="dot-sep"/>
            {Object.entries(totalsByCcy).map(([c,v]) => (
              <span key={c} className="num">{c} {v.toLocaleString('en-US',{maximumFractionDigits:0})}</span>
            ))}
          </div>
          <div className="row" style={{ marginTop: 14, gap: 10 }}>
            <button className="btn btn--primary" onClick={openTx}><Icon name="plus" size={15}/> Add transaction</button>
            <button className="btn"><Icon name="swap" size={15}/> Transfer</button>
            <button className="btn btn--ghost" onClick={()=>goto?.('balances')}><Icon name="plus" size={14}/> New snapshot</button>
          </div>
        </div>
        <div className="hero-side">
          <div className="stat-card">
            <div className="stat-label label">Avg income / mo</div>
            <div className="stat-value" style={{ color:'var(--income-ink)' }}>${avgIncome.toLocaleString('en-US',{maximumFractionDigits:0})}</div>
            <Sparkline data={trends.income} color="var(--income)" width={160} height={34}/>
          </div>
          <hr className="divider"/>
          <div className="stat-card">
            <div className="stat-label label">Avg expense / mo</div>
            <div className="stat-value" style={{ color:'var(--expense-ink)' }}>${avgExpense.toLocaleString('en-US',{maximumFractionDigits:0})}</div>
            <Sparkline data={trends.expense} color="var(--expense)" width={160} height={34}/>
          </div>
          <hr className="divider"/>
          <div className="stat-card">
            <div className="stat-label label">Avg profit / mo</div>
            <div className="stat-value" style={{ color:'var(--accent-ink)' }}>${avgProfit.toLocaleString('en-US',{maximumFractionDigits:0})}</div>
            <Sparkline data={trends.profit} color="var(--accent)" width={160} height={34}/>
          </div>
        </div>
      </div>

      {/* Trend chart */}
      <div className="card">
        <div className="row-between" style={{ marginBottom: 16 }}>
          <div>
            <div className="label">Last 12 months</div>
            <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>
              {chartMode==='balance' ? 'Balance trend' : chartMode==='income' ? 'Income trend' : chartMode==='expense' ? 'Expense trend' : 'Profit trend'}
            </div>
          </div>
          <div className="segmented">
            {[['balance','Balance'],['income','Income'],['expense','Expenses'],['profit','Profit']].map(([k,l]) => (
              <button key={k} className={chartMode===k?'on':''} onClick={()=>setChartMode(k)}>{l}</button>
            ))}
          </div>
        </div>
        <AreaChart data={trends[chartMode]} labels={MONTHS_12} height={240}
          color={chartMode==='profit'?'var(--accent)':chartMode==='income'?'var(--income)':chartMode==='expense'?'var(--expense)':'var(--accent)'}
          formatValue={v => `$${v>=1000?(v/1000).toFixed(1)+'k':v.toFixed(0)}`}/>
      </div>

      {/* Breakdown: donut + table side-by-side */}
      <div className="grid" style={{ gridTemplateColumns:'1fr 1.4fr' }}>
        <div className="card">
          <div className="label">This month</div>
          <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, margin: '4px 0 16px' }}>Where money went</div>
          <div className="donut-wrap">
            <Donut segments={donutSegs} size={180} thickness={20} centerLabel="Total spent" centerValue={`$${expenseTotal.toLocaleString('en-US',{maximumFractionDigits:0})}`}/>
            <div className="donut-legend">
              {donutSegs.map(s => (
                <div key={s.label} className="row-between" style={{ fontSize: 12 }}>
                  <span className="row" style={{ gap: 8 }}>
                    <span className="dot" style={{ background: s.color }}/>
                    <span>{s.label}</span>
                  </span>
                  <span className="num muted">{((s.value/expenseTotal)*100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="card" style={{ padding:0, overflow:'hidden' }}>
          <div className="row-between" style={{ padding:'18px 22px 12px' }}>
            <div>
              <div className="label">Recent</div>
              <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>Latest transactions</div>
            </div>
            <button className="btn btn--ghost" onClick={()=>goto?.('transactions')}>View all <Icon name="arrowRight" size={14}/></button>
          </div>
          <table className="table">
            <thead><tr><th>Date</th><th>Category</th><th>Account</th><th className="right">Amount</th></tr></thead>
            <tbody>
              {transactions.slice(0,6).map(t => {
                const cat = categoriesExp.find(c=>c.id===t.category) || D.categoriesInc.find(c=>c.id===t.category);
                const pos = t.type==='income';
                const baseAmt = D.toBase(Math.abs(t.amount), t.ccy);
                const showConv = t.ccy !== convertTo;
                return (
                  <tr key={t.id}>
                    <td className="muted num">{t.date.slice(5)}</td>
                    <td>
                      <span className="cat-badge">
                        <span className="sw" style={{ background: cat?.color, color: cat?.fg }}><Icon name={cat?.icon} size={13}/></span>
                        {cat?.name}
                      </span>
                    </td>
                    <td className="muted">{t.account}</td>
                    <td className={`right num ${pos?'up':'down'}`} style={{ fontWeight: 600 }}>
                      <div>{pos?'+':'−'}{t.ccy==='USD'?'$':t.ccy==='EUR'?'€':t.ccy==='GBP'?'£':''}{Math.abs(t.amount).toFixed(2)}</div>
                      {showConv && <div className="num muted" style={{ fontSize: 10, fontWeight: 400 }}>≈ {convSym}{conv(baseAmt).toFixed(2)} {convertTo}</div>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Monthly summary + Upcoming */}
      <div className="grid" style={{ gridTemplateColumns:'1.4fr 1fr' }}>
        <div className="card" style={{ padding: 0, overflow:'hidden' }}>
          <div style={{ padding:'18px 22px 12px' }}>
            <div className="label">Cashflow</div>
            <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>Monthly summary</div>
          </div>
          <table className="table">
            <thead><tr><th>Month</th><th className="right">Income</th><th className="right">Expenses</th><th className="right">Profit</th><th className="right">Savings rate</th></tr></thead>
            <tbody>
              {summary.map(s => (
                <tr key={s.m}>
                  <td style={{ fontWeight: 500 }}>{s.m} 2026</td>
                  <td className="right num up">+${s.inc.toLocaleString()}</td>
                  <td className="right num down">−${s.exp.toLocaleString()}</td>
                  <td className="right num" style={{ fontWeight: 600, color: s.prof>=0 ? 'var(--accent-ink)' : 'var(--expense-ink)' }}>${s.prof.toLocaleString()}</td>
                  <td className="right">
                    <span className={`chip ${s.savings>=20?'chip--income':s.savings>=10?'chip--accent':'chip--warn'}`}>{s.savings}%</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="label">Scheduled</div>
          <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, margin: '4px 0 14px' }}>Upcoming</div>
          <div className="stack" style={{ gap: 10 }}>
            {recurring.slice(0,4).map(r => (
              <div key={r.id} className="row-between" style={{ padding: '10px 12px', background:'var(--surface-2)', borderRadius: 14 }}>
                <div className="row">
                  <span className="sw" style={{ width: 32, height: 32, borderRadius: 10, background:'var(--surface)', color:'var(--ink-2)', border:'1px solid var(--hairline)', display:'grid', placeItems:'center' }}>
                    <Icon name={r.icon} size={14}/>
                  </span>
                  <div className="stack" style={{ gap: 2 }}>
                    <span style={{ fontSize: 13, fontWeight: 500 }}>{r.name}</span>
                    <span className="muted" style={{ fontSize: 11 }}>Due {r.nextDate} · {r.frequency}</span>
                  </div>
                </div>
                <span className="num" style={{ fontWeight: 600, fontSize: 14 }}>${r.amount.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

window.Dashboard = Dashboard;
