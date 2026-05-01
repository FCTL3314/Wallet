// Base building blocks: BaseStatCard, BaseConfirmButton, EditDeleteActions, EmptyState, PasswordRequirements

const BaseStatCard = ({ label, value, ccy='USD', growth, variant='neutral', foot, children }) => {
  const color = variant==='income' ? 'var(--income-ink)'
    : variant==='expense' ? 'var(--expense-ink)'
    : variant==='profit' ? 'var(--accent-ink)' : 'var(--ink)';
  return (
    <div className="card stat-card">
      <div className="stat-label label">{label}</div>
      <div className="stat-value" style={{ color }}>
        {ccy && <span style={{ color:'var(--ink-3)', fontSize:'0.55em', marginRight:6, fontWeight:500 }}>{ccy}</span>}
        {typeof value==='number' ? value.toLocaleString('en-US',{minimumFractionDigits:2, maximumFractionDigits:2}) : value}
      </div>
      {(growth!=null || foot) && (
        <div className="stat-foot">
          {growth!=null && (
            <span className={`growth ${growth>0?'growth--up':growth<0?'growth--down':'growth--flat'}`}>
              <Icon name={growth>0?'arrowUp':growth<0?'arrowDown':'trend'} size={11}/>
              {growth>0?'+':''}{growth}%
            </span>
          )}
          {foot}
        </div>
      )}
      {children}
    </div>
  );
};

const BaseConfirmButton = ({ onConfirm, label='Delete', armedLabel='Sure?' }) => {
  const [armed, setArmed] = React.useState(false);
  const timer = React.useRef(null);
  React.useEffect(() => () => clearTimeout(timer.current), []);
  const click = () => {
    if (!armed) { setArmed(true); timer.current = setTimeout(()=>setArmed(false), 2500); }
    else { clearTimeout(timer.current); setArmed(false); onConfirm?.(); }
  };
  return (
    <button className={`confirm-btn ${armed?'armed':''}`} onClick={click}>
      {armed ? <><Icon name="check" size={12}/>{armedLabel}</> : <><Icon name="trash" size={12}/>{label}</>}
    </button>
  );
};

const EditDeleteActions = ({ onEdit, onDelete }) => (
  <div className="ed-actions">
    <button className="icon-btn" onClick={onEdit} title="Edit"><Icon name="edit" size={14}/></button>
    <BaseConfirmButton onConfirm={onDelete} label="" armedLabel="Sure?"/>
  </div>
);

const EmptyState = ({ icon='tag', title, subtitle, action }) => (
  <div className="empty">
    <div className="empty-illust"><Icon name={icon} size={36} stroke={1.4}/></div>
    <div className="empty-title">{title}</div>
    <div className="empty-sub">{subtitle}</div>
    {action}
  </div>
);

const PasswordRequirements = ({ value }) => {
  const reqs = [
    { label:'At least 8 characters',  ok: value.length>=8 },
    { label:'One uppercase letter',   ok: /[A-Z]/.test(value) },
    { label:'One number',             ok: /\d/.test(value) },
    { label:'One special character',  ok: /[^A-Za-z0-9]/.test(value) },
  ];
  return (
    <ul className="pwd-req">
      {reqs.map((r,i) => (
        <li key={i} className={r.ok?'ok':''}>
          <span className="tick"><Icon name={r.ok?'check':'close'} size={10} stroke={2.5}/></span>
          {r.label}
        </li>
      ))}
    </ul>
  );
};

// RateBadge — surfaces "rates as of X" with a stale-warning chip when older than 2 days.
const RateBadge = ({ asOf, today, onRefresh }) => {
  const a = new Date(asOf), t = new Date(today);
  const days = Math.round((t - a) / 86400000);
  const stale = days >= 2;
  return (
    <span className={`rate-badge ${stale?'rate-badge--stale':''}`} title="Currency rates freshness">
      <Icon name={stale?'info':'check'} size={13}/>
      <span>Rates · {asOf}{stale ? ` · ${days}d old` : ''}</span>
      {onRefresh && <button className="rate-refresh" onClick={onRefresh} title="Refresh"><Icon name="recurring" size={10}/></button>}
    </span>
  );
};

// TagChips — small inline tag list with optional "+ Add"
const TagChips = ({ tags = [], onAdd, onRemove }) => (
  <span className="tag-chips">
    {tags.map(t => (
      <span key={t} className="tag-chip">
        {t}
        {onRemove && <button onClick={()=>onRemove(t)} aria-label="remove"><Icon name="close" size={9}/></button>}
      </span>
    ))}
    {onAdd && <button className="tag-chip tag-chip--add" onClick={onAdd}><Icon name="plus" size={9}/> Tag</button>}
  </span>
);

window.RateBadge = RateBadge;
window.TagChips = TagChips;
window.BaseStatCard = BaseStatCard;
window.BaseConfirmButton = BaseConfirmButton;
window.EditDeleteActions = EditDeleteActions;
window.EmptyState = EmptyState;
window.PasswordRequirements = PasswordRequirements;
