import { getBaselineMetrics } from '../simulation/engine';
import { motion } from 'framer-motion';

export default function BaselineComparison({ simState }) {
  const m = getBaselineMetrics();
  if (!m || m.rl.jobs < 3) return null;

  const agents = [
    { key: 'random', label: 'Random', icon: '🎲', color: '#ff5252', bg: 'bg-red-500/10' },
    { key: 'rl',     label: 'PPO', icon: '🧠', color: '#00e676', bg: 'bg-green-500/10' },
  ];

  // Find max for bar scaling
  const maxCarbon = Math.max(1, ...agents.map(a => m[a.key].carbonSaved));

  // RL advantage over random
  const rlVsRandom = m.random.carbonSaved > 0
    ? ((m.rl.carbonSaved - m.random.carbonSaved) / m.random.carbonSaved * 100).toFixed(0)
    : '∞';

  return (
    <div className="px-4 py-3 bg-bg-secondary/80 backdrop-blur border-t border-border">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[10px] uppercase tracking-[1.5px] text-slate-500 font-medium">
          Live Agent Comparison
        </h3>
        <span className="text-[9px] text-slate-600 font-mono">{m.rl.jobs} jobs processed</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {agents.map((agent) => {
          const data = m[agent.key];
          const carbonPct = (data.carbonSaved / maxCarbon) * 100;
          const avgRenew = data.jobs > 0 ? (data.renewableSum / data.jobs * 100).toFixed(0) : '0';
          const isWinner = agent.key === 'rl' && m.rl.carbonSaved >= m.random.carbonSaved && m.rl.jobs > 20;

          return (
            <div
              key={agent.key}
              className={`rounded-lg p-3 border transition-all ${
                isWinner
                  ? 'border-accent-green/40 bg-accent-green/5'
                  : 'border-border bg-bg-card/50'
              }`}
            >
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-sm">{agent.icon}</span>
                <span className="text-xs font-bold" style={{ color: agent.color }}>
                  {agent.label}
                </span>
                {isWinner && (
                  <span className="text-[8px] bg-accent-green/20 text-accent-green px-1.5 py-0.5 rounded-full ml-auto font-bold">
                    BEST
                  </span>
                )}
              </div>

              {/* Carbon saved — main metric */}
              <div className="mb-2">
                <motion.div
                  className="text-lg font-bold font-mono leading-none"
                  style={{ color: agent.color }}
                  key={Math.round(data.carbonSaved)}
                  initial={{ scale: 1.05 }}
                  animate={{ scale: 1 }}
                >
                  {Math.round(data.carbonSaved).toLocaleString()}
                </motion.div>
                <div className="text-[9px] text-slate-500 mt-0.5">gCO₂ saved</div>
              </div>

              {/* Carbon bar */}
              <div className="h-1.5 bg-white/5 rounded-full overflow-hidden mb-2">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: agent.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.max(2, carbonPct)}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>

              {/* Secondary metrics */}
              <div className="flex justify-between text-[9px]">
                <span className="text-slate-500">♻ {avgRenew}%</span>
                <span className="text-slate-500">${data.costSaved.toFixed(1)}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* RL advantage callout */}
      {m.rl.jobs > 20 && (
        <div className="mt-2 text-center text-[10px] text-slate-400">
          PPO saves{' '}
          <span className="font-bold text-accent-green">
            {rlVsRandom}% more
          </span>{' '}
          CO₂ than Random
        </div>
      )}
    </div>
  );
}
