// Main App shell — routing, theme, tweaks

const TWEAKS_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "light",
  "accentHue": 150,
  "density": "cozy",
  "radius": 24
}/*EDITMODE-END*/;

const App = () => {
  const [route, setRoute] = React.useState(() => localStorage.getItem('wallet.route') || 'dashboard');
  const [theme, setTheme] = React.useState(() => localStorage.getItem('wallet.theme') || TWEAKS_DEFAULTS.theme);
  const [accentHue, setAccentHue] = React.useState(() => +localStorage.getItem('wallet.hue') || TWEAKS_DEFAULTS.accentHue);
  const [density, setDensity] = React.useState(() => localStorage.getItem('wallet.density') || TWEAKS_DEFAULTS.density);
  const [radius, setRadius] = React.useState(() => +localStorage.getItem('wallet.radius') || TWEAKS_DEFAULTS.radius);
  const [period, setPeriod] = React.useState('YTD');
  const [ccy, setCcy] = React.useState('All');
  const [showTx, setShowTx] = React.useState(false);
  const [tweaksOpen, setTweaksOpen] = React.useState(false);

  React.useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('wallet.theme', theme); }, [theme]);
  React.useEffect(() => { localStorage.setItem('wallet.route', route); }, [route]);
  React.useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.style.setProperty('--accent',      `oklch(74% 0.17 ${accentHue})`);
      root.style.setProperty('--accent-ink',  `oklch(88% 0.14 ${accentHue})`);
      root.style.setProperty('--accent-soft', `oklch(26% 0.06 ${accentHue})`);
      root.style.setProperty('--accent-soft-2',`oklch(34% 0.09 ${accentHue})`);
    } else {
      root.style.setProperty('--accent',      `oklch(58% 0.14 ${accentHue})`);
      root.style.setProperty('--accent-ink',  `oklch(36% 0.11 ${accentHue})`);
      root.style.setProperty('--accent-soft', `oklch(94% 0.04 ${accentHue})`);
      root.style.setProperty('--accent-soft-2',`oklch(88% 0.08 ${accentHue})`);
    }
    localStorage.setItem('wallet.hue', accentHue);
  }, [accentHue, theme]);
  React.useEffect(() => {
    const map = { compact:{pad:16,gap:14}, cozy:{pad:22,gap:20}, comfortable:{pad:28,gap:28} };
    document.documentElement.style.setProperty('--pad-card', map[density].pad+'px');
    document.documentElement.style.setProperty('--gap-section', map[density].gap+'px');
    localStorage.setItem('wallet.density', density);
  }, [density]);
  React.useEffect(() => { document.documentElement.style.setProperty('--r-card', radius+'px'); localStorage.setItem('wallet.radius', radius); }, [radius]);

  React.useEffect(() => {
    const onMessage = (e) => {
      if (e.data?.type === '__activate_edit_mode') setTweaksOpen(true);
      if (e.data?.type === '__deactivate_edit_mode') setTweaksOpen(false);
    };
    window.addEventListener('message', onMessage);
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    return () => window.removeEventListener('message', onMessage);
  }, []);
  const persistTweak = (key, val) => window.parent.postMessage({ type: '__edit_mode_set_keys', edits: { [key]: val } }, '*');

  const routes = {
    dashboard:    <Dashboard    period={period} setPeriod={setPeriod} ccy={ccy} setCcy={setCcy} openTx={()=>setShowTx(true)} goto={setRoute}/>,
    transactions: <Transactions period={period} setPeriod={setPeriod} ccy={ccy} setCcy={setCcy} openTx={()=>setShowTx(true)}/>,
    balances:     <Balances     period={period} setPeriod={setPeriod} ccy={ccy} setCcy={setCcy}/>,
    recurring:    <Recurring    period={period} setPeriod={setPeriod} ccy={ccy} setCcy={setCcy}/>,
    references:   <References/>,
    settings:     <Settings/>,
  };
  const titles = {
    dashboard:    { eyebrow:'Overview',  title:'Good morning, Nikita' },
    transactions: { eyebrow:'Movement',  title:'Transactions' },
    balances:     { eyebrow:'Accounts',  title:'Balances' },
    recurring:    { eyebrow:'Scheduled', title:'Regular expenses' },
    references:   { eyebrow:'Library',   title:'References' },
    settings:     { eyebrow:'Account',   title:'Settings' },
  };
  const t = titles[route];

  return (
    <>
      <Header route={route} setRoute={setRoute} theme={theme} setTheme={setTheme}/>
      <div className="app" data-screen-label={route}>
        <div className="page-head">
          <div>
            <div className="page-eyebrow">{t.eyebrow}</div>
            <h1 className="page-title">{t.title}</h1>
          </div>
        </div>
        {routes[route]}
      </div>
      {showTx && <TransactionModal onClose={()=>setShowTx(false)}/>}
      {tweaksOpen && (
        <div className="tweaks-panel">
          <div className="row-between" style={{ marginBottom: 10 }}>
            <h4>Tweaks</h4>
            <button className="icon-btn" style={{ width:24, height:24 }} onClick={()=>setTweaksOpen(false)}><Icon name="close" size={14}/></button>
          </div>
          <div className="tweaks-row"><span>Theme</span>
            <div className="segmented">
              <button className={theme==='light'?'on':''} onClick={()=>{setTheme('light'); persistTweak('theme','light');}}><Icon name="sun" size={12}/></button>
              <button className={theme==='dark'?'on':''} onClick={()=>{setTheme('dark'); persistTweak('theme','dark');}}><Icon name="moon" size={12}/></button>
            </div>
          </div>
          <div className="tweaks-row"><span>Accent hue · {accentHue}°</span></div>
          <input type="range" min="0" max="360" value={accentHue} onChange={e=>{const v=+e.target.value; setAccentHue(v); persistTweak('accentHue',v);}} style={{ width:'100%', marginBottom: 10 }}/>
          <div className="tweaks-row"><span>Density</span>
            <div className="segmented">
              {['compact','cozy','comfortable'].map(d => (
                <button key={d} className={density===d?'on':''} onClick={()=>{setDensity(d); persistTweak('density',d);}}>{d[0].toUpperCase()}</button>
              ))}
            </div>
          </div>
          <div className="tweaks-row"><span>Card radius · {radius}px</span></div>
          <input type="range" min="8" max="32" value={radius} onChange={e=>{const v=+e.target.value; setRadius(v); persistTweak('radius',v);}} style={{ width:'100%' }}/>
        </div>
      )}
    </>
  );
};

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
