// Reusable charts — pure SVG, no libs

// Smooth cubic spline (Catmull-Rom → bezier)
function smoothPath(points) {
  if (points.length < 2) return '';
  const t = 0.2;
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] || points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] || p2;
    const c1x = p1.x + (p2.x - p0.x) * t;
    const c1y = p1.y + (p2.y - p0.y) * t;
    const c2x = p2.x - (p3.x - p1.x) * t;
    const c2y = p2.y - (p3.y - p1.y) * t;
    d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`;
  }
  return d;
}

const AreaChart = ({ data, width = 800, height = 260, color = 'var(--accent)', showAxis = true, showGrid = true, interactive = true, gradient = true, labels = [], formatValue = v => v }) => {
  const padL = 42, padR = 8, padT = 14, padB = 28;
  const innerW = width - padL - padR;
  const innerH = height - padT - padB;
  const [hover, setHover] = React.useState(null);
  const svgRef = React.useRef(null);

  const minV = Math.min(...data);
  const maxV = Math.max(...data);
  const range = maxV - minV || 1;
  const vMin = minV - range * 0.15;
  const vMax = maxV + range * 0.15;

  const xs = data.map((_, i) => padL + (innerW * i) / (data.length - 1));
  const ys = data.map(v => padT + innerH - ((v - vMin) / (vMax - vMin)) * innerH);
  const pts = data.map((v, i) => ({ x: xs[i], y: ys[i], v, label: labels[i] }));

  const linePath = smoothPath(pts);
  const areaPath = `${linePath} L ${xs[xs.length - 1]} ${padT + innerH} L ${xs[0]} ${padT + innerH} Z`;

  const yTicks = 4;
  const yVals = Array.from({ length: yTicks + 1 }, (_, i) => vMin + (vMax - vMin) * (i / yTicks));

  const onMove = (e) => {
    if (!interactive || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * width;
    let best = 0, bestDist = Infinity;
    for (let i = 0; i < xs.length; i++) {
      const d = Math.abs(xs[i] - px);
      if (d < bestDist) { bestDist = d; best = i; }
    }
    setHover(best);
  };

  return (
    <div className="chart-wrap" style={{ position: 'relative' }}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        style={{ display: 'block', overflow: 'visible' }}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <linearGradient id="areaFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.28"/>
            <stop offset="60%" stopColor={color} stopOpacity="0.08"/>
            <stop offset="100%" stopColor={color} stopOpacity="0"/>
          </linearGradient>
        </defs>

        {showGrid && yVals.map((v, i) => (
          <g key={i}>
            <line x1={padL} x2={width - padR} y1={padT + innerH * (1 - i / yTicks)} y2={padT + innerH * (1 - i / yTicks)}
              stroke="var(--hairline)" strokeDasharray="2 4" />
            {showAxis && (
              <text x={padL - 8} y={padT + innerH * (1 - i / yTicks) + 4} textAnchor="end"
                fontSize="10" fill="var(--ink-4)" style={{ fontFamily: 'var(--font-mono)' }}>
                {formatValue(v)}
              </text>
            )}
          </g>
        ))}

        {gradient && <path d={areaPath} fill="url(#areaFill)" />}
        <path d={linePath} fill="none" stroke={color} strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" />

        {showAxis && labels.length > 0 && labels.map((lab, i) => {
          if (labels.length > 8 && i % Math.ceil(labels.length / 8) !== 0) return null;
          return (
            <text key={i} x={xs[i]} y={height - 8} textAnchor="middle"
              fontSize="10" fill="var(--ink-4)" style={{ fontFamily: 'var(--font-sans)' }}>
              {lab}
            </text>
          );
        })}

        {hover !== null && (
          <g>
            <line x1={xs[hover]} x2={xs[hover]} y1={padT} y2={padT + innerH}
              stroke={color} strokeOpacity="0.4" strokeDasharray="3 3" />
            <circle cx={xs[hover]} cy={ys[hover]} r="9" fill={color} fillOpacity="0.15" />
            <circle cx={xs[hover]} cy={ys[hover]} r="4" fill="var(--surface)" stroke={color} strokeWidth="2" />
          </g>
        )}
      </svg>

      {hover !== null && (
        <div className="chart-tip" style={{
          position: 'absolute',
          left: `${(xs[hover] / width) * 100}%`,
          top: `${(ys[hover] / height) * 100}%`,
          transform: 'translate(-50%, calc(-100% - 14px))',
          background: 'var(--surface)',
          border: '1px solid var(--hairline)',
          borderRadius: 12,
          padding: '8px 12px',
          boxShadow: 'var(--shadow-md)',
          pointerEvents: 'none',
          whiteSpace: 'nowrap',
          fontSize: 12,
        }}>
          <div style={{ color: 'var(--ink-3)', fontSize: 11, marginBottom: 2 }}>{labels[hover]}</div>
          <div style={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{formatValue(data[hover])}</div>
        </div>
      )}
    </div>
  );
};

const Sparkline = ({ data, width = 120, height = 36, color = 'var(--accent)' }) => {
  const pad = 2;
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => ({
    x: pad + ((width - 2 * pad) * i) / (data.length - 1),
    y: pad + (height - 2 * pad) * (1 - (v - min) / range),
  }));
  const d = smoothPath(pts);
  const area = `${d} L ${pts[pts.length-1].x} ${height} L ${pts[0].x} ${height} Z`;
  const id = React.useId();
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} style={{ display: 'block' }}>
      <defs>
        <linearGradient id={`sp-${id}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3"/>
          <stop offset="100%" stopColor={color} stopOpacity="0"/>
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#sp-${id})`} />
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

