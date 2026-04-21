import { getLearningMetrics } from '../simulation/engine';
import { LOCATIONS, LOC_IDS } from '../simulation/locations';

export default function LearningPanel({ simState }) {
  const m = getLearningMetrics();
  if (!m || m.totalSteps < 1) return null;

  const totalActions = Object.values(m.actionDistribution).reduce((a, b) => a + b, 0) || 1;

  // Entropy: max entropy for 5 actions = ln(5) ≈ 1.61
  const maxEntropy = Math.log(5);
  const entropyPct = Math.min(100, (m.epsilon / maxEntropy) * 100);
  const convergencePct = 100 - entropyPct;

  // Phase label based on entropy
  let phase = 'Training (High Entropy)';
  let phaseColor = 'text-accent-amber';
  if (m.epsilon < 0.5) { phase = 'Converged Policy'; phaseColor = 'text-accent-green'; }
  else if (m.epsilon < 1.0) { phase = 'Refining Policy'; phaseColor = 'text-accent-cyan'; }

  return (
    <div className="px-5 py-4 border-b border-white/[0.06]">
      <h3 className="text-[10px] uppercase tracking-[1.5px] text-slate-500 mb-3 font-medium flex items-center gap-2">
        <span className="w-1 h-3 rounded-full bg-accent-green" />
        PPO Agent (Actor-Critic)
      </h3>

      {/* Phase indicator */}
      <div className="flex items-center justify-between mb-3">
        <span className={`text-xs font-bold ${phaseColor}`}>{phase}</span>
        <span className="text-[10px] text-slate-500 font-mono">Step {m.totalSteps}</span>
      </div>

      {/* Entropy → Convergence bar */}
      <div className="mb-3">
        <div className="flex justify-between text-[10px] mb-1">
          <span className="text-amber-400">Entropy {entropyPct.toFixed(0)}%</span>
          <span className="text-green-400">Converged {convergencePct.toFixed(0)}%</span>
        </div>
        <div className="w-full h-2 bg-bg-primary rounded-full overflow-hidden flex">
          <div
            className="h-full bg-amber-500/60 transition-all duration-500"
            style={{ width: `${entropyPct}%` }}
          />
          <div
            className="h-full bg-green-500/60 transition-all duration-500"
            style={{ width: `${convergencePct}%` }}
          />
        </div>
        <div className="text-[9px] text-slate-600 mt-1 font-mono">
          H(π) = {m.epsilon.toFixed(3)} / {maxEntropy.toFixed(2)} nats
        </div>
      </div>

      {/* NN status + Avg reward */}
      <div className="flex justify-between items-center mb-2 text-xs">
        <span className="text-slate-500">Neural Network</span>
        <span className={`font-mono font-bold ${m.statesExplored ? 'text-accent-green' : 'text-accent-amber'}`}>
          {m.statesExplored ? '✓ Loaded' : '⏳ Loading...'}
        </span>
      </div>
      <div className="flex justify-between items-center mb-3 text-xs">
        <span className="text-slate-500">Avg Reward (50)</span>
        <span className={`font-mono font-bold ${m.avgReward50 > 0.5 ? 'text-accent-green' : m.avgReward50 > 0 ? 'text-accent-amber' : 'text-accent-red'}`}>
          {m.avgReward50.toFixed(3)}
        </span>
      </div>

      {/* Architecture info */}
      <div className="text-[9px] text-slate-600 mb-3 font-mono leading-relaxed">
        67→256→256 (backbone) → 5 actions<br/>
        Trained: 5000 ep · Stochastic weather<br/>
        GAE(λ=0.95) · Clip(ε=0.2) · 8 epochs
      </div>

      {/* Action distribution */}
      <div className="space-y-1.5">
        <div className="text-[10px] text-slate-500 mb-1">Policy π(a|s) — Last 30 Steps</div>
        {LOC_IDS.map((id) => {
          const count = m.actionDistribution[id] || 0;
          const pct = (count / totalActions) * 100;
          const loc = LOCATIONS[id];
          return (
            <div key={id} className="flex items-center gap-2">
              <span className="text-[10px] w-6 font-mono text-slate-500">{id}</span>
              <div className="flex-1 h-1.5 bg-bg-primary rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out"
                  style={{ width: `${Math.max(2, pct)}%`, backgroundColor: loc.colour }}
                />
              </div>
              <span className="text-[10px] w-8 text-right font-mono text-slate-400">
                {pct.toFixed(0)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
