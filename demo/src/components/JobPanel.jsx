import { LOCATIONS } from '../simulation/locations';
import { motion, AnimatePresence } from 'framer-motion';

export default function JobPanel({ job }) {
  if (!job) {
    return (
      <Section title="Current Job">
        <p className="text-xs text-slate-500 italic">Waiting for next job...</p>
      </Section>
    );
  }

  const originLoc = LOCATIONS[job.origin];

  return (
    <Section title="Current Job">
      <AnimatePresence mode="wait">
        <motion.div
          key={job.name + job.origin + job.compute}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 8 }}
          transition={{ duration: 0.2 }}
        >
          <Row label="Type" value={job.name} valueClass="text-accent-cyan" />
          <Row
            label="Origin"
            value={`${originLoc.name} (${job.origin})`}
            valueClass="text-accent-amber"
          />
          <Row label="Compute" value={`${job.compute} TFLOPS`} />
          <Row
            label="Max Delay"
            value={job.maxLatency > 0 ? `${job.maxLatency.toFixed(1)} hours` : 'Real-time'}
          />
          <div className="mt-1.5">
            <span
              className={`inline-block text-[10px] px-2 py-0.5 rounded-full font-medium tracking-wide
                ${job.type === 'FLEXIBLE' ? 'bg-accent-cyan/15 text-accent-cyan' :
                  job.type === 'SEMI_FLEX' ? 'bg-accent-amber/15 text-accent-amber' :
                  'bg-accent-red/15 text-accent-red'}`}
            >
              {job.type.replace('_', ' ')}
            </span>
          </div>
        </motion.div>
      </AnimatePresence>
    </Section>
  );
}

function Section({ title, children }) {
  return (
    <div className="px-5 py-4 border-b border-border">
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
