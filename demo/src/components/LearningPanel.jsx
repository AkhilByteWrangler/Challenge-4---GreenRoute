import { getLearningMetrics } from '../simulation/engine';
import { LOCATIONS, LOC_IDS } from '../simulation/locations';

export default function LearningPanel({ simState, selectedAgent = 'PPO' }) {
  const m = getLearningMetrics();

  return (
    <div className="px-5 py-4 border-b border-slate-200 dark:border-white/[0.1]">
      <h3 className="text-[10px] uppercase tracking-[1.5px] text-slate-600 dark:text-slate-500 mb-3 font-semibold flex items-center gap-2">
        <span className="w-1 h-3 rounded-full bg-accent-green" />
        {selectedAgent} Agent
      </h3>

      {!m || m.totalSteps < 1 ? (
        <div className="text-[10px] text-slate-500 dark:text-slate-400 py-4">
          Waiting for metrics...
        </div>
      ) : (
        <>
          {renderMetrics(m)}
        </>
      )}
    </div>
  );
}

function renderMetrics(m) {
  const totalActions = Object.values(m.actionDistribution).reduce((a, b) => a + b, 0) || 1;

  // Entropy: max entropy for 7 actions = ln(7) ≈ 1.95
  const maxEntropy = Math.log(7);
  const entropyPct = Math.min(100, (m.epsilon / maxEntropy) * 100);
  const convergencePct = 100 - entropyPct;

  // Phase label based on entropy
  let phase = 'Training (High Entropy)';
  let phaseColor = 'text-accent-amber';
  if (m.epsilon < 0.5) { phase = 'Converged Policy'; phaseColor = 'text-accent-green'; }
  else if (m.epsilon < 1.0) { phase = 'Refining Policy'; phaseColor = 'text-accent-cyan'; }

  return (
    <>

      {/* Phase indicator */}
      <div className="flex items-center justify-between mb-3">
        <span className={`text-xs font-bold ${phaseColor}`}>{phase}</span>
        <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">Step {m.totalSteps}</span>
      </div>

      {/* Entropy / Convergence bar */}
      <div className="mb-3">
        <div className="flex justify-between text-[10px] mb-1">
          <span className="text-amber-600 dark:text-amber-400">Entropy {entropyPct.toFixed(0)}%</span>
          <span className="text-green-600 dark:text-green-400">Converged {convergencePct.toFixed(0)}%</span>
        </div>
        <div className="w-full h-2 bg-slate-100 dark:bg-white/[0.05] rounded overflow-hidden flex">
          <div
            className="h-full bg-amber-500 dark:bg-amber-500 transition-all duration-500"
            style={{ width: `${entropyPct}%` }}
            role="progressbar"
            aria-valuenow={entropyPct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Entropy percentage"
          />
          <div
            className="h-full bg-green-500 dark:bg-green-500 transition-all duration-500"
            style={{ width: `${convergencePct}%` }}
            role="progressbar"
            aria-valuenow={convergencePct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Convergence percentage"
          />
        </div>
        <div className="text-[9px] text-slate-600 dark:text-slate-500 mt-1 font-mono">
          H(π) = {m.epsilon.toFixed(3)} / {maxEntropy.toFixed(2)} nats
        </div>
      </div>

      {/* NN status + Avg reward */}
      <div className="flex justify-between items-center mb-2 text-xs">
        <span className="text-slate-700 dark:text-slate-400">Neural Network</span>
        <span className={`font-mono font-bold ${m.statesExplored ? 'text-green-600 dark:text-accent-green' : 'text-amber-600 dark:text-accent-amber'}`}>
          {m.statesExplored ? '✓ Loaded' : '⏳ Loading...'}
        </span>
      </div>
      <div className="flex justify-between items-center mb-3 text-xs">
        <span className="text-slate-700 dark:text-slate-400">Avg Reward (50)</span>
        <span className={`font-mono font-bold ${m.avgReward50 > 0.5 ? 'text-green-600 dark:text-accent-green' : m.avgReward50 > 0 ? 'text-amber-600 dark:text-accent-amber' : 'text-red-600 dark:text-accent-red'}`}>
          {m.avgReward50.toFixed(3)}
        </span>
      </div>

      {/* Architecture info */}
      <div className="text-[9px] text-slate-600 dark:text-slate-500 mb-3 font-mono leading-relaxed">
        67-256-256 (backbone) - 7 actions<br/>
        Trained: 5000 ep · Stochastic weather<br/>
        GAE(λ=0.95) · Clip(ε=0.2) · 10 epochs
      </div>

      {/* Action distribution */}
      <div className="space-y-1.5">
        <div className="text-[10px] text-slate-600 dark:text-slate-500 mb-1 font-medium">Policy π(a|s) — Last 30 Steps</div>
        {LOC_IDS.map((id) => {
          const count = m.actionDistribution[id] || 0;
          const pct = (count / totalActions) * 100;
          const loc = LOCATIONS[id];
          return (
            <div key={id} className="flex items-center gap-2">
              <span className="text-[10px] w-6 font-mono text-slate-600 dark:text-slate-500">{id}</span>
              <div className="flex-1 h-1.5 bg-slate-200 dark:bg-white/[0.05] rounded overflow-hidden">
                <div
                  className="h-full transition-all duration-700 ease-out rounded"
                  style={{ width: `${Math.max(2, pct)}%`, backgroundColor: loc.colour, opacity: 0.85 }}
                  role="progressbar"
                  aria-valuenow={pct}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`${id}: ${pct.toFixed(0)}% action probability`}
                />
              </div>
              <span className="text-[10px] w-8 text-right font-mono text-slate-600 dark:text-slate-400">
                {pct.toFixed(0)}%
              </span>
            </div>
          );
        })}
      </div>
    </>
  );
}
