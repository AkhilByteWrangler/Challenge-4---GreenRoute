import { getSnapshot } from '../simulation/engine';
import { LOC_IDS } from '../simulation/locations';

export default function Timeline({ simState }) {
  const hour = simState.utcHour;
  const snap = getSnapshot();

  // Compute average renewable fraction across all DCs
  let avgRF = 0;
  if (snap) {
    for (const id of LOC_IDS) avgRF += snap[id]?.rf || 0;
    avgRF /= LOC_IDS.length;
  }

  const hours = [];
  for (let h = 0; h < 24; h++) hours.push(h);

  const currentH = Math.floor(hour);

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-bg-secondary/80 backdrop-blur border-t border-border">
      {/* Time labels */}
      <div className="flex items-center gap-1 shrink-0">
        <span className="text-[10px] text-slate-500 font-mono w-10">00:00</span>
      </div>

      {/* Hour blocks */}
      <div className="flex-1 flex items-center gap-[2px] h-6">
        {hours.map((h) => {
          const isCurrent = h === currentH;
          const isPast = h < currentH;
          // Sun position determines brightness of each hour block
          const sunDist = Math.abs((12 - h) * 15 - (-96));
          const daylight = Math.max(0, Math.min(1, 1 - sunDist / 90));

          let bg = 'bg-slate-800/40';
          if (isPast || isCurrent) {
            if (daylight > 0.6) bg = 'bg-amber-500/30';
            else if (daylight > 0.3) bg = 'bg-amber-800/20';
            else bg = 'bg-indigo-900/40';
          }

          return (
            <div
              key={h}
              className={`relative flex-1 h-full rounded-sm transition-all duration-300 ${bg} ${
                isCurrent ? 'ring-1 ring-accent-green' : ''
              }`}
              title={`${String(h).padStart(2, '0')}:00 UTC`}
            >
              {isCurrent && (
                <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
              )}
              {/* Sun indicator */}
              {daylight > 0.5 && (
                <div
                  className="absolute bottom-0 left-0 right-0 rounded-sm"
                  style={{
                    height: `${daylight * 100}%`,
                    background: isPast || isCurrent
                      ? `rgba(255,179,0,${daylight * 0.3})`
                      : `rgba(255,179,0,${daylight * 0.08})`,
                  }}
                />
              )}
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-1 shrink-0">
        <span className="text-[10px] text-slate-500 font-mono w-10 text-right">23:59</span>
      </div>

      {/* Current time + Day */}
      <div className="flex items-center gap-3 pl-3 border-l border-border shrink-0">
        <div className="text-center">
          <div className="text-lg font-bold font-mono text-white leading-none">
            {String(Math.floor(hour)).padStart(2, '0')}:{String(Math.floor((hour % 1) * 60)).padStart(2, '0')}
          </div>
          <div className="text-[9px] text-slate-500 mt-0.5">UTC — Day {simState.day}</div>
        </div>
        <div className="text-center">
          <div className="text-sm font-bold font-mono leading-none" style={{ color: avgRF > 0.5 ? '#00e676' : '#ffb300' }}>
            {(avgRF * 100).toFixed(0)}%
          </div>
          <div className="text-[9px] text-slate-500 mt-0.5">Avg Renew</div>
        </div>
      </div>
    </div>
  );
}
