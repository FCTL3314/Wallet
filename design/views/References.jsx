// References — Currencies (with base + manual rate override + freshness),
// Storage Locations, Storage Accounts, Income sources, Expense categories.
const References = () => {
  const [tab, setTab] = React.useState('currencies');
  const [editRate, setEditRate] = React.useState(null); // currency code
  const D = window.DATA;
  const { currencies, categoriesInc, categoriesExp, storageLocations, accounts, RATES_AS_OF, TODAY } = D;

  const tabs = [
    { id:'currencies', label:'Currencies' },
    { id:'locations',  label:'Storage Locations' },
    { id:'accounts',   label:'Storage Accounts' },
    { id:'income',     label:'Income sources' },
    { id:'expense',    label:'Expense categories' },
  ];

  return (
    <div className="sections">
      <div className="card" style={{ padding:'14px 16px', display:'flex', gap: 12, alignItems:'center', flexWrap:'wrap' }}>
        <div className="segmented">
          {tabs.map(t => <button key={t.id} className={tab===t.id?'on':''} onClick={()=>setTab(t.id)}>{t.label}</button>)}
        </div>
        <div style={{ flex: 1 }}/>
        {tab==='currencies' && <RateBadge asOf={RATES_AS_OF} today={TODAY} onRefresh={()=>{}}/>}
        <button className="btn btn--primary"><Icon name="plus" size={15}/> New</button>
      </div>

      {tab==='currencies' && (
        <div className="card" style={{ padding:0, overflow:'hidden' }}>
          <div className="row-between" style={{ padding:'18px 22px' }}>
            <div>
              <div className="label">Reference</div>
              <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>Currencies</div>
              <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>One currency is the <b style={{ color:'var(--ink)' }}>base</b> — every amount in the app is converted to it for totals.</div>
            </div>
            <div className="base-pill">
              <span className="label">Base currency</span>
              <span className="num" style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600 }}>{currencies.find(c=>c.isBase)?.code}</span>
              <span className="muted" style={{ fontSize: 12 }}>{currencies.find(c=>c.isBase)?.symbol} · {currencies.find(c=>c.isBase)?.name}</span>
            </div>
          </div>
          <table className="table">
            <thead><tr>
              <th>Code</th>
              <th>Name</th>
              <th>Symbol</th>
              <th className="right">Exchange rate</th>
              <th>Source</th>
              <th className="right">Actions</th>
            </tr></thead>
            <tbody>
              {currencies.map(c => {
                const base = currencies.find(x=>x.isBase);
                return (
                  <tr key={c.code}>
                    <td style={{ fontWeight: 600, fontFamily:'var(--font-mono)' }}>{c.code}</td>
                    <td>{c.name}{c.isBase && <span className="chip chip--accent" style={{ marginLeft: 8 }}>Base</span>}</td>
                    <td className="mono">{c.symbol}</td>
                    <td className="right">
                      {c.isBase ? <span className="muted">— base —</span> : (
                        <span className="rate-line">
                          <span className="num">1 {c.code}</span>
                          <span className="rate-eq">=</span>
                          <span className="num" style={{ fontWeight: 600 }}>{c.rate.toFixed(4)}</span>
                          <span className="num" style={{ color:'var(--ink-3)' }}>{base?.code}</span>
                        </span>
                      )}
                    </td>
                    <td>
                      {c.isBase ? <span className="muted">—</span>
                        : c.manual ? <span className="chip chip--warn">Manual</span>
                        : <span className="chip">Auto · {RATES_AS_OF}</span>}
                    </td>
                    <td className="right">
                      <div className="ed-actions">
                        {!c.isBase && <button className="btn btn--ghost" style={{ padding:'4px 10px', fontSize: 11 }}>Set as base</button>}
                        {!c.isBase && <button className="icon-btn" onClick={()=>setEditRate(c.code)} title="Override rate"><Icon name="edit" size={13}/></button>}
                        {!c.isBase && <BaseConfirmButton label="" armedLabel="Sure?"/>}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {tab==='locations' && (
        <div className="card" style={{ padding:0, overflow:'hidden' }}>
          <div className="row-between" style={{ padding:'18px 22px' }}>
            <div>
              <div className="label">Reference</div>
              <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>Storage Locations</div>
              <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>Where your money lives — banks, wallets, cash, etc.</div>
            </div>
          </div>
          <table className="table">
            <thead><tr><th>Name</th><th>Currencies</th><th className="right">Accounts</th><th className="right">Total ≈ USD</th><th className="right">Actions</th></tr></thead>
            <tbody>
              {storageLocations.map(l => {
                const totalUSD = l.accounts.reduce((s,a)=>s + D.toBase(a.balance, a.ccy), 0);
                return (
                  <tr key={l.id}>
                    <td style={{ fontWeight: 500 }}>{l.name}</td>
                    <td>{l.accounts.map(a=><span key={a.id} className="chip" style={{ marginRight: 4 }}>{a.ccy}</span>)}</td>
                    <td className="right num">{l.accounts.length}</td>
                    <td className="right num" style={{ fontWeight: 600 }}>${totalUSD.toLocaleString('en-US',{maximumFractionDigits:0})}</td>
                    <td className="right"><EditDeleteActions/></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {tab==='accounts' && (
        <div className="card" style={{ padding:0, overflow:'hidden' }}>
          <div className="row-between" style={{ padding:'18px 22px' }}>
            <div>
              <div className="label">Reference</div>
              <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>Storage Accounts</div>
              <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>One account per (location × currency).</div>
            </div>
          </div>
          <table className="table">
            <thead><tr><th>Location</th><th>Currency</th><th className="right">Balance</th><th className="right">≈ USD</th><th className="right">Actions</th></tr></thead>
            <tbody>
              {accounts.map(a => (
                <tr key={a.id}>
                  <td style={{ fontWeight: 500 }}>{a.location}</td>
                  <td><span className="chip">{a.ccy}</span></td>
                  <td className="right num">{a.balance.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}</td>
                  <td className="right num muted">${D.toBase(a.balance, a.ccy).toLocaleString('en-US',{maximumFractionDigits:0})}</td>
                  <td className="right"><EditDeleteActions/></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab==='income' && (
        <div className="card" style={{ padding:0, overflow:'hidden' }}>
          <div style={{ padding:'18px 22px' }}>
            <div className="label">Reference</div>
            <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>Income sources</div>
          </div>
          <table className="table">
            <thead><tr><th>Name</th><th className="right">Actions</th></tr></thead>
            <tbody>
              {categoriesInc.map(c => (
                <tr key={c.id}>
                  <td><span className="cat-badge"><span className="sw" style={{ background:c.color, color:c.fg }}><Icon name={c.icon} size={13}/></span>{c.name}</span></td>
                  <td className="right"><EditDeleteActions/></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab==='expense' && (
        <div className="card" style={{ padding:0, overflow:'hidden' }}>
          <div style={{ padding:'18px 22px' }}>
            <div className="label">Reference</div>
            <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>Expense categories</div>
          </div>
          <table className="table">
            <thead><tr><th>Name · tags</th><th>Frequency</th><th className="right">Budget</th><th className="right">Actions</th></tr></thead>
            <tbody>
              {categoriesExp.map(c => (
                <tr key={c.id}>
                  <td>
                    <div className="stack" style={{ gap: 4 }}>
                      <span className="cat-badge"><span className="sw" style={{ background:c.color, color:c.fg }}><Icon name={c.icon} size={13}/></span>{c.name}</span>
                      <TagChips tags={c.tags || []}/>
                    </div>
                  </td>
                  <td><span className={`chip ${c.frequency==='annual'?'chip--accent':''}`}>{c.frequency}</span></td>
                  <td className="right num">${c.budgeted.toFixed(2)}</td>
                  <td className="right"><EditDeleteActions/></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Manual rate override modal */}
      {editRate && (
        <div className="scrim" onClick={()=>setEditRate(null)}>
          <div className="modal" onClick={e=>e.stopPropagation()} style={{ maxWidth: 460 }}>
            <div className="row-between" style={{ marginBottom: 16 }}>
              <div>
                <div className="label">Override rate</div>
                <div style={{ fontFamily:'var(--font-display)', fontSize: 22, fontWeight: 600, marginTop: 4 }}>Manual rate · {editRate}</div>
              </div>
              <button className="icon-btn" onClick={()=>setEditRate(null)}><Icon name="close" size={16}/></button>
            </div>
            <div className="muted" style={{ fontSize: 13, marginBottom: 14 }}>
              Replaces the auto-fetched rate until you clear it. Useful when you want to lock a historical rate or your bank used a different one.
            </div>
            <div className="grid" style={{ gridTemplateColumns:'1fr 1fr', gap: 12, marginBottom: 16 }}>
              <div className="field"><span className="label">1 {editRate} =</span>
                <div style={{ position:'relative' }}>
                  <input className="input" defaultValue={currencies.find(c=>c.code===editRate)?.rate.toFixed(4)} style={{ paddingRight: 56 }}/>
                  <span style={{ position:'absolute', right:14, top:'50%', transform:'translateY(-50%)', color:'var(--ink-3)', fontSize: 12, fontFamily:'var(--font-mono)' }}>USD</span>
                </div>
              </div>
              <div className="field"><span className="label">Effective from</span><input type="date" className="input" defaultValue={TODAY}/></div>
            </div>
            <div className="row" style={{ gap: 10, justifyContent:'flex-end' }}>
              <button className="btn" onClick={()=>setEditRate(null)}>Cancel</button>
              <button className="btn btn--ghost" onClick={()=>setEditRate(null)}>Reset to auto</button>
              <button className="btn btn--primary" onClick={()=>setEditRate(null)}><Icon name="check" size={14}/> Save override</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
window.References = References;
