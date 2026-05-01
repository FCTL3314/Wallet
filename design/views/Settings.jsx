// Settings — Profile, Email, Password, Appearance, Data (export / replay onboarding / danger).
const Settings = () => {
  const [tab, setTab] = React.useState('profile');
  const [pwd, setPwd] = React.useState('');
  const { currencies } = window.DATA;
  const tabs = [
    { id:'profile',     label:'Profile' },
    { id:'email',       label:'Change email' },
    { id:'password',    label:'Password' },
    { id:'appearance',  label:'Appearance' },
    { id:'data',        label:'Data' },
  ];
  return (
    <div className="sections">
      <div className="card" style={{ padding:'14px 16px', overflowX:'auto' }}>
        <div className="segmented" style={{ flexWrap:'nowrap' }}>
          {tabs.map(t => <button key={t.id} className={tab===t.id?'on':''} onClick={()=>setTab(t.id)}>{t.label}</button>)}
        </div>
      </div>

      {tab==='profile' && (
        <div className="card">
          <div className="row" style={{ gap: 14, marginBottom: 22 }}>
            <div className="avatar" style={{ width: 56, height: 56, fontSize: 18 }}>NS</div>
            <div className="stack" style={{ gap: 2 }}>
              <span style={{ fontFamily:'var(--font-display)', fontWeight: 600, fontSize: 17 }}>Nikita Solovev</span>
              <span className="muted" style={{ fontSize: 13 }}>solovev.nikita.05@gmail.com</span>
            </div>
          </div>
          <div className="grid" style={{ gridTemplateColumns:'1fr 1fr', gap: 14, maxWidth: 640 }}>
            <div className="field"><span className="label">Name</span><input className="input" defaultValue="Nikita Solovev"/></div>
            <div className="field"><span className="label">Base currency</span><select className="select">{currencies.map(c=><option key={c.code}>{c.code} — {c.name}</option>)}</select></div>
            <div className="field"><span className="label">Week starts on</span><select className="select"><option>Monday</option><option>Sunday</option></select></div>
            <div className="field"><span className="label">Default convert-to</span><select className="select">{currencies.map(c=><option key={c.code}>{c.code}</option>)}</select></div>
          </div>
          <div className="row" style={{ marginTop: 22, gap: 10 }}>
            <button className="btn btn--primary"><Icon name="check" size={14}/> Save changes</button>
            <button className="btn">Cancel</button>
          </div>
        </div>
      )}

      {tab==='email' && (
        <div className="card" style={{ maxWidth: 520 }}>
          <div className="label">Account</div>
          <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, margin:'4px 0 4px' }}>Change email</div>
          <div className="muted" style={{ fontSize: 13, marginBottom: 18 }}>We'll send a confirmation link to the new address. Your current email keeps working until you confirm.</div>
          <div className="stack" style={{ gap: 12 }}>
            <div className="field"><span className="label">Current email</span><input className="input" defaultValue="solovev.nikita.05@gmail.com" disabled/></div>
            <div className="field"><span className="label">New email</span><input className="input" type="email" placeholder="you@example.com"/></div>
            <div className="field"><span className="label">Current password</span><input className="input" type="password"/></div>
          </div>
          <div className="row" style={{ marginTop: 18, gap: 10 }}>
            <button className="btn btn--primary"><Icon name="check" size={14}/> Send confirmation</button>
          </div>
        </div>
      )}

      {tab==='password' && (
        <div className="card" style={{ maxWidth: 520 }}>
          <div className="label">Account security</div>
          <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, margin:'4px 0 18px' }}>Change password</div>
          <div className="stack" style={{ gap: 12 }}>
            <div className="field"><span className="label">Current password</span><input type="password" className="input"/></div>
            <div className="field"><span className="label">New password</span><input type="password" className="input" value={pwd} onChange={e=>setPwd(e.target.value)}/><PasswordRequirements value={pwd}/></div>
            <div className="field"><span className="label">Confirm new password</span><input type="password" className="input"/></div>
          </div>
          <div className="row" style={{ marginTop: 18, gap: 10 }}>
            <button className="btn btn--primary">Update password</button>
          </div>
        </div>
      )}

      {tab==='appearance' && (
        <div className="card" style={{ maxWidth: 720 }}>
          <div className="label">Look & feel</div>
          <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, margin:'4px 0 18px' }}>Appearance</div>
          <div className="stack" style={{ gap: 18 }}>
            <div className="row-between" style={{ padding: '14px 16px', background:'var(--surface-2)', borderRadius: 14 }}>
              <div className="stack" style={{ gap: 2 }}>
                <span style={{ fontWeight: 500 }}>Theme</span>
                <span className="muted" style={{ fontSize: 12 }}>Light, dark or follow your system.</span>
              </div>
              <div className="segmented">
                <button className="on">Light</button><button>Dark</button><button>Auto</button>
              </div>
            </div>
            <div className="row-between" style={{ padding: '14px 16px', background:'var(--surface-2)', borderRadius: 14 }}>
              <div className="stack" style={{ gap: 2 }}>
                <span style={{ fontWeight: 500 }}>Density</span>
                <span className="muted" style={{ fontSize: 12 }}>How tightly cards and rows pack together.</span>
              </div>
              <div className="segmented"><button>Compact</button><button className="on">Cozy</button><button>Comfortable</button></div>
            </div>
            <div className="row-between" style={{ padding: '14px 16px', background:'var(--surface-2)', borderRadius: 14 }}>
              <div className="stack" style={{ gap: 2 }}>
                <span style={{ fontWeight: 500 }}>Number format</span>
                <span className="muted" style={{ fontSize: 12 }}>1,234.56 vs 1.234,56 vs 1 234,56</span>
              </div>
              <div className="segmented"><button className="on">1,234.56</button><button>1.234,56</button><button>1 234,56</button></div>
            </div>
            <div className="row-between" style={{ padding: '14px 16px', background:'var(--surface-2)', borderRadius: 14 }}>
              <div className="stack" style={{ gap: 2 }}>
                <span style={{ fontWeight: 500 }}>Hide amounts</span>
                <span className="muted" style={{ fontSize: 12 }}>Mask all numbers as ••••• until you tap to reveal.</span>
              </div>
              <label className="switch"><input type="checkbox"/><span/></label>
            </div>
          </div>
        </div>
      )}

      {tab==='data' && (
        <div className="stack" style={{ gap: 16 }}>
          <div className="card">
            <div className="label">Export</div>
            <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, margin:'4px 0 14px' }}>Download your data</div>
            <div className="grid" style={{ gridTemplateColumns:'repeat(3, 1fr)', gap: 12 }}>
              <button className="export-card">
                <Icon name="book" size={20}/>
                <div className="stack" style={{ gap: 2 }}>
                  <span style={{ fontWeight: 600 }}>Full archive · JSON</span>
                  <span className="muted" style={{ fontSize: 12 }}>All transactions, snapshots, references.</span>
                </div>
              </button>
              <button className="export-card">
                <Icon name="book" size={20}/>
                <div className="stack" style={{ gap: 2 }}>
                  <span style={{ fontWeight: 600 }}>Transactions · CSV</span>
                  <span className="muted" style={{ fontSize: 12 }}>For Excel / Google Sheets.</span>
                </div>
              </button>
              <button className="export-card">
                <Icon name="book" size={20}/>
                <div className="stack" style={{ gap: 2 }}>
                  <span style={{ fontWeight: 600 }}>Snapshots · CSV</span>
                  <span className="muted" style={{ fontSize: 12 }}>One row per (date · location · ccy).</span>
                </div>
              </button>
            </div>
          </div>

          <div className="card">
            <div className="row-between">
              <div>
                <div className="label">Help</div>
                <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, marginTop: 4 }}>Replay onboarding</div>
                <div className="muted" style={{ fontSize: 13, marginTop: 4, maxWidth: 480 }}>Walk through the intro tour again — base currency, your first storage location and a starter snapshot.</div>
              </div>
              <button className="btn"><Icon name="sparkle" size={14}/> Replay tour</button>
            </div>
          </div>

          <div className="card" style={{ borderColor:'rgba(220,80,80,.25)' }}>
            <div className="label" style={{ color: 'var(--expense-ink)' }}>Danger zone</div>
            <div style={{ fontFamily:'var(--font-display)', fontSize: 18, fontWeight: 600, margin: '4px 0 6px' }}>Reset everything</div>
            <div className="muted" style={{ fontSize: 13, marginBottom: 14, maxWidth: 520 }}>Wipes all transactions, snapshots, locations and references. Can't be undone — export your data first.</div>
            <BaseConfirmButton label="Reset all data" armedLabel="Confirm — reset everything"/>
          </div>
        </div>
      )}
    </div>
  );
};
window.Settings = Settings;
