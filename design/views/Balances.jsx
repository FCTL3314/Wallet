// Balances — locations, by-storage pivot, snapshot sets (one expandable card per date).
const Balances = ({ period, setPeriod, ccy, setCcy }) => {
  const D = window.DATA;
  const { storageLocations, accounts, snapshots, RATES_AS_OF, TODAY } = D;
  const [year, setYear] = React.useState('2026');
  const [openDates, setOpenDates] = React.useState({ '2026-04-21': true });
  const totalUSD = accounts.reduce((s,a)=>s + D.toBase(a.balance, a.ccy), 0);

  // Group snapshots by date.
  const snapByDate = snapshots.reduce((acc, s) => {
    (acc[s.date] = acc[s.date] || []).push(s);
    return acc;
  }, {});
  const dates = Object.keys(snapByDate).sort().reverse();

  // Pivot: locations × dates → ≈ USD.
  const pivotLocs = [...new Set(snapshots.map(s=>s.location))];

  return (
    <div className="sections">
      <FilterBar period={period} setPeriod={setPeriod} ccy={ccy} setCcy={setCcy}
        actions={<>
          <RateBadge asOf={RATES_AS_OF} today={TODAY}/>
          <button className="btn btn--primary"><Icon name="plus" size={15}/> New snapshot</button>
        </>}/>

      <div className="kpis">
        <BaseStatCard label="Total balance" value={totalUSD} variant="profit" growth={5.7}/>
        <BaseStatCard label="Locations"     value={storageLocations.length.toString()} ccy="" foot={<span className="muted">{accounts.length} accounts</span>}/>
        <BaseStatCard label="Snapshot sets" value={dates.length.toString()} ccy="" foot={<span className="muted">{snapshots.length} rows total</span>}/>
      </div>

      {/* Locations grid */}
      <div className="grid" style={{ gridTemplateColumns:'repeat(3, 1fr)' }}>
        {storageLocations.map(loc => {
          const locTotal = loc.accounts.reduce((s,a)=>s + D.toBase(a.balance, a.ccy),0);
          return (
            <div key={loc.id} className="card">
              <div className="row-between" style={{ marginBottom: 14 }}>
                <div className="row">
                  <span style={{ width:36, height:36, borderRadius:11, background:'var(--accent-soft)', color:'var(--accent-ink)', display:'grid', placeItems:'center' }}><Icon name="wallet" size={16}/></span>
                  <span style={{ fontWeight: 600, fontFamily:'var(--font-display)' }}>{loc.name}</span>
                </div>
                <EditDeleteActions/>
              </div>
              <div className="stack" style={{ gap: 6 }}>
                {loc.accounts.map(a => (
                  <div key={a.id} className="row-between" style={{ fontSize: 13 }}>
                    <span className="muted">{a.ccy}</span>
                    <span className="num" style={{ fontWeight: 500 }}>{a.ccy==='USD'?'$':a.ccy==='EUR'?'€':''}{a.balance.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}</span>
                  </div>
                ))}
              </div>
              <hr className="divider" style={{ margin: '14px 0 10px' }}/>
              <div className="row-between"><span className="label">≈ USD</span><span className="num" style={{ fontWeight: 600 }}>${locTotal.toLocaleString('en-US',{maximumFractionDigits:0})}</span></div>
            </div>
          );
        })}
        <button className="card" style={{ border:'1.5px dashed var(--hairline-strong)', background:'transparent', boxShadow:'none', display:'flex', alignItems:'center', justifyContent:'center', gap:10, minHeight: 180, color:'var(--ink-3)', cursor:'pointer' }}>
          <Icon name="plus" size={18}/><span>New location</span>
        </button>
      </div>

      {/* By-storage pivot — easy month-over-month comparison */}
      <div className="card" style={{ padding: 0, overflow:'hidden' }}>
        <div className="row-between" style={{ padding:'18px 22px' }}>
          <div>
            <div className="label">Pivot</div>
            <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>By storage · ≈ USD across snapshot dates</div>
          </div>
          <div className="segmented">{['2024','2025','2026'].map(y=>(<button key={y} className={year===y?'on':''} onClick={()=>setYear(y)}>{y}</button>))}</div>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Location</th>
              {dates.map(d => <th key={d} className="right num">{d.slice(5)}</th>)}
              <th className="right">Δ first→last</th>
            </tr>
          </thead>
          <tbody>
            {pivotLocs.map(loc => {
              const cells = dates.map(d => {
                const rows = snapByDate[d].filter(r=>r.location===loc);
                return rows.reduce((s,r)=> s + D.toBase(r.balance, r.ccy), 0);
              });
              const first = cells[cells.length-1] || 0;
              const last  = cells[0] || 0;
              const delta = last - first;
              return (
                <tr key={loc}>
                  <td style={{ fontWeight: 500 }}>{loc}</td>
                  {cells.map((v, i) => <td key={i} className="right num">${v.toLocaleString('en-US',{maximumFractionDigits:0})}</td>)}
                  <td className="right num" style={{ fontWeight: 600, color: delta>=0 ? 'var(--accent-ink)' : 'var(--expense-ink)' }}>
                    {delta>=0?'+':'−'}${Math.abs(delta).toLocaleString('en-US',{maximumFractionDigits:0})}
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr>
              <td style={{ fontWeight: 600 }}>Total</td>
              {dates.map(d => {
                const sum = snapByDate[d].reduce((s,r)=> s + D.toBase(r.balance, r.ccy), 0);
                return <td key={d} className="right num" style={{ fontWeight: 600 }}>${sum.toLocaleString('en-US',{maximumFractionDigits:0})}</td>;
              })}
              <td/>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Snapshot sets — timeline of moments in time */}
      <div className="card" style={{ padding: 0, overflow:'hidden' }}>
        <div className="row-between" style={{ padding:'18px 22px 16px' }}>
          <div>
            <div className="label">History</div>
            <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>Snapshot timeline</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>Each entry is one moment in time across every account. Click to expand.</div>
          </div>
        </div>
        <div className="snap-timeline">
          {dates.map((d, i) => {
            const rows = snapByDate[d];
            const total = rows.reduce((s,r)=> s + D.toBase(r.balance, r.ccy), 0);
            const prevDate = dates[i+1];
            const prevTotal = prevDate ? snapByDate[prevDate].reduce((s,r)=> s + D.toBase(r.balance, r.ccy), 0) : null;
            const delta = prevTotal!=null ? total - prevTotal : null;
            const deltaPct = prevTotal ? (delta/prevTotal)*100 : null;
            const open = !!openDates[d];

            const dt = new Date(d);
            const day   = dt.getDate();
            const month = dt.toLocaleString('en-US', { month: 'short' });
            const year  = dt.getFullYear();

            return (
              <div key={d} className={`snap-set ${open?'snap-set--open':''}`}>
                <button className="snap-head" onClick={()=>setOpenDates(s=>({...s, [d]: !s[d]}))}>
                  <span className="snap-rail">
                    <span className="snap-dot"/>
                    {i < dates.length - 1 && <span className="snap-line"/>}
                  </span>
                  <div className="snap-date">
                    <span className="snap-day">{day}</span>
                    <span className="snap-month">{month}</span>
                    <span className="snap-year">{year}</span>
                  </div>
                  <div className="snap-meta">
                    <span className="snap-locs">
                      {[...new Set(rows.map(r=>r.location))].map(l => (
                        <span key={l} className="snap-loc-chip">{l}</span>
                      ))}
                    </span>
                    <span className="muted" style={{ fontSize: 11 }}>{rows.length} balances captured</span>
                  </div>
                  <div className="snap-total">
                    <span className="num snap-total-num">${total.toLocaleString('en-US',{maximumFractionDigits:0})}</span>
                    {delta!=null && (
                      <span className={`growth ${delta>0?'growth--up':delta<0?'growth--down':'growth--flat'}`} style={{ fontSize: 11 }}>
                        <Icon name={delta>0?'arrowUp':'arrowDown'} size={10}/>
                        {delta>0?'+':'−'}${Math.abs(delta).toLocaleString('en-US',{maximumFractionDigits:0})}
                        {deltaPct!=null && <span style={{ opacity:.7 }}> · {deltaPct>0?'+':''}{deltaPct.toFixed(1)}%</span>}
                      </span>
                    )}
                  </div>
                  <div className="snap-actions">
                    <button className="icon-btn" title="Edit set" onClick={e=>e.stopPropagation()}><Icon name="edit" size={13}/></button>
                    <span onClick={e=>e.stopPropagation()}><BaseConfirmButton label="" armedLabel="Sure?"/></span>
                    <span className="snap-chevron"><Icon name="chevronDown" size={14}/></span>
                  </div>
                </button>
                {open && (
                  <div className="snap-body">
                    <div className="snap-grid">
                      {rows.map(r => (
                        <div key={r.id} className="snap-cell">
                          <div className="snap-cell-head">
                            <span style={{ width: 28, height: 28, borderRadius: 9, background:'var(--surface)', border:'1px solid var(--hairline)', display:'grid', placeItems:'center', flexShrink: 0 }}>
                              <Icon name="wallet" size={13}/>
                            </span>
                            <div className="stack" style={{ gap: 1 }}>
                              <span style={{ fontWeight: 500, fontSize: 13 }}>{r.location}</span>
                              <span className="muted" style={{ fontSize: 10, fontFamily:'var(--font-mono)' }}>{r.ccy}</span>
                            </div>
                          </div>
                          <div className="snap-cell-amt">
                            <span className="num">{r.ccy==='USD'?'$':r.ccy==='EUR'?'€':r.ccy==='GBP'?'£':''}{r.balance.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}</span>
                            {r.ccy !== 'USD' && (
                              <span className="num muted" style={{ fontSize: 11 }}>≈ ${D.toBase(r.balance, r.ccy).toLocaleString('en-US',{maximumFractionDigits:0})} USD</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
window.Balances = Balances;
