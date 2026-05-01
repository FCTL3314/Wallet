// Add transaction modal — supports catalog autocomplete on the Note field.
const TransactionModal = ({ onClose }) => {
  const { categoriesInc, categoriesExp, accounts, catalog } = window.DATA;
  const [type, setType] = React.useState('expense');
  const cats = type==='income' ? categoriesInc : categoriesExp;
  const [cat, setCat] = React.useState(cats[0].id);
  const [amount, setAmount] = React.useState('');
  const [note, setNote] = React.useState('');
  const [showSugg, setShowSugg] = React.useState(false);

  React.useEffect(()=>{ setCat((type==='income'?categoriesInc:categoriesExp)[0].id); }, [type]);

  const pool = (type==='income' ? catalog.income : catalog.expense);
  const matches = note.length >= 1
    ? pool.filter(p => p.name.toLowerCase().includes(note.toLowerCase())).slice(0,5)
    : pool.slice(0,5);

  const pickSugg = (p) => { setNote(p.name); setCat(p.category); if (!amount) setAmount(p.typical.toFixed(2)); setShowSugg(false); };

  return (
    <div className="scrim" onClick={onClose}>
      <div className="modal" onClick={e=>e.stopPropagation()}>
        <div className="row-between" style={{ marginBottom: 20 }}>
          <div>
            <div className="label">New entry</div>
            <div style={{ fontFamily:'var(--font-display)', fontSize: 22, fontWeight: 600, marginTop: 4 }}>Add transaction</div>
          </div>
          <button className="icon-btn" onClick={onClose}><Icon name="close" size={16}/></button>
        </div>

        <div className="segmented" style={{ marginBottom: 16 }}>
          <button className={type==='expense'?'on':''} onClick={()=>setType('expense')}>Expense</button>
          <button className={type==='income'?'on':''} onClick={()=>setType('income')}>Income</button>
        </div>

        <div className="field" style={{ marginBottom: 16 }}>
          <span className="label">Amount</span>
          <div style={{ position:'relative' }}>
            <span style={{ position:'absolute', left:14, top:'50%', transform:'translateY(-50%)', color:'var(--ink-3)', fontSize:22 }}>$</span>
            <input className="input" style={{ paddingLeft:32, fontSize:26, fontFamily:'var(--font-display)', fontWeight:600 }} placeholder="0.00" value={amount} onChange={e=>setAmount(e.target.value)} inputMode="decimal"/>
          </div>
        </div>

        <div className="grid" style={{ gridTemplateColumns:'1fr 1fr', gap: 12, marginBottom: 16 }}>
          <div className="field"><span className="label">Account</span><select className="select">{accounts.map(a => <option key={a.id}>{a.location} · {a.ccy}</option>)}</select></div>
          <div className="field"><span className="label">Date</span><input type="date" className="input" defaultValue="2026-04-21"/></div>
        </div>

        <div className="field" style={{ marginBottom: 16 }}>
          <span className="label">Category</span>
          <div style={{ display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap: 8 }}>
            {cats.map(c => (
              <button key={c.id} onClick={()=>setCat(c.id)}
                style={{
                  padding:'10px 12px', borderRadius:12, textAlign:'left',
                  border:`1.5px solid ${cat===c.id?'var(--accent)':'var(--hairline)'}`,
                  background: cat===c.id?'var(--accent-soft)':'var(--surface)',
                  color: cat===c.id?'var(--accent-ink)':'var(--ink)',
                  display:'flex', gap:8, alignItems:'center', cursor:'pointer',
                  transition:'all var(--t-fast) var(--ease)', fontWeight:500, fontSize:13,
                }}>
                <Icon name={c.icon} size={14}/>{c.name}
              </button>
            ))}
          </div>
        </div>

        <div className="field" style={{ marginBottom: 20, position:'relative' }}>
          <span className="label">Note · catalog autocomplete</span>
          <input className="input" placeholder="Lidl, Spotify, Upwork…" value={note}
            onChange={e=>{ setNote(e.target.value); setShowSugg(true); }}
            onFocus={()=>setShowSugg(true)}
            onBlur={()=>setTimeout(()=>setShowSugg(false), 120)}/>
          {showSugg && matches.length>0 && (
            <div className="autocomplete">
              <div className="label" style={{ padding:'10px 14px 4px' }}>Suggestions from your catalog</div>
              {matches.map((m, i) => {
                const cm = (type==='income'?categoriesInc:categoriesExp).find(x=>x.id===m.category);
                return (
                  <button key={i} className="autocomplete-item" onMouseDown={e=>{ e.preventDefault(); pickSugg(m); }}>
                    <span className="cat-badge"><span className="sw" style={{ background:cm?.color, color:cm?.fg }}><Icon name={cm?.icon} size={12}/></span>{m.name}</span>
                    <span className="num muted">~${m.typical.toFixed(2)}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="row" style={{ gap: 10, justifyContent:'flex-end' }}>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn--primary" onClick={onClose}><Icon name="check" size={14}/> Save</button>
        </div>
      </div>
    </div>
  );
};
window.TransactionModal = TransactionModal;
