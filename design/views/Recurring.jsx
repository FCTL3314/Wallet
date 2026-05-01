// Regular Expenses — budget vs actual, frequency, tags, annual projection.
const Recurring = ({ period, setPeriod, ccy, setCcy }) => {
  const { categoriesExp, recurring } = window.DATA;
  const totalBudgetMonthly = categoriesExp.reduce((s,c)=> s + (c.frequency==='annual' ? c.budgeted/12 : c.budgeted), 0);
  const totalActual        = categoriesExp.reduce((s,c)=> s + c.actual, 0);
  const annualProjection   = categoriesExp.reduce((s,c)=> s + (c.frequency==='annual' ? c.budgeted : c.budgeted*12), 0);
  const overCount = categoriesExp.filter(c=>c.actual>c.budgeted).length;

  const annualRecurring = recurring.reduce((s,r)=> s + (r.frequency==='annual' ? r.amount : r.amount*12), 0);

  return (
    <div className="sections">
      <FilterBar period={period} setPeriod={setPeriod} ccy={ccy} setCcy={setCcy}
        actions={<button className="btn btn--primary"><Icon name="plus" size={15}/> New category</button>}/>

      <div className="kpis">
        <BaseStatCard label="Budget · monthly avg" value={totalBudgetMonthly} foot={<span className="muted">{categoriesExp.length} categories</span>}/>
        <BaseStatCard label="Actual spent · this month" value={totalActual} variant="expense" growth={-3.2}/>
        <BaseStatCard label="Annual projection" value={annualProjection} variant="profit" foot={<span className="muted">If pace continues</span>}/>
        <BaseStatCard label="Over budget"  value={overCount.toString()} ccy="" foot={<span className={`chip ${overCount>0?'chip--warn':'chip--income'}`}>{overCount>0?'Needs attention':'On track'}</span>}/>
      </div>

      <div className="card" style={{ padding:0, overflow:'hidden' }}>
        <div className="row-between" style={{ padding:'18px 22px' }}>
          <div>
            <div className="label">Budget vs actual · this month</div>
            <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>Expense categories</div>
          </div>
        </div>
        <table className="table">
          <thead><tr>
            <th>Category · tags</th>
            <th>Freq.</th>
            <th className="right">Budgeted</th>
            <th className="right">Actual</th>
            <th className="right">Remaining</th>
            <th style={{ width:'22%' }}>Progress</th>
            <th className="right">Annual</th>
            <th className="right">Actions</th>
          </tr></thead>
          <tbody>
            {categoriesExp.map(c => {
              const remaining = c.budgeted - c.actual;
              const pct = (c.actual/c.budgeted)*100;
              const state = pct>100?'over':pct>=80?'warn':'good';
              const annual = c.frequency==='annual' ? c.budgeted : c.budgeted*12;
              return (
                <tr key={c.id}>
                  <td>
                    <div className="stack" style={{ gap: 4 }}>
                      <span className="cat-badge"><span className="sw" style={{ background:c.color, color:c.fg }}><Icon name={c.icon} size={13}/></span>{c.name}</span>
                      <TagChips tags={c.tags || []}/>
                    </div>
                  </td>
                  <td><span className={`chip ${c.frequency==='annual'?'chip--accent':''}`}>{c.frequency}</span></td>
                  <td className="right num">${c.budgeted.toFixed(2)}</td>
                  <td className="right num">${c.actual.toFixed(2)}</td>
                  <td className="right num" style={{ color: remaining<0?'var(--expense-ink)':'var(--ink)', fontWeight: 500 }}>{remaining<0?'−':''}${Math.abs(remaining).toFixed(2)}</td>
                  <td><div className="row" style={{ gap: 8 }}><div className={`bar bar--${state}`} style={{ flex: 1 }}><span style={{ width: `${Math.min(100,pct)}%` }}/></div><span className="num muted" style={{ fontSize: 12, minWidth: 40, textAlign:'right' }}>{pct.toFixed(0)}%</span></div></td>
                  <td className="right num muted">${annual.toLocaleString('en-US',{maximumFractionDigits:0})}</td>
                  <td className="right"><EditDeleteActions/></td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan="2" style={{ fontWeight: 600 }}>Total</td>
              <td className="right num" style={{ fontWeight: 600 }}>${categoriesExp.reduce((s,c)=>s+c.budgeted,0).toFixed(2)}</td>
              <td className="right num" style={{ fontWeight: 600 }}>${totalActual.toFixed(2)}</td>
              <td/>
              <td/>
              <td className="right num" style={{ fontWeight: 600 }}>${annualProjection.toLocaleString('en-US',{maximumFractionDigits:0})}</td>
              <td/>
            </tr>
          </tfoot>
        </table>
      </div>

      <div className="card">
        <div className="row-between" style={{ marginBottom: 14 }}>
          <div>
            <div className="label">Scheduled</div>
            <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>Upcoming recurring</div>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <span className="label">Annual cost ≈</span>
            <span className="num" style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600 }}>${annualRecurring.toLocaleString('en-US',{maximumFractionDigits:0})}</span>
          </div>
        </div>
        <div className="grid" style={{ gridTemplateColumns:'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
          {recurring.map(r => {
            const annual = r.frequency==='annual' ? r.amount : r.amount*12;
            return (
              <div key={r.id} style={{ padding:'14px 16px', background:'var(--surface-2)', borderRadius: 16 }}>
                <div className="row-between" style={{ marginBottom: 10 }}>
                  <div className="row">
                    <span style={{ width:32, height:32, borderRadius:10, background:'var(--surface)', border:'1px solid var(--hairline)', display:'grid', placeItems:'center' }}><Icon name={r.icon} size={14}/></span>
                    <span style={{ fontWeight: 500 }}>{r.name}</span>
                  </div>
                  <span className={`chip ${r.frequency==='annual'?'chip--accent':''}`}>{r.frequency==='annual'?'1×/yr':'1×/mo'}</span>
                </div>
                <div className="row-between">
                  <span className="muted" style={{ fontSize: 12 }}>Next {r.nextDate}</span>
                  <span className="num" style={{ fontWeight: 600 }}>${r.amount.toFixed(2)}</span>
                </div>
                <hr className="divider" style={{ margin: '10px 0 6px' }}/>
                <div className="row-between">
                  <span className="label">Annual</span>
                  <span className="num muted" style={{ fontSize: 12 }}>${annual.toLocaleString('en-US',{maximumFractionDigits:0})}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
window.Recurring = Recurring;
