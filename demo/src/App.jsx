import { useState, useEffect, useCallback } from 'react';
import IntroScreen from './components/IntroScreen';
import Header from './components/Header';
import MapCanvas from './components/MapCanvas';
import JobPanel from './components/JobPanel';
import DecisionPanel from './components/DecisionPanel';
import RoutingFeed from './components/RoutingFeed';
import DCStatus from './components/DCStatus';
import QueuePanel from './components/QueuePanel';
import LearningPanel from './components/LearningPanel';
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
  const [selectedAgent, setSelectedAgent] = useState('PPO');
  const [agents, setAgents] = useState(['PPO', 'Q-Learning', 'DQN', 'Random', 'Greedy']);
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    return saved !== null ? JSON.parse(saved) : window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  const sim = useSimulation();

  // Load trained policy on mount
  useEffect(() => {
    loadTrainedPolicy().then((data) => {
      setPolicyLoaded(isPolicyLoaded());
      if (data?.metadata?.agents_trained) {
        setAgents(data.metadata.agents_trained);
        setSelectedAgent(data.metadata.agents_trained[0] || 'PPO');
      }
    });
  }, []);

  // Persist dark mode preference and apply to document
  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(darkMode));
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

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
    <div className="flex flex-col h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100">
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
        darkMode={darkMode}
        setDarkMode={setDarkMode}
        agents={agents}
        selectedAgent={selectedAgent}
        onAgentChange={setSelectedAgent}
      />

      {/* Weather event alerts */}
      <WeatherTicker />

      {/* Main area: immersive map + side panel */}
      <div className="flex flex-1 overflow-hidden relative flex-col lg:flex-row">
        {/* Full-screen map */}
        <div className="flex-1 relative min-h-0">
          <MapCanvas
            simState={sim.simState}
            packets={sim.packets}
            advancePackets={sim.advancePackets}
            paused={sim.paused}
            darkMode={darkMode}
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

        {/* Side panel — responsive, scrollable */}
        <div className="w-full lg:w-96 flex flex-col border-t lg:border-t-0 lg:border-l border-slate-200 dark:border-white/[0.1] bg-white dark:bg-slate-900/50 overflow-y-auto max-h-64 lg:max-h-none">
          <LearningPanel simState={sim.simState} />
          <QueuePanel simState={sim.simState} />
          <JobPanel job={sim.currentJob} />
          <DecisionPanel decision={sim.currentDecision} job={sim.currentJob} />
          <RoutingFeed feedItems={sim.feedItems} />
          <DCStatus simState={sim.simState} />
        </div>
      </div>

      {/* Live baseline comparison */}
      <BaselineComparison simState={sim.simState} darkMode={darkMode} />

      {/* 24-hour timeline strip */}
      <Timeline simState={sim.simState} />
    </div>
  );
}
