// Header — routes cover every spec page
const Header = ({ route, setRoute, theme, setTheme }) => {
  const routes = [
    { id:'dashboard',    label:'Dashboard',        icon:'dashboard'  },
    { id:'transactions', label:'Transactions',     icon:'income'     },
    { id:'balances',     label:'Balances',         icon:'balances'   },
    { id:'recurring',    label:'Regular Expenses', icon:'recurring'  },
    { id:'references',   label:'References',       icon:'refs'       },
    { id:'settings',     label:'Settings',         icon:'settings'   },
  ];
  return (
    <header className="header">
      <div className="brand">
        <span className="brand-mark">W</span>
        <span>Wallet</span>
      </div>
      <nav className="nav">
        {routes.map(r => (
          <button key={r.id}
            className={`nav-item ${route===r.id?'active':''}`}
            onClick={()=>setRoute(r.id)}>
            <Icon name={r.icon} size={15} stroke={2}/>
            {r.label}
          </button>
        ))}
      </nav>
      <div className="header-right">
        <button className="icon-btn" aria-label="Search"><Icon name="search"/></button>
        <button className="icon-btn" aria-label="Notifications"><Icon name="bell"/></button>
        <button className="icon-btn" aria-label="Theme"
          onClick={()=>setTheme(theme==='dark'?'light':'dark')}>
          <Icon name={theme==='dark'?'sun':'moon'}/>
        </button>
        <div className="avatar">NS</div>
      </div>
    </header>
  );
};
window.Header = Header;
