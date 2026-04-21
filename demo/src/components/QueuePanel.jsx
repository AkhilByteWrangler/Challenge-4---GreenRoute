import { motion, AnimatePresence } from 'framer-motion';
import { getHoldQueue, getQueueStats } from '../simulation/engine';

export default function QueuePanel({ simState }) {
  const holdQueue = getHoldQueue();
  const stats = getQueueStats();
  const totalJobs = stats.flexible + stats.semiFlex + stats.pinned;

  // Percentages for composition bar
  const flexPct = totalJobs > 0 ? (stats.flexible / totalJobs * 100) : 0;
  const semiPct = totalJobs > 0 ? (stats.semiFlex / totalJobs * 100) : 0;
  const pinnedPct = totalJobs > 0 ? (stats.pinned / totalJobs * 100) : 0;

  return (
    <div className="px-5 py-4 border-b border-slate-200 dark:border-white/[0.1]">
      <h3 className="text-[10px] uppercase tracking-[1.5px] text-slate-600 dark:text-slate-500 mb-3 font-semibold flex items-center gap-2">
        <span className="w-1 h-3 rounded-full bg-accent-cyan" />
        Queue & Hold Decisions
      </h3>

      {/* Queue composition bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-[9px] text-slate-600 dark:text-slate-500 mb-1">
          <span>Job composition ({totalJobs} total)</span>
          <span className="font-mono">{stats.held} held</span>
        </div>
        <div className="h-3 bg-slate-200 dark:bg-white/[0.05] rounded overflow-hidden flex">
          {flexPct > 0 && (
            <motion.div
              className="h-full bg-cyan-500 dark:bg-accent-cyan"
              style={{ width: `${flexPct}%` }}
              title={`Flexible: ${stats.flexible}`}
              role="progressbar"
              aria-valuenow={flexPct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Flexible jobs: ${stats.flexible}`}
            />
          )}
          {semiPct > 0 && (
            <motion.div
              className="h-full bg-amber-500 dark:bg-accent-amber"
              style={{ width: `${semiPct}%` }}
              title={`Semi-flex: ${stats.semiFlex}`}
              role="progressbar"
              aria-valuenow={semiPct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Semi-flexible jobs: ${stats.semiFlex}`}
            />
          )}
          {pinnedPct > 0 && (
            <motion.div
              className="h-full bg-red-500 dark:bg-accent-red"
              style={{ width: `${pinnedPct}%` }}
              title={`Pinned: ${stats.pinned}`}
              role="progressbar"
              aria-valuenow={pinnedPct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Pinned jobs: ${stats.pinned}`}
            />
          )}
        </div>
        <div className="flex gap-3 mt-1.5 text-[9px]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-500 dark:bg-accent-cyan inline-block" />
            <span className="text-slate-700 dark:text-slate-400">Flexible {stats.flexible}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500 dark:bg-accent-amber inline-block" />
            <span className="text-slate-700 dark:text-slate-400">Semi-flex {stats.semiFlex}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500 dark:bg-accent-red inline-block" />
            <span className="text-slate-700 dark:text-slate-400">Pinned {stats.pinned}</span>
          </span>
        </div>
      </div>

      {/* Hold queue */}
      <div className="mb-1">
        <div className="flex items-center justify-between text-[9px] text-slate-600 dark:text-slate-500 mb-1.5 font-medium">
          <span className="flex items-center gap-1">
            <span className="text-sm">[H]</span> Hold queue
          </span>
          <span className="font-mono">
            {simState.totalHoldDecisions || 0} holds · {simState.totalHoldReleases || 0} released
          </span>
        </div>

        {holdQueue.length === 0 ? (
          <p className="text-[10px] text-slate-500 dark:text-slate-600 italic pl-1">
            No jobs on hold — carbon levels are acceptable
          </p>
        ) : (
          <div className="space-y-1">
            <AnimatePresence>
              {holdQueue.map((entry, i) => (
                <HoldEntry key={`hold-${i}-${entry.heldAt}`} entry={entry} />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Explanation */}
      {(simState.totalHoldDecisions || 0) > 0 && (
        <div className="mt-2 px-2.5 py-2 bg-cyan-50 dark:bg-cyan-950/20 rounded border-l-2 border-cyan-500 dark:border-accent-cyan">
          <p className="text-[10px] text-slate-700 dark:text-slate-300 leading-relaxed">
            The agent held <strong className="text-cyan-700 dark:text-accent-cyan">{simState.totalHoldDecisions}</strong> flexible
            jobs when carbon was high, waiting for renewable energy to come online before routing.
            Greedy agents cannot do this.
          </p>
        </div>
      )}
    </div>
  );
}

function HoldEntry({ entry }) {
  const waitTime = (entry.holdSteps * 0.15 * 60).toFixed(0); // minutes
  const progress = Math.min(100, (entry.holdSteps / 8) * 100);
  const urgent = progress > 75;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className={`rounded px-2.5 py-2 border text-[10px] transition-colors ${
        urgent
          ? 'border-amber-400 dark:border-accent-amber/50 bg-amber-50 dark:bg-amber-950/20'
          : 'border-slate-300 dark:border-white/[0.1] bg-slate-50 dark:bg-slate-50 dark:bg-white/[0.03]'
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="font-semibold text-slate-900 dark:text-slate-100">
          [H] {entry.job.name.split(' ').slice(0, 2).join(' ')}
        </span>
        <span className="text-slate-600 dark:text-slate-400 font-mono">{waitTime}m</span>
      </div>
      <div className="flex items-center gap-2 mb-1 text-[9px]">
        <span className="text-slate-600 dark:text-slate-400">from {entry.job.origin}</span>
        <span className="text-slate-400 dark:text-slate-600">·</span>
        <span className="text-slate-600 dark:text-slate-400">{entry.job.compute} TFLOPS</span>
        <span className="text-slate-400 dark:text-slate-600">·</span>
        <span className="text-cyan-600 dark:text-accent-cyan font-mono">hold={Math.round(entry.holdProb * 100)}%</span>
      </div>
      {/* Timeout progress bar */}
      <div className="h-1 bg-slate-200 dark:bg-white/[0.05] rounded overflow-hidden">
        <motion.div
          className={`h-full rounded ${urgent ? 'bg-amber-500 dark:bg-accent-amber' : 'bg-cyan-500 dark:bg-accent-cyan'}`}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <div className="text-[8px] text-slate-600 dark:text-slate-500 mt-0.5">{entry.reason}</div>
    </motion.div>
  );
}
