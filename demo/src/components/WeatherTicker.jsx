import { LOCATIONS, LOC_IDS } from '../simulation/locations';
import { getSnapshot } from '../simulation/engine';

const EVENT_COLORS = {
  'Cold': { bg: 'bg-blue-900/80', border: 'border-blue-400', text: 'text-blue-200' },
  'Storm': { bg: 'bg-purple-900/80', border: 'border-purple-400', text: 'text-purple-200' },
  'Heat': { bg: 'bg-orange-900/80', border: 'border-orange-400', text: 'text-orange-200' },
  'Solar': { bg: 'bg-yellow-900/80', border: 'border-yellow-400', text: 'text-yellow-200' },
};

function getEventStyle(label) {
  for (const [key, style] of Object.entries(EVENT_COLORS)) {
    if (label.includes(key)) return style;
  }
  return { bg: 'bg-slate-800', border: 'border-slate-500', text: 'text-slate-200' };
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
  if (!snap) return null;

  const activeEvents = [];
  for (const locId of LOC_IDS) {
    const s = snap[locId];
    if (s?.weatherEvent) {
      activeEvents.push({ locId, event: s.weatherEvent, carbon: s.carbon, rf: s.rf });
    }
  }

  if (activeEvents.length === 0) return null;

  return (
    <div className="flex items-center gap-2 px-4 py-1.5 bg-bg-primary/90 border-b border-border overflow-x-auto">
      <span className="text-[10px] uppercase tracking-wider text-slate-500 shrink-0 font-semibold">
        ⚠ WEATHER
      </span>
      {activeEvents.map(({ locId, event, carbon, rf }) => {
        const style = getEventStyle(event);
        const loc = LOCATIONS[locId];
        const explanation = getExplanation(event);
        return (
          <div
            key={locId}
            className={`flex items-center gap-2 px-2.5 py-1 rounded-md border ${style.bg} ${style.border} animate-pulse`}
            title={explanation}
          >
            <span className={`font-bold text-xs ${style.text}`}>
              {event}
            </span>
            <span className="text-[10px] text-slate-300">
              {loc.name}
            </span>
            <span className={`text-[10px] font-mono ${carbon > 300 ? 'text-red-400' : 'text-green-400'}`}>
              {Math.round(carbon)}g
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              ♻{(rf * 100).toFixed(0)}%
            </span>
          </div>
        );
      })}
    </div>
  );
}
