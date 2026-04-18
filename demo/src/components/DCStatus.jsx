import { LOCATIONS, LOC_IDS } from '../simulation/locations';
import { getSnapshot } from '../simulation/engine';

export default function DCStatus({ simState }) {
  return (
    <div className="px-5 py-4 border-b border-border">
      <h3 className="text-[10px] uppercase tracking-[1.5px] text-slate-500 mb-3 font-medium">
        Data Centre Status
      </h3>
      <div className="space-y-2">
        {LOC_IDS.map((locId) => {
          const loc = LOCATIONS[locId];
          const snap = getSnapshot();
          const s = snap?.[locId];
          if (!s) return null;
          const { rf, carbon, util, weatherEvent } = s;
          const barCol = util > 0.85 ? '#ff5252' : rf > 0.5 ? '#00e676' : '#ffb300';

          return (
            <div key={locId} className="flex items-center gap-2 text-xs">
              <span className="font-semibold w-7 shrink-0" style={{ color: loc.colour }}>
                {locId}
              </span>
              {weatherEvent && (
                <span className="text-[9px] px-1 py-0.5 rounded bg-slate-800 text-white shrink-0 animate-pulse">
                  {weatherEvent}
                </span>
              )}
              <div className="flex-1 h-1.5 bg-bg-primary rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${(util * 100).toFixed(0)}%`, background: barCol }}
                />
              </div>
              <span className="font-mono text-[10px] text-slate-500 w-8 text-right">
                {(util * 100).toFixed(0)}%
              </span>
              <span
                className="font-mono text-[10px] w-12 text-right"
                style={{ color: carbon < 250 ? '#00e676' : '#ff5252' }}
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