const Donut = ({ segments, size = 160, thickness = 18, centerLabel, centerValue }) => {
  const r = (size - thickness) / 2;
  const cx = size / 2, cy = size / 2;
  const circ = 2 * Math.PI * r;
  const total = segments.reduce((s, x) => s + x.value, 0);
  let offset = 0;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={cx} cy={cy} r={r} stroke="var(--hairline)" strokeWidth={thickness} fill="none" />
      {segments.map((s, i) => {
        const len = (s.value / total) * circ;
        const el = (
          <circle key={i} cx={cx} cy={cy} r={r}
            stroke={s.color} strokeWidth={thickness} fill="none"
            strokeDasharray={`${len} ${circ - len}`}
            strokeDashoffset={-offset}
            strokeLinecap="butt"
          />
        );
        offset += len;
        return el;
      })}
      {centerValue && (
        <g style={{ transform: 'rotate(90deg)', transformOrigin: `${cx}px ${cy}px` }}>
          <text x={cx} y={cy - 2} textAnchor="middle" fontSize="11" fill="var(--ink-3)">{centerLabel}</text>
          <text x={cx} y={cy + 18} textAnchor="middle" fontSize="20" fill="var(--ink)" fontWeight="500" style={{ fontFamily: 'var(--font-display)' }}>{centerValue}</text>
        </g>
      )}
    </svg>
  );
};

// Horizontal bar for categories
const Bars = ({ data, accent = 'var(--accent)' }) => {
  const max = Math.max(...data.map(d => d.value));
  return (
    <div className="bars">
      {data.map((d, i) => (
        <div key={i} className="bar-row">
          <div className="bar-label">
            <span className="cat-badge">
              <span className="sw" style={{ background: d.color || 'var(--surface-2)', color: d.fg || 'var(--ink-2)' }}>{d.icon || ''}</span>
              <span>{d.label}</span>
            </span>
          </div>
          <div className="bar">
            <span style={{ width: `${(d.value / max) * 100}%`, background: d.color || accent }}></span>
          </div>
          <div className="bar-val num">${d.value.toLocaleString()}</div>
        </div>
      ))}
    </div>
  );
};

window.AreaChart = AreaChart;
window.Sparkline = Sparkline;
window.Donut = Donut;
window.Bars = Bars;
