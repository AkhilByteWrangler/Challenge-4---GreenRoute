import { motion } from 'framer-motion';

export default function NodeTooltip({ data, onClose }) {
  const { x, y, loc, solar, wind, rf, carbon, cost, util } = data;
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0 }}
      className="absolute z-50 bg-bg-card/95 backdrop-blur-md border border-border rounded-lg p-4 shadow-2xl min-w-[240px] pointer-events-none"
      style={{ left: x, top: Math.max(y, 10) }}
    >
      <div className="font-bold text-sm mb-1" style={{ color: loc.colour }}>
        {loc.emoji} {loc.name}
      </div>
      <div className="text-[10px] text-slate-500 mb-2">
        Primary: {loc.primary} · PUE {loc.basePUE} · {loc.capacity} TFLOPS
      </div>
      <div className="space-y-1.5">
        <BarRow label="☀ Solar" value={`${Math.round(solar)} W/m²`} pct={solar / 1000} color="#FFB300" />
        <BarRow label="💨 Wind" value={`${wind.toFixed(1)} m/s`} pct={wind / 20} color="#00BCD4" />
        <BarRow label="♻ Renewable" value={`${(rf * 100).toFixed(0)}%`} pct={rf} color={rf > 0.5 ? '#00e676' : '#ff5252'} />
        <BarRow label="⚡ Carbon" value={`${Math.round(carbon)} gCO₂`} pct={Math.min(1, carbon / 500)} color={carbon < 200 ? '#00e676' : carbon < 400 ? '#FFB300' : '#ff5252'} />
        <BarRow label="📊 Load" value={`${(util * 100).toFixed(0)}%`} pct={util} color={util > 0.8 ? '#ff5252' : '#40c4ff'} />
      </div>
    </motion.div>
  );
}

function BarRow({ label, value, pct, color }) {
  return (
    <div className="text-xs">
      <div className="flex justify-between mb-0.5">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono text-slate-200">{value}</span>
      </div>
      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.max(2, pct * 100)}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between py-0.5 text-xs">
      <span className="text-slate-500">{label}</span>
      <span className="font-mono text-slate-300">{value}</span>
    </div>
  );
}
