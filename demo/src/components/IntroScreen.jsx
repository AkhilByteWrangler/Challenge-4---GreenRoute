import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function IntroScreen({ onEnter }) {
  const [exiting, setExiting] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);
  }, []);

  const handleEnter = () => {
    setExiting(true);
    setTimeout(onEnter, 800);
  };

  const duration = prefersReducedMotion ? 0.1 : 2;
  const delay = prefersReducedMotion ? 0 : 2.5;

  return (
    <AnimatePresence>
      {!exiting && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-white dark:bg-slate-950"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8 }}
        >
          <div className="max-w-2xl text-center px-8">
            <motion.p
              className="text-xl md:text-2xl font-light leading-relaxed text-slate-700 dark:text-slate-300 italic"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration }}
            >
              &ldquo;Every year, data centres burn fossil fuels to run jobs that
              could have run on sunshine &mdash; if only someone had decided to
              move them.&rdquo;
            </motion.p>

            <motion.div
              className="mt-12"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1.5, delay }}
            >
              <button
                onClick={handleEnter}
                aria-label="Enter GreenRoute demo"
                className="px-10 py-3 border-2 border-accent-green text-accent-green rounded
                           text-base font-medium tracking-wide
                           hover:bg-accent-green hover:text-white
                           active:scale-95
                           transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent-green dark:focus:ring-offset-slate-950"
              >
                Enter GreenRoute
              </button>
            </motion.div>

            <motion.p
              className="mt-6 text-xs text-slate-600 dark:text-slate-500 tracking-widest uppercase"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: prefersReducedMotion ? 0 : 3.5, duration: 1 }}
            >
              Press any key to continue
            </motion.p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
