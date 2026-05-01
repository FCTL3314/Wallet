// Filter bar + toolbar
const FilterBar = ({ period, setPeriod, ccy, setCcy, actions }) => {
  const periods = ['All','YTD','3M','6M','12M'];
  const ccys = ['USD','EUR','GBP','BYN'];
  return (
    <div className="card" style={{ display:'flex', gap: 12, alignItems:'center', flexWrap:'wrap', padding: '14px 16px' }}>
      <div className="segmented">
        {periods.map(p => (
          <button key={p} className={period===p?'on':''} onClick={()=>setPeriod(p)}>{p}</button>
        ))}
      </div>
      <div style={{ display:'inline-flex', alignItems:'center', gap:6, color:'var(--ink-3)', fontSize: 12 }}>
        <Icon name="calendar" size={14}/>
        <span>Jan 01 — Apr 21, 2026</span>
      </div>
      <span className="label" style={{ marginLeft: 10 }}>Currency</span>
      <div className="segmented">
        <button className={ccy==='All'?'on':''} onClick={()=>setCcy('All')}>All</button>
        {ccys.map(c => (
          <button key={c} className={ccy===c?'on':''} onClick={()=>setCcy(c)}>{c}</button>
        ))}
      </div>
      <div style={{ flex: 1 }}/>
      {actions}
    </div>
  );
};
window.FilterBar = FilterBar;
