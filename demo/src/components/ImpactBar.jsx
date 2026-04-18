import { Leaf, DollarSign, ShieldCheck, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

export default function ImpactBar({ simState }) {
  const { totalCarbonSaved, totalCostSaved, totalJobsProcessed, totalSLAViolations, totalRenewableSum } = simState;
  const sla = totalJobsProcessed > 0
    ? ((1 - totalSLAViolations / totalJobsProcessed) * 100).toFixed(0)
    : '100';
  const renew = totalJobsProcessed > 0
    ? ((totalRenewableSum / totalJobsProcessed) * 100).toFixed(0)
    : '0';

  return (
    <div className="grid grid-cols-4 gap-3 px-5 py-3 bg-bg-secondary border-t border-border">
      <ImpactItem
        icon={<Leaf className="w-4 h-4" />}
        value={Math.round(totalCarbonSaved).toLocaleString()}
        unit="gCO₂ saved"
        color="text-accent-green"
      />
      <ImpactItem
        icon={<DollarSign className="w-4 h-4" />}
        value={`$${totalCostSaved.toFixed(2)}`}
        unit="cost saved"
        color="text-accent-amber"
      />
      <ImpactItem
        icon={<ShieldCheck className="w-4 h-4" />}
        value={`${sla}%`}
        unit="SLA compliance"
        color="text-accent-cyan"
      />
      <ImpactItem
        icon={<Zap className="w-4 h-4" />}
        value={`${renew}%`}
        unit="renewable used"
        color="text-accent-blue"
      />
    </div>
  );
}

function ImpactItem({ icon, value, unit, color }) {
  return (
    <div className="text-center">
      <div className={`flex items-center justify-center gap-1.5 ${color}`}>
        {icon}
        <motion.span
          key={value}
          initial={{ scale: 1.1 }}
          animate={{ scale: 1 }}
          className="text-xl font-bold font-mono"
        >
          {value}
        </motion.span>
      </div>
      <div className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">{unit}</div>
    </div>
  );
}
