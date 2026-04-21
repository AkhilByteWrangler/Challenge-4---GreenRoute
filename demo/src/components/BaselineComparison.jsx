import { getBaselineMetrics } from '../simulation/engine';
import { motion } from 'framer-motion';

export default function BaselineComparison({ simState, darkMode }) {
  const m = getBaselineMetrics();

  const agents = [
    { key: 'random', label: 'Random', color: '#ff5252', bg: 'bg-red-500/10' },
    { key: 'rl',     label: 'PPO', color: '#00e676', bg: 'bg-green-500/10' },
  ];

  // If no data yet, show empty state
  if (!m) {
    return (
      <div className={`px-4 py-3 backdrop-blur border-t ${
        darkMode
          ? 'bg-gradient-to-r from-[#0a0e1a] via-[#0d1220] to-[#0a0e1a] border-white/[0.1]'
          : 'bg-gradient-to-r from-slate-100 via-slate-50 to-slate-100 border-slate-300'
      }`}>
        <div className="flex items-center justify-between mb-2">
          <h3 className={`text-[10px] uppercase tracking-[1.5px] font-medium ${
            darkMode ? 'text-slate-500' : 'text-slate-600'
          }`}>
            Live Agent Comparison
          </h3>
          <span className={`text-[9px] font-mono ${
            darkMode ? 'text-slate-600' : 'text-slate-500'
          }`}>Initializing...</span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {agents.map((agent) => (
            <div key={agent.key} className={`rounded-lg p-3 border ${
              darkMode
                ? 'border-white/[0.1] bg-white/[0.02]'
                : 'border-slate-300 bg-slate-100'
            }`}>
              <div className="text-xs font-bold mb-2" style={{ color: agent.color }}>
                {agent.label}
              </div>
              <div className={`text-lg font-bold font-mono mb-2 ${
                darkMode ? 'text-slate-400' : 'text-slate-400'
              }`}>—</div>
              <div className={`h-1.5 rounded-full mb-2 ${
                darkMode ? 'bg-white/5' : 'bg-slate-300'
              }`}></div>
              <div className={`text-[9px] ${
                darkMode ? 'text-slate-500' : 'text-slate-600'
              }`}>Waiting for data...</div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Find max for bar scaling
  const maxCarbon = Math.max(1, ...agents.map(a => m[a.key].carbonSaved));

  // RL advantage over random
  const rlVsRandom = m.random.carbonSaved > 0
    ? ((m.rl.carbonSaved - m.random.carbonSaved) / m.random.carbonSaved * 100).toFixed(0)
    : '>100';

  return (
    <div className={`px-4 py-3 backdrop-blur border-t ${
      darkMode
        ? 'bg-gradient-to-r from-[#0a0e1a] via-[#0d1220] to-[#0a0e1a] border-white/[0.1]'
        : 'bg-gradient-to-r from-slate-100 via-slate-50 to-slate-100 border-slate-300'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className={`text-[10px] uppercase tracking-[1.5px] font-medium ${
          darkMode ? 'text-slate-500' : 'text-slate-600'
        }`}>
          Live Agent Comparison
        </h3>
        <span className={`text-[9px] font-mono ${
          darkMode ? 'text-slate-600' : 'text-slate-500'
        }`}>{m.rl.jobs} jobs processed</span>
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
                  ? darkMode
                    ? 'border-accent-green/30 bg-accent-green/5 shadow-lg shadow-green-500/5'
                    : 'border-green-400 bg-green-50 shadow-lg shadow-green-200'
                  : darkMode
                    ? 'border-white/[0.1] bg-white/[0.02]'
                    : 'border-slate-300 bg-slate-100'
              }`}
            >
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-xs font-bold" style={{ color: agent.color }}>
                  {agent.label}
                </span>
                {isWinner && (
                  <span className={`text-[8px] px-1.5 py-0.5 rounded-full ml-auto font-bold ${
                    darkMode
                      ? 'bg-accent-green/20 text-accent-green'
                      : 'bg-green-200 text-green-800'
                  }`}>
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
                <div className={`text-[9px] mt-0.5 ${
                  darkMode ? 'text-slate-500' : 'text-slate-600'
                }`}>g CO₂ saved</div>
              </div>

              {/* Carbon bar */}
              <div className={`h-1.5 rounded-full overflow-hidden mb-2 ${
                darkMode ? 'bg-white/5' : 'bg-slate-300'
              }`}>
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
                <span className={darkMode ? 'text-slate-500' : 'text-slate-600'}>Renewable: {avgRenew}%</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* RL advantage callout */}
      {m.rl.jobs > 20 && (
        <div className={`mt-2 text-center text-[10px] ${
          darkMode ? 'text-slate-400' : 'text-slate-600'
        }`}>
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
