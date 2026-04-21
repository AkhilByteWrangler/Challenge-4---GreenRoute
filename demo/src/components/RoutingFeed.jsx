import { LOCATIONS } from '../simulation/locations';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

export default function RoutingFeed({ feedItems }) {
  return (
    <div className="px-5 py-4 border-b border-slate-200 dark:border-white/[0.1]">
      <h3 className="text-[10px] uppercase tracking-[1.5px] text-slate-600 dark:text-slate-500 mb-3 font-semibold">
        Routing Feed
      </h3>
      <div className="max-h-48 overflow-y-auto space-y-0.5">
        <AnimatePresence initial={false}>
          {feedItems.map((item) => (
            <FeedItem key={item.id} item={item} />
          ))}
        </AnimatePresence>
        {feedItems.length === 0 && (
          <p className="text-xs text-slate-500 dark:text-slate-600 italic">No routing decisions yet...</p>
        )}
      </div>
    </div>
  );
}

function FeedItem({ item }) {
  const { job, decision, carbonSaved, held, released, releaseReason } = item;
  const destLoc = LOCATIONS[decision.dest];
  const isPositive = carbonSaved > 0;

  // Held job — show pause indicator
  if (held) {
    return (
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.25 }}
        className="flex items-center gap-2 py-1.5 text-xs border-b border-cyan-200 dark:border-accent-cyan/20 bg-cyan-50 dark:bg-cyan-950/20 rounded px-1"
      >
        <span className="text-sm shrink-0">[H]</span>
        <span className="text-slate-600 dark:text-slate-500 w-6 shrink-0 font-mono">{job.origin}</span>
        <span className="text-cyan-600 dark:text-accent-cyan font-semibold shrink-0">HELD</span>
        <span className="text-slate-600 dark:text-slate-500 truncate flex-1">
          {job.name.split(' ').slice(0, 2).join(' ')}
        </span>
        <span className="font-mono text-[10px] text-cyan-600 dark:text-accent-cyan shrink-0">waiting...</span>
      </motion.div>
    );
  }

  // Released held job
  if (released) {
    return (
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.25 }}
        className="flex items-center gap-2 py-1.5 text-xs border-b border-green-200 dark:border-accent-green/20 bg-green-50 dark:bg-green-950/20 rounded px-1"
      >
        <span className="text-sm shrink-0">▶</span>
        <span className="text-slate-600 dark:text-slate-500 w-6 shrink-0 font-mono">{job.origin}</span>
        <span className="text-green-600 dark:text-accent-green font-semibold shrink-0">RELEASED</span>
        <span className="text-slate-600 dark:text-slate-500 truncate flex-1">
          {releaseReason === 'conditions_improved' ? 'carbon dropped' : 'timeout'}
        </span>
      </motion.div>
    );
  }

  // Normal routed job
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      className="flex items-center gap-2 py-1.5 text-xs border-b border-slate-200 dark:border-white/[0.05]"
    >
      <span
        className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ background: isPositive ? '#10b981' : '#ef4444' }}
      />
      <span className="text-slate-600 dark:text-slate-500 w-6 shrink-0 font-mono">{job.origin}</span>
      <ArrowRight className="w-3 h-3 text-green-600 dark:text-accent-green shrink-0" />
      <span className="font-semibold shrink-0" style={{ color: destLoc.colour, opacity: 0.85 }}>
        {decision.dest}
      </span>
      <span className="text-slate-600 dark:text-slate-500 truncate flex-1">
        {job.name.split(' ').slice(0, 2).join(' ')}
      </span>
      <span
        className={`font-mono text-[11px] shrink-0 ${isPositive ? 'text-green-600 dark:text-accent-green' : 'text-red-600 dark:text-accent-red'}`}
      >
        {isPositive ? '-' : '+'}
        {Math.abs(Math.round(carbonSaved))}g
      </span>
    </motion.div>
  );
}
