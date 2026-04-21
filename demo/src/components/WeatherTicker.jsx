import { LOCATIONS, LOC_IDS } from '../simulation/locations';
import { getSnapshot } from '../simulation/engine';

const EVENT_COLORS = {
  'Cold': { bg: 'bg-blue-100 dark:bg-blue-950/50', border: 'border-blue-400 dark:border-blue-500', text: 'text-blue-900 dark:text-blue-200' },
  'Storm': { bg: 'bg-purple-100 dark:bg-purple-950/50', border: 'border-purple-400 dark:border-purple-500', text: 'text-purple-900 dark:text-purple-200' },
  'Heat': { bg: 'bg-orange-100 dark:bg-orange-950/50', border: 'border-orange-400 dark:border-orange-500', text: 'text-orange-900 dark:text-orange-200' },
  'Solar': { bg: 'bg-yellow-100 dark:bg-yellow-950/50', border: 'border-yellow-400 dark:border-yellow-500', text: 'text-yellow-900 dark:text-yellow-200' },
};

function getEventStyle(label) {
  for (const [key, style] of Object.entries(EVENT_COLORS)) {
    if (label.includes(key)) return style;
  }
  return { bg: 'bg-slate-200 dark:bg-slate-800', border: 'border-slate-400 dark:border-slate-600', text: 'text-slate-900 dark:text-slate-200' };
}

const EVENT_EXPLANATIONS = {
  'Cold': 'Hydro output frozen, solar blocked by snow clouds — carbon intensity spikes',
  'Storm': 'Solar near zero, turbines may curtail at high wind — grid instability',
  'Heat': 'AC demand surge, stagnant air kills wind — fossil generation ramps up',
  'Solar': 'Exceptional clear skies — solar generation peaks, carbon plummets',
};

function getExplanation(label) {
  for (const [key, desc] of Object.entries(EVENT_EXPLANATIONS)) {
    if (label.includes(key)) return desc;
  }
  return '';
}

export default function WeatherTicker() {
  const snap = getSnapshot();

  const activeEvents = [];
  if (snap) {
    for (const locId of LOC_IDS) {
      const s = snap[locId];
      if (s?.weatherEvent) {
        activeEvents.push({ locId, event: s.weatherEvent, carbon: s.carbon, rf: s.rf });
      }
    }
  }

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-900/80 border-b border-slate-200 dark:border-white/[0.1] overflow-x-auto">
      <span className="text-[10px] uppercase tracking-wider text-slate-600 dark:text-slate-500 shrink-0 font-semibold flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 dark:bg-accent-amber" />
        WEATHER
      </span>
      {activeEvents.length > 0 ? (
        activeEvents.map(({ locId, event, carbon, rf }) => {
          const style = getEventStyle(event);
          const loc = LOCATIONS[locId];
          const explanation = getExplanation(event);
          return (
            <div
              key={locId}
              className={`flex items-center gap-2 px-2.5 py-1 rounded border ${style.bg} ${style.border}`}
              title={explanation}
            >
              <span className={`font-bold text-xs ${style.text}`}>
                {event}
              </span>
              <span className="text-[10px] text-slate-700 dark:text-slate-300">
                {loc.name}
              </span>
              <span className={`text-[10px] font-mono font-semibold ${carbon > 300 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                {Math.round(carbon)}g
              </span>
              <span className="text-[10px] font-mono text-slate-600 dark:text-slate-400">
                {(rf * 100).toFixed(0)}%
              </span>
            </div>
          );
        })
      ) : (
        <span className="text-[10px] text-slate-500 dark:text-slate-400">
          No active weather events — clear skies across grid
        </span>
      )}
    </div>
  );
}
