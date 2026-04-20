import { LOCATIONS } from '../simulation/locations';
import { motion, AnimatePresence } from 'framer-motion';

export default function DecisionPanel({ decision, job }) {
  if (!decision || !job) {
    return (
      <Section title="Agent Decision">
        <p className="text-xs text-slate-500 italic">Awaiting decision...</p>
      </Section>
    );
  }

  const destLoc = LOCATIONS[decision.dest];
  const saving = decision.saving;
  const confPct = Math.round(decision.confidence * 100);

  return (
    <Section title="Agent Decision">
      <AnimatePresence mode="wait">
        <motion.div
          key={decision.dest + decision.destCarbon}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 8 }}
          transition={{ duration: 0.2 }}
        >
          <Row
            label="Route to"
            value={`${destLoc.name.toUpperCase()} ${destLoc.emoji}`}
            valueClass="text-accent-green font-bold"
          />
          <Row
            label="Carbon at dest"
            value={`${Math.round(decision.destCarbon)} gCO₂/kWh`}
            valueClass="text-accent-green"
          />
          <Row
            label="vs Origin"
            value={`${Math.round(decision.originCarbon)} gCO₂/kWh`}
            valueClass="text-accent-red"
          />
          <Row
            label="Saving"
            value={`${saving > 0 ? '+' : ''}${saving}g CO₂`}
            valueClass={saving > 0 ? 'text-accent-green' : 'text-accent-red'}
          />

          {/* Confidence bar */}
          <div className="mt-3">
            <div className="w-full h-1.5 bg-bg-primary rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-accent-green rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${confPct}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
            <div className="text-right text-[10px] text-slate-500 mt-1">
              Confidence: <span className="text-slate-300 font-mono">{confPct}%</span>
            </div>
          </div>

          {/* Policy source */}
          <div className="mt-2 flex items-center gap-2">
            <span
              className={`inline-block text-[10px] px-2 py-0.5 rounded-full font-medium tracking-wide
                ${decision.policySource === 'hold'
                  ? 'bg-purple-500/15 text-purple-400'
                  : decision.policySource === 'ppo_confident'
                  ? 'bg-accent-green/15 text-accent-green'
                  : decision.policySource === 'ppo_exploring'
                  ? 'bg-accent-cyan/15 text-accent-cyan'
                  : decision.policySource === 'constraint'
                  ? 'bg-accent-amber/15 text-accent-amber'
                  : 'bg-slate-500/15 text-slate-400'
                }`}
            >
              {decision.policySource === 'hold' ? '⏸ Holding — Waiting for Better Window' :
               decision.policySource === 'ppo_confident' ? '🧠 PPO Policy (Confident)' :
               decision.policySource === 'ppo_exploring' ? '🔍 PPO Policy (Exploring)' :
               decision.policySource === 'constraint' ? '🔒 Hard Constraint' : 'Fallback'}
            </span>
          </div>

          {/* Reasoning */}
          <div className="mt-3 px-3 py-2.5 bg-bg-primary rounded-md border-l-2 border-accent-green">
            <p className="text-xs text-slate-400 leading-relaxed">{decision.reason}</p>
          </div>
        </motion.div>
      </AnimatePresence>
    </Section>
  );
}

function Section({ title, children }) {
  return (
    <div className="px-5 py-4 border-b border-white/[0.06]">
      <h3 className="text-[10px] uppercase tracking-[1.5px] text-slate-500 mb-3 font-medium">
        {title}
      </h3>
      {children}
    </div>
  );
}

function Row({ label, value, valueClass = '' }) {
  return (
    <div className="flex justify-between items-center py-1 text-sm">
      <span className="text-slate-400">{label}</span>
      <span className={`font-semibold font-mono text-xs ${valueClass}`}>{value}</span>
    </div>
  );
}
