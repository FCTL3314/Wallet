// Transactions view — unified income + expense list, filters, tags, base-currency conversion.
const Transactions = ({ period, setPeriod, ccy, setCcy, openTx }) => {
  const D = window.DATA;
  const { transactions, categoriesExp, categoriesInc, accounts, BASE_CCY, RATES_AS_OF, TODAY } = D;
  const allCats = [...categoriesExp, ...categoriesInc];
  const [type, setType] = React.useState('all');
  const [cat, setCat] = React.useState('all');
  const [acct, setAcct] = React.useState('all');
  const [q, setQ] = React.useState('');

  const filtered = transactions.filter(t => {
    if (type!=='all' && t.type!==type) return false;
    if (cat!=='all' && t.category!==cat) return false;
    if (acct!=='all' && t.account!==acct) return false;
    if (q) {
      const hay = (t.note+' '+(allCats.find(c=>c.id===t.category)?.name||'')).toLowerCase();
      if (!hay.includes(q.toLowerCase())) return false;
    }
    return true;
  });

  // Sums in base currency (USD).
  const inSum  = filtered.filter(t=>t.type==='income').reduce((s,t)=>s + D.toBase(t.amount, t.ccy),0);
  const outSum = filtered.filter(t=>t.type==='expense').reduce((s,t)=>s + D.toBase(Math.abs(t.amount), t.ccy),0);
  const net    = inSum - outSum;

  return (
    <div className="sections">
      <FilterBar period={period} setPeriod={setPeriod} ccy={ccy} setCcy={setCcy}
        actions={<>
          <RateBadge asOf={RATES_AS_OF} today={TODAY}/>
          <button className="btn btn--primary" onClick={openTx}><Icon name="plus" size={15}/> Add transaction</button>
        </>}/>

      <div className="kpis">
        <BaseStatCard label="Income"   value={inSum}  variant="income"  foot={<span className="muted">{filtered.filter(t=>t.type==='income').length} entries</span>}/>
        <BaseStatCard label="Expenses" value={outSum} variant="expense" foot={<span className="muted">{filtered.filter(t=>t.type==='expense').length} entries</span>}/>
        <BaseStatCard label="Net"      value={net}    variant={net>=0?'profit':'expense'} growth={+((net/(inSum||1))*100).toFixed(1)}/>
      </div>

      <div className="card" style={{ padding: 0, overflow:'hidden' }}>
        <div style={{ padding: '16px 22px', display:'flex', alignItems:'center', gap: 12, flexWrap:'wrap' }}>
          <div className="segmented">
            {[['all','All'],['income','Income'],['expense','Expenses']].map(([k,l]) => (
              <button key={k} className={type===k?'on':''} onClick={()=>setType(k)}>{l}</button>
            ))}
          </div>
          <select className="select" value={cat} onChange={e=>setCat(e.target.value)} style={{ padding:'8px 12px' }}>
            <option value="all">All categories</option>
            {allCats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <select className="select" value={acct} onChange={e=>setAcct(e.target.value)} style={{ padding:'8px 12px' }}>
            <option value="all">All accounts</option>
            {accounts.map(a => <option key={a.id} value={`${a.location} · ${a.ccy}`}>{a.location} · {a.ccy}</option>)}
          </select>
          <div style={{ flex: 1, position: 'relative', minWidth: 200 }}>
            <Icon name="search" size={15} style={{ position:'absolute', left: 14, top:'50%', transform:'translateY(-50%)', color:'var(--ink-3)' }}/>
            <input className="input" style={{ paddingLeft: 38, width:'100%' }} placeholder="Search notes…" value={q} onChange={e=>setQ(e.target.value)}/>
          </div>
        </div>
        {filtered.length===0 ? (
          <EmptyState icon="tag" title="No transactions" subtitle="Try widening the period or clearing filters."
            action={<button className="btn btn--primary" onClick={openTx}><Icon name="plus" size={15}/> Add transaction</button>}/>
        ) : (
          <table className="table">
            <thead><tr><th>Date</th><th>Category · tags</th><th>Account</th><th>Note</th><th className="right">Amount</th><th className="right">Actions</th></tr></thead>
            <tbody>
              {filtered.map(t => {
                const c = allCats.find(x=>x.id===t.category);
                const pos = t.type==='income';
                const sym = t.ccy==='USD'?'$':t.ccy==='EUR'?'€':t.ccy==='GBP'?'£':'';
                const baseAmt = D.toBase(Math.abs(t.amount), t.ccy);
                const isForeign = t.ccy !== BASE_CCY;
                return (
                  <tr key={t.id}>
                    <td className="muted num">{t.date}</td>
                    <td>
                      <div className="stack" style={{ gap: 4 }}>
                        <span className="cat-badge"><span className="sw" style={{ background:c?.color, color:c?.fg }}><Icon name={c?.icon} size={13}/></span>{c?.name}</span>
                        {c?.tags && c.tags.length>0 && <TagChips tags={c.tags}/>}
                      </div>
                    </td>
                    <td className="muted">{t.account}</td>
                    <td className="muted" style={{ fontSize: 13 }}>{t.note || '—'}</td>
                    <td className={`right num ${pos?'up':'down'}`} style={{ fontWeight: 600 }}>
                      <div>{pos?'+':'−'}{sym}{Math.abs(t.amount).toFixed(2)}</div>
                      {isForeign && <div className="num muted" style={{ fontSize: 10, fontWeight: 400 }}>≈ ${baseAmt.toFixed(2)} {BASE_CCY}</div>}
                    </td>
                    <td className="right"><EditDeleteActions/></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
window.Transactions = Transactions;
