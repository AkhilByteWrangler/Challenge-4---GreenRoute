import { LOCATIONS } from '../simulation/locations';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

export default function RoutingFeed({ feedItems }) {
  return (
    <div className="px-5 py-4 border-b border-border">
      <h3 className="text-[10px] uppercase tracking-[1.5px] text-slate-500 mb-3 font-medium">
        Routing Feed
      </h3>
      <div className="max-h-48 overflow-y-auto space-y-0.5">
        <AnimatePresence initial={false}>
          {feedItems.map((item) => (
            <FeedItem key={item.id} item={item} />
          ))}
        </AnimatePresence>
        {feedItems.length === 0 && (
          <p className="text-xs text-slate-600 italic">No routing decisions yet...</p>
        )}
      </div>
    </div>
  );
}

function FeedItem({ item }) {
  const { job, decision, carbonSaved } = item;
  const destLoc = LOCATIONS[decision.dest];
  const isPositive = carbonSaved > 0;

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      className="flex items-center gap-2 py-1.5 text-xs border-b border-white/[0.03]"
    >
      <span
        className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ background: isPositive ? '#00e676' : '#ff5252' }}
      />
      <span className="text-slate-500 w-6 shrink-0 font-mono">{job.origin}</span>
      <ArrowRight className="w-3 h-3 text-accent-green shrink-0" />
      <span className="font-semibold shrink-0" style={{ color: destLoc.colour }}>
        {decision.dest} {destLoc.emoji}
      </span>
      <span className="text-slate-500 truncate flex-1">
        {job.name.split(' ').slice(0, 2).join(' ')}
      </span>
      <span
        className={`font-mono text-[11px] shrink-0 ${isPositive ? 'text-accent-green' : 'text-accent-red'}`}
      >
        {isPositive ? '-' : '+'}
        {(Math.abs(carbonSaved) / 1_000_000).toFixed(4)}t
      </span>
    </motion.div>
  );
}
