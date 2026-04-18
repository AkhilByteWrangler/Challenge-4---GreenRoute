import { useState, useRef, useCallback, useEffect } from 'react';
import { createInitialState, simulationStep } from '../simulation/engine';

export default function useSimulation() {
  const [simState, setSimState] = useState(createInitialState);
  const [paused, setPaused] = useState(false);
  const [speed, setSpeed] = useState(4);
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
    const { state, job, decision, carbonSaved } = simulationStep(stateRef.current);
    setSimState(state);
    setCurrentJob(job);
    setCurrentDecision(decision);

    // Add feed item
    feedIdRef.current += 1;
    setFeedItems((prev) => {
      const next = [{ id: feedIdRef.current, job, decision, carbonSaved }, ...prev];
      return next.slice(0, 40);
    });

    // Spawn routing packet (arrow across map)
    if (decision.dest !== job.origin) {
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
      const ms = Math.max(200, 2500 - speed * 230);
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
