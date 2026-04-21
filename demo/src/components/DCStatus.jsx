import { LOCATIONS, LOC_IDS } from '../simulation/locations';
import { getSnapshot } from '../simulation/engine';

export default function DCStatus({ simState }) {
  return (
    <div className="px-5 py-4 border-b border-slate-200 dark:border-white/[0.1]">
      <h3 className="text-[10px] uppercase tracking-[1.5px] text-slate-600 dark:text-slate-500 mb-3 font-semibold">
        Data Centre Status
      </h3>
      <div className="space-y-2">
        {LOC_IDS.map((locId) => {
          const loc = LOCATIONS[locId];
          const snap = getSnapshot();
          const s = snap?.[locId];
          if (!s) return null;
          const { rf, carbon, util, weatherEvent } = s;
          const barCol = util > 0.85 ? '#ef4444' : rf > 0.5 ? '#10b981' : '#f59e0b';

          return (
            <div key={locId} className="flex items-center gap-2 text-xs">
              <span className="font-semibold w-7 shrink-0" style={{ color: loc.colour, opacity: 0.85 }}>
                {locId}
              </span>
              {weatherEvent && (
                <span className="text-[9px] px-1 py-0.5 rounded bg-slate-300 dark:bg-slate-700 text-slate-900 dark:text-white shrink-0">
                  {weatherEvent}
                </span>
              )}
              <div className="flex-1 h-1.5 bg-slate-200 dark:bg-white/[0.05] rounded overflow-hidden">
                <div
                  className="h-full transition-all duration-500 rounded"
                  style={{ width: `${(util * 100).toFixed(0)}%`, background: barCol, opacity: 0.85 }}
                  role="progressbar"
                  aria-valuenow={util * 100}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`${locId} utilization`}
                />
              </div>
              <span className="font-mono text-[10px] text-slate-600 dark:text-slate-500 w-8 text-right">
                {(util * 100).toFixed(0)}%
              </span>
              <span
                className="font-mono text-[10px] w-12 text-right font-semibold"
                style={{ color: carbon < 250 ? '#10b981' : '#ef4444' }}
              >
                {Math.round(carbon)}g
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
