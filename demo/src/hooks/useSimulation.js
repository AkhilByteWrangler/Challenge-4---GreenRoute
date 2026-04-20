import { useState, useRef, useCallback, useEffect } from 'react';
import { createInitialState, simulationStep } from '../simulation/engine';

export default function useSimulation() {
  const [simState, setSimState] = useState(createInitialState);
  const [paused, setPaused] = useState(false);
  const [speed, setSpeed] = useState(3);
  const [currentJob, setCurrentJob] = useState(null);
  const [currentDecision, setCurrentDecision] = useState(null);
  const [feedItems, setFeedItems] = useState([]);
  const [packets, setPackets] = useState([]);
  const stateRef = useRef(simState);
  const intervalRef = useRef(null);
  const feedIdRef = useRef(0);

  // Keep ref in sync
  useEffect(() => { stateRef.current = simState; }, [simState]);

  const tick = useCallback(() => {
    const { state, job, decision, carbonSaved, held, released } = simulationStep(stateRef.current);
    setSimState(state);
    setCurrentJob(job);
    setCurrentDecision(held ? { ...decision, policySource: 'hold', reason: `⏸ HELD — carbon too high, waiting for renewable window. ${decision.reason}` } : decision);

    // Add feed item (mark held jobs)
    feedIdRef.current += 1;
    setFeedItems((prev) => {
      const items = [];

      // Show released held jobs first
      if (released) {
        for (const entry of released) {
          feedIdRef.current += 1;
          items.push({
            id: feedIdRef.current, job: entry.job,
            decision: { dest: entry.job.origin }, // placeholder
            carbonSaved: 0, held: false, released: true,
            releaseReason: entry.releaseReason,
          });
        }
      }

      // Current job
      items.push({ id: feedIdRef.current, job, decision, carbonSaved, held });

      const next = [...items, ...prev];
      return next.slice(0, 40);
    });

    // Spawn routing packet (arrow across map) — not for held jobs
    if (!held && decision.dest !== job.origin) {
      setPackets((prev) => [
        ...prev,
        {
          id: Date.now() + Math.random(),
          origin: job.origin,
          dest: decision.dest,
          t: 0,
          speed: 0.012 + Math.random() * 0.008,
          colour: job.type === 'FLEXIBLE' ? '#00bcd4' : '#ffb300',
        },
      ]);
    }
  }, []);

  // Manage interval
  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (!paused) {
      const ms = Math.max(600, 3000 - speed * 300);
      intervalRef.current = setInterval(tick, ms);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [paused, speed, tick]);

  const togglePause = useCallback(() => setPaused((p) => !p), []);

  const reset = useCallback(() => {
    setSimState(createInitialState());
    setFeedItems([]);
    setPackets([]);
    setCurrentJob(null);
    setCurrentDecision(null);
  }, []);

  // Advance packets each frame (called from MapCanvas)
  const advancePackets = useCallback(() => {
    setPackets((prev) =>
      prev
        .map((p) => ({ ...p, t: p.t + p.speed }))
        .filter((p) => p.t <= 1)
    );
  }, []);

  return {
    simState,
    paused,
    speed,
    setSpeed,
    togglePause,
    reset,
    currentJob,
    currentDecision,
    feedItems,
    packets,
    advancePackets,
  };
}
