import { Sun, Pause, Play, RotateCcw, Brain, ChevronDown, Clock } from 'lucide-react';

const SPEED_LABELS = ['', 'Slow', '', 'Normal', '', 'Fast', '', 'Faster', ''];

export default function Header({ simState, paused, speed, setSpeed, togglePause, reset, policyLoaded, onShowTraining }) {
  const h = Math.floor(simState.utcHour);
  const m = Math.floor((simState.utcHour % 1) * 60);
  const clock = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')} UTC`;

  return (
    <header className="flex items-center justify-between px-6 py-2.5 border-b border-white/[0.06] bg-gradient-to-r from-[#0a0e1a] via-[#0d1220] to-[#0a0e1a] backdrop-blur-xl">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-green/20 to-accent-green/5 flex items-center justify-center border border-accent-green/20">
          <Sun className="w-4.5 h-4.5 text-accent-green" />
        </div>
        <div>
          <span className="text-base font-bold tracking-tight bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">GreenRoute</span>
          <span className="text-[10px] text-slate-500 ml-2 hidden sm:inline">Move Computation to Energy</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3">
        {/* Policy badge */}
        <button
          onClick={onShowTraining}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium border transition-all
            ${policyLoaded
              ? 'bg-accent-green/8 border-accent-green/20 text-accent-green hover:bg-accent-green/15'
              : 'bg-accent-amber/10 border-accent-amber/30 text-accent-amber animate-pulse'
            }`}
        >
          <Brain className="w-3.5 h-3.5" />
          {policyLoaded ? 'PPO Agent' : 'Loading...'}
          <ChevronDown className="w-3 h-3 opacity-50" />
        </button>

        {/* Speed control */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-white/[0.03] border border-white/[0.06]">
          <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">Speed</span>
          <input
            type="range"
            min={1}
            max={8}
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            className="w-20 accent-accent-green h-1"
          />
          <span className="text-[10px] text-slate-400 font-mono w-10">{SPEED_LABELS[speed] || `${speed}x`}</span>
        </div>

        {/* Pause/Resume */}
        <button
          onClick={togglePause}
          className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm font-medium border transition-all
            ${paused
              ? 'bg-accent-green text-[#0a0e1a] border-accent-green shadow-lg shadow-accent-green/20'
              : 'bg-white/[0.04] text-slate-200 border-white/[0.08] hover:border-accent-green/40 hover:text-accent-green'
            }`}
        >
          {paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
          {paused ? 'Resume' : 'Pause'}
        </button>

        {/* Reset */}
        <button
          onClick={reset}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border border-white/[0.06]
                     bg-white/[0.03] text-slate-400 hover:border-red-400/30 hover:text-red-400 transition-all"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

        {/* Clock */}
        <div className="flex items-center gap-2 pl-3 border-l border-white/[0.06]">
          <Clock className="w-3.5 h-3.5 text-accent-amber/70" />
          <div className="text-right">
            <div className="font-mono text-sm text-accent-amber font-medium">{clock}</div>
            <div className="text-[9px] text-slate-500">Day {simState.day}</div>
          </div>
        </div>
      </div>
    </header>
  );
}
