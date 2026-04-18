import { Sun, Pause, Play, RotateCcw, Brain, ChevronDown } from 'lucide-react';

export default function Header({ simState, paused, speed, setSpeed, togglePause, reset, policyLoaded, onShowTraining }) {
  const h = Math.floor(simState.utcHour);
  const m = Math.floor((simState.utcHour % 1) * 60);
  const clock = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')} UTC — Day ${simState.day}`;

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-bg-secondary">
      <div className="flex items-center gap-3">
        <Sun className="w-6 h-6 text-accent-amber" />
        <span className="text-lg font-bold tracking-tight">GreenRoute</span>
        <span className="text-xs text-slate-500 hidden sm:inline ml-1">Renewable-Aware Workload Shifting</span>
      </div>

      <div className="flex items-center gap-4">
        {/* Policy status */}
        <button
          onClick={onShowTraining}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs border transition-all
            ${policyLoaded
              ? 'bg-accent-green/10 border-accent-green/30 text-accent-green hover:bg-accent-green/20'
              : 'bg-accent-amber/10 border-accent-amber/30 text-accent-amber'
            }`}
        >
          <Brain className="w-3.5 h-3.5" />
          {policyLoaded ? 'PPO (Actor-Critic)' : 'Initialising PPO...'}
          <ChevronDown className="w-3 h-3" />
        </button>

        <label className="flex items-center gap-2 text-xs text-slate-500">
          Speed
          <input
            type="range"
            min={1}
            max={10}
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            className="w-24 accent-accent-green"
          />
        </label>

        <button
          onClick={togglePause}
          className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm border transition-all
            ${paused
              ? 'bg-accent-green text-bg-primary border-accent-green'
              : 'bg-bg-card text-slate-200 border-border hover:border-accent-green hover:text-accent-green'
            }`}
        >
          {paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
          {paused ? 'Resume' : 'Pause'}
        </button>

        <button
          onClick={reset}
          className="flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm border border-border
                     bg-bg-card text-slate-200 hover:border-accent-green hover:text-accent-green transition-all"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset
        </button>

        <div className="font-mono text-sm text-accent-amber min-w-[160px] text-right">
          {clock}
        </div>
      </div>
    </header>
  );
}
