import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function IntroScreen({ onEnter }) {
  const [exiting, setExiting] = useState(false);

  const handleEnter = () => {
    setExiting(true);
    setTimeout(onEnter, 800);
  };

  return (
    <AnimatePresence>
      {!exiting && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-bg-primary"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8 }}
        >
          <div className="max-w-2xl text-center px-8">
            <motion.p
              className="text-xl md:text-2xl font-light leading-relaxed text-slate-400 italic"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 2 }}
            >
              &ldquo;Every year, data centres burn fossil fuels to run jobs that
              could have run on sunshine &mdash; if only someone had decided to
              move them.&rdquo;
            </motion.p>

            <motion.div
              className="mt-12"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1.5, delay: 2.5 }}
            >
              <button
                onClick={handleEnter}
                className="px-10 py-3 border border-accent-green text-accent-green rounded-md
                           text-base font-medium tracking-wide
                           hover:bg-accent-green hover:text-bg-primary
                           transition-all duration-300 cursor-pointer"
              >
                Enter GreenRoute
              </button>
            </motion.div>

            <motion.p
              className="mt-6 text-xs text-slate-600 tracking-widest uppercase"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 3.5, duration: 1 }}
            >
              Press any key to continue
            </motion.p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
