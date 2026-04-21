import { Sun, Moon, Pause, Play, RotateCcw, Brain, Clock } from 'lucide-react';
import { useState } from 'react';

const SPEED_LABELS = ['', 'Slow', '', 'Normal', '', 'Fast', '', 'Faster', ''];

export default function Header({ simState, paused, speed, setSpeed, togglePause, reset, policyLoaded, onShowTraining, darkMode, setDarkMode, agents = ['PPO', 'Q-Learning', 'DQN', 'Random', 'Greedy'], selectedAgent = 'PPO', onAgentChange = () => {} }) {
  const h = Math.floor(simState.utcHour);
  const m = Math.floor((simState.utcHour % 1) * 60);
  const clock = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')} UTC`;

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-slate-200 dark:border-white/[0.1] bg-white dark:bg-slate-950 relative z-50">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-green-50 dark:bg-green-950/30 flex items-center justify-center border border-green-300 dark:border-accent-green/20">
          <Sun className="w-4.5 h-4.5 text-accent-green" />
        </div>
        <div>
          <span className="text-base font-bold tracking-tight text-slate-900 dark:text-white">GreenRoute</span>
          <span className="text-[10px] text-slate-600 dark:text-slate-500 ml-2 hidden sm:inline">Move Computation to Energy</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Agent selector buttons */}
        <div className="flex items-center gap-1">
          {agents.map((agent) => (
            <button
              key={agent}
              onClick={() => onAgentChange(agent)}
              className={`px-3 py-1.5 rounded text-[11px] font-medium border transition-all
                ${selectedAgent === agent
                  ? 'bg-green-100 dark:bg-green-950/40 border-green-300 dark:border-accent-green/30 text-green-700 dark:text-accent-green'
                  : 'bg-slate-100 dark:bg-white/[0.05] border-slate-300 dark:border-white/[0.1] text-slate-700 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-white/[0.08]'
                }`}
            >
              {agent}
            </button>
          ))}
        </div>

        {/* Speed control */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded border border-slate-300 dark:border-white/[0.1] bg-slate-50 dark:bg-slate-50 dark:bg-white/[0.02]">
          <label htmlFor="speed-slider" className="text-[10px] text-slate-600 dark:text-slate-500 font-medium uppercase tracking-wider">Speed</label>
          <input
            id="speed-slider"
            type="range"
            min={1}
            max={8}
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            aria-label="Simulation speed"
            className="w-20 h-1"
          />
          <span className="text-[10px] text-slate-600 dark:text-slate-400 font-mono w-10 text-right">{SPEED_LABELS[speed] || `${speed}x`}</span>
        </div>

        {/* Pause/Resume */}
        <button
          onClick={togglePause}
          aria-label={paused ? 'Resume simulation' : 'Pause simulation'}
          className={`flex items-center gap-1.5 px-3 sm:px-4 py-1.5 rounded text-sm font-medium border transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-slate-950
            ${paused
              ? 'bg-accent-green text-white border-accent-green hover:bg-green-600'
              : 'bg-white dark:bg-white/[0.05] text-slate-900 dark:text-slate-200 border-slate-300 dark:border-white/[0.1] hover:border-accent-green dark:hover:border-accent-green/50'
            }`}
        >
          {paused ? <Play className="w-3.5 h-3.5 flex-shrink-0" /> : <Pause className="w-3.5 h-3.5 flex-shrink-0" />}
          <span className="hidden sm:inline">{paused ? 'Resume' : 'Pause'}</span>
        </button>

        {/* Reset */}
        <button
          onClick={reset}
          aria-label="Reset simulation"
          title="Reset simulation"
          className="flex items-center justify-center p-2 rounded border border-slate-300 dark:border-white/[0.1]
                     bg-white dark:bg-slate-50 dark:bg-white/[0.02] text-slate-600 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400
                     hover:border-red-400 dark:hover:border-red-400/30 transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-slate-950"
        >
          <RotateCcw className="w-4 h-4" />
        </button>

        {/* Dark mode toggle */}
        <button
          onClick={() => setDarkMode(!darkMode)}
          aria-label={`Switch to ${darkMode ? 'light' : 'dark'} mode`}
          title={`Switch to ${darkMode ? 'light' : 'dark'} mode`}
          className="flex items-center justify-center p-2 rounded border border-slate-300 dark:border-white/[0.1]
                     bg-white dark:bg-slate-50 dark:bg-white/[0.02] text-slate-600 dark:text-slate-400 hover:text-amber-600 dark:hover:text-accent-amber
                     hover:border-amber-400 dark:hover:border-accent-amber/30 transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-slate-950"
        >
          {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Clock */}
        <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-slate-300 dark:border-white/[0.1]">
          <Clock className="w-3.5 h-3.5 text-amber-600 dark:text-accent-amber/70" />
          <div className="text-right">
            <div className="font-mono text-sm text-slate-900 dark:text-accent-amber font-medium">{clock}</div>
            <div className="text-[9px] text-slate-600 dark:text-slate-500">Day {simState.day}</div>
          </div>
        </div>
      </div>
    </header>
  );
}
