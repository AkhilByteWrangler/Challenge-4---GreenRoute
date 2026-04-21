import { Leaf, ShieldCheck, Zap, Activity } from 'lucide-react';
import { motion } from 'framer-motion';

export default function ImpactBar({ simState }) {
  const { totalCarbonSaved, totalJobsProcessed, totalSLAViolations, totalRenewableSum } = simState;
  const sla = totalJobsProcessed > 0
    ? ((1 - totalSLAViolations / totalJobsProcessed) * 100).toFixed(0)
    : '100';
  const renew = totalJobsProcessed > 0
    ? ((totalRenewableSum / totalJobsProcessed) * 100).toFixed(0)
    : '0';

  return (
    <div className="grid grid-cols-4 gap-2 px-4 py-2.5 bg-gradient-to-r from-[#0a0e1a] via-[#0d1220] to-[#0a0e1a] border-t border-slate-200 dark:border-white/[0.1]">
      <ImpactItem
        icon={<Leaf className="w-3.5 h-3.5" />}
        value={Math.round(totalCarbonSaved).toLocaleString()}
        unit="g CO₂ saved"
        gradient="from-green-400 to-emerald-500"
        bg="bg-green-500/8"
      />
      <ImpactItem
        icon={<ShieldCheck className="w-3.5 h-3.5" />}
        value={`${sla}%`}
        unit="SLA compliance"
        gradient="from-cyan-400 to-blue-500"
        bg="bg-cyan-500/8"
      />
      <ImpactItem
        icon={<Zap className="w-3.5 h-3.5" />}
        value={`${renew}%`}
        unit="renewable used"
        gradient="from-amber-400 to-orange-500"
        bg="bg-amber-500/8"
      />
      <ImpactItem
        icon={<Activity className="w-3.5 h-3.5" />}
        value={totalJobsProcessed.toLocaleString()}
        unit="jobs routed"
        gradient="from-violet-400 to-purple-500"
        bg="bg-violet-500/8"
      />
    </div>
  );
}

function ImpactItem({ icon, value, unit, gradient, bg }) {
  return (
    <div className={`flex items-center gap-3 px-3 py-2 rounded-lg ${bg} border border-white/[0.04]`}>
      <div className={`bg-gradient-to-br ${gradient} bg-clip-text text-transparent`}>
        {icon}
      </div>
      <div>
        <motion.div
          key={value}
          initial={{ scale: 1.05 }}
          animate={{ scale: 1 }}
          className={`text-lg font-bold font-mono bg-gradient-to-r ${gradient} bg-clip-text text-transparent leading-none`}
        >
          {value}
        </motion.div>
        <div className="text-[9px] text-slate-500 uppercase tracking-wider mt-0.5">{unit}</div>
      </div>
    </div>
  );
}
