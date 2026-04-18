import { useState, useEffect, useCallback } from 'react';
import IntroScreen from './components/IntroScreen';
import Header from './components/Header';
import MapCanvas from './components/MapCanvas';
import JobPanel from './components/JobPanel';
import DecisionPanel from './components/DecisionPanel';
import RoutingFeed from './components/RoutingFeed';
import DCStatus from './components/DCStatus';
import LearningPanel from './components/LearningPanel';
import ImpactBar from './components/ImpactBar';
import BaselineComparison from './components/BaselineComparison';
import Timeline from './components/Timeline';
import TrainingInfo from './components/TrainingInfo';
import WeatherTicker from './components/WeatherTicker';
import useSimulation from './hooks/useSimulation';
import { loadTrainedPolicy, isPolicyLoaded, getTrainingMeta, getFinalMetrics, getTrainingCurves } from './simulation/engine';

export default function App() {
  const [showIntro, setShowIntro] = useState(true);
  const [policyLoaded, setPolicyLoaded] = useState(false);
  const [showTraining, setShowTraining] = useState(false);
  const sim = useSimulation();

  // Load trained policy on mount
  useEffect(() => {
    loadTrainedPolicy().then(() => setPolicyLoaded(isPolicyLoaded()));
  }, []);

  // Skip intro on keypress
  const handleKeyDown = useCallback(() => {
    if (showIntro) setShowIntro(false);
  }, [showIntro]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  if (showIntro) {
    return <IntroScreen onEnter={() => setShowIntro(false)} />;
  }

  return (
    <div className="flex flex-col h-screen bg-bg-primary">
      {/* Compact header */}
      <Header
        simState={sim.simState}
        paused={sim.paused}
        speed={sim.speed}
        setSpeed={sim.setSpeed}
        togglePause={sim.togglePause}
        reset={sim.reset}
        policyLoaded={policyLoaded}
        onShowTraining={() => setShowTraining((v) => !v)}
      />

      {/* Weather event alerts */}
      <WeatherTicker />

      {/* Main area: immersive map + side panel */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Full-screen map */}
        <div className="flex-1 relative">
          <MapCanvas
            simState={sim.simState}
            packets={sim.packets}
            advancePackets={sim.advancePackets}
          />

          {/* Training info overlay (floats on map) */}
          {showTraining && (
            <TrainingInfo
              meta={getTrainingMeta()}
              metrics={getFinalMetrics()}
              curves={getTrainingCurves()}
              onClose={() => setShowTraining(false)}
            />
          )}
        </div>

        {/* Side panel — compact, scrollable */}
        <div className="w-[340px] flex flex-col border-l border-border bg-bg-secondary/95 backdrop-blur overflow-y-auto">
          <LearningPanel simState={sim.simState} />
          <JobPanel job={sim.currentJob} />
          <DecisionPanel decision={sim.currentDecision} job={sim.currentJob} />
          <RoutingFeed feedItems={sim.feedItems} />
          <DCStatus simState={sim.simState} />
        </div>
      </div>

      {/* Impact metrics */}
      <ImpactBar simState={sim.simState} />

      {/* Live baseline comparison */}
      <BaselineComparison simState={sim.simState} />

      {/* 24-hour timeline strip */}
      <Timeline simState={sim.simState} />
    </div>
  );
}
