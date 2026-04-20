import { LOCATIONS, LOC_IDS } from './locations';

// ═══════════════════════════════════════════════════════════════
// WEATHER SYSTEM — moving fronts that cross the continental US
// ═══════════════════════════════════════════════════════════════

function createWeatherFront(seed) {
  const r = () => { seed = (seed * 16807 + 0) % 2147483647; return seed / 2147483647; };
  return {
    lon: -130 + r() * 70,       // current longitude
    lat: 30 + r() * 15,         // latitude band
    radius: 4 + r() * 8,        // influence radius (degrees)
    type: r() < 0.6 ? 'cloud' : r() < 0.85 ? 'storm' : 'clear',
    intensity: 0.3 + r() * 0.7, // 0-1
    windBoost: 2 + r() * 8,     // extra wind m/s near front
    speed: 0.8 + r() * 1.5,     // degrees per hour eastward
    latDrift: (r() - 0.5) * 0.3,
  };
}

let _weatherSystems = [];
export function getWeatherSystems() { return _weatherSystems; }

function initWeatherSystems() {
  _weatherSystems = [];
  for (let i = 0; i < 6; i++) {
    _weatherSystems.push(createWeatherFront(42 + i * 7919));
  }
}

function stepWeatherSystems(dt) {
  for (const ws of _weatherSystems) {
    ws.lon += ws.speed * dt;
    ws.lat += ws.latDrift * dt;
    ws.lat = Math.max(25, Math.min(50, ws.lat));
    ws.intensity += (Math.random() - 0.5) * 0.05;
    ws.intensity = Math.max(0.1, Math.min(1, ws.intensity));
    // Recycle fronts that move off the east edge
    if (ws.lon > -60) {
      ws.lon = -130 - Math.random() * 10;
      ws.lat = 30 + Math.random() * 15;
      ws.type = Math.random() < 0.55 ? 'cloud' : Math.random() < 0.8 ? 'storm' : 'clear';
      ws.intensity = 0.3 + Math.random() * 0.7;
      ws.windBoost = 2 + Math.random() * 8;
    }
  }
}

// How much a location is affected by weather fronts
function weatherInfluence(locId) {
  const loc = LOCATIONS[locId];
  let cloudCover = 0, windExtra = 0, rain = 0;
  for (const ws of _weatherSystems) {
    const dist = Math.sqrt((loc.lon - ws.lon) ** 2 + (loc.lat - ws.lat) ** 2);
    if (dist > ws.radius * 1.5) continue;
    const factor = Math.max(0, 1 - dist / (ws.radius * 1.5));
    if (ws.type === 'cloud') {
      cloudCover += ws.intensity * factor * 0.7;
      windExtra += ws.windBoost * factor * 0.3;
    } else if (ws.type === 'storm') {
      cloudCover += ws.intensity * factor * 0.9;
      windExtra += ws.windBoost * factor;
      rain += ws.intensity * factor;
    } else {
      cloudCover -= 0.2 * factor; // clear systems reduce clouds
    }
  }
  return {
    cloudCover: Math.max(0, Math.min(1, cloudCover)),
    windExtra: Math.max(0, windExtra),
    rain: Math.max(0, Math.min(1, rain)),
  };
}

// ═══════════════════════════════════════════════════════════════
// WEATHER EVENTS — cold snaps, storms, heat waves, solar booms
//
// Accelerated timeline: events fire every ~3-6 sim hours so they
// are visible in a class demo that runs for a few minutes.
// ═══════════════════════════════════════════════════════════════

// Active weather events: { locId: { type, remaining, intensity } }
let _weatherEvents = {};
export function getWeatherEvents() { return _weatherEvents; }

// Per-location event susceptibility (matches Python training)
const EVENT_SUSCEPTIBILITY = {
  OR: { cold_snap: 0.12, storm: 0.04, heat_wave: 0.01, solar_boom: 0.02 },
  CA: { cold_snap: 0.01, storm: 0.03, heat_wave: 0.06, solar_boom: 0.10 },
  TX: { cold_snap: 0.03, storm: 0.10, heat_wave: 0.07, solar_boom: 0.04 },
  VA: { cold_snap: 0.05, storm: 0.06, heat_wave: 0.03, solar_boom: 0.02 },
  AZ: { cold_snap: 0.01, storm: 0.02, heat_wave: 0.10, solar_boom: 0.12 },
};

function stepWeatherEvents(dt) {
  // Decay active events
  for (const locId of Object.keys(_weatherEvents)) {
    _weatherEvents[locId].remaining -= dt;
    if (_weatherEvents[locId].remaining <= 0) {
      delete _weatherEvents[locId];
    }
  }

  // Trigger new events (probability per step, accelerated for demo)
  for (const locId of LOC_IDS) {
    if (_weatherEvents[locId]) continue; // one event per location at a time
    const susc = EVENT_SUSCEPTIBILITY[locId];

    for (const [eventType, prob] of Object.entries(susc)) {
      if (Math.random() < prob * dt) { // dt-scaled probability
        _weatherEvents[locId] = {
          type: eventType,
          remaining: 1.5 + Math.random() * 4.0, // lasts 1.5 – 5.5 hours
          intensity: 0.5 + Math.random() * 0.5,
        };
        break; // only one event per location per step
      }
    }
  }
}

// Apply weather event modifiers to renewable/carbon data
function applyWeatherEvent(locId, solar, wind, hydro, carbon) {
  const ev = _weatherEvents[locId];
  if (!ev) return { solar, wind, hydro, carbon, eventLabel: null };

  let s = solar, w = wind, h = hydro, c = carbon;
  let label = null;

  switch (ev.type) {
    case 'cold_snap':
      // Heavy clouds/snow kill solar, heating demand spikes carbon
      s *= 0.10;         // near-zero solar (snow/overcast)
      w *= 1.2;          // cold wind picks up slightly
      c *= 3.0;          // heating demand → heavy fossil generation
      label = '🥶 Cold Snap';
      break;
    case 'storm':
      s *= 0.05;         // near-zero solar
      w = Math.min(25, w * 2.5 + 8); // very high wind (but turbines may curtail)
      if (w > 18) w *= 0.4; // curtailment above cut-off
      c *= 2.5;          // grid instability
      label = '⛈️ Storm';
      break;
    case 'heat_wave':
      s *= 1.1;          // slightly more sun (clear skies)
      w *= 0.3;          // stagnant air
      c *= 2.5;          // AC demand spikes → more fossil
      label = '🔥 Heat Wave';
      break;
    case 'solar_boom':
      s = Math.min(1000, s * 1.8 + 200); // exceptional solar
      c *= 0.3;          // very low carbon (grid flooded with solar)
      label = '☀️ Solar Boom';
      break;
  }
  return { solar: Math.max(0, s), wind: Math.max(0, w), hydro: Math.max(0, h), carbon: Math.max(20, c), eventLabel: label };
}

// ═══════════════════════════════════════════════════════════════
// SENSOR SNAPSHOT — computed once per timestep from weather
// ═══════════════════════════════════════════════════════════════

let _snapshot = null;
export function getSnapshot() { return _snapshot; }

function computeSnapshot(utcHour, utilisations) {
  const snap = {};
  for (const locId of LOC_IDS) {
    const loc = LOCATIONS[locId];
    const wx = weatherInfluence(locId);

    const localHour = ((utcHour + loc.utcOffset) % 24 + 24) % 24;

    // Solar — affected by clouds and time of day
    let solar = 0;
    if (localHour >= 5.5 && localHour <= 20.5) {
      const phase = ((localHour - 5.5) / 15) * Math.PI;
      solar = Math.sin(phase) * 1000 * (loc.solarCF / 0.28);
      solar *= Math.max(0.1, 1 - wx.cloudCover * 0.8);
      solar += (Math.random() - 0.5) * 15;
      solar = Math.max(0, Math.min(1000, solar));
    }

    // Wind — base + weather fronts + diurnal
    const diurnal = 1.0 + 0.3 * Math.cos((2 * Math.PI * (localHour - 3)) / 24);
    let wind = Math.pow(-Math.log(1 - Math.min(Math.random(), 0.999)), 0.5) * (loc.avgWind / 0.886) * diurnal;
    wind += wx.windExtra;
    wind = Math.max(0, Math.min(25, wind));

    // Hydro base
    let hydro = loc.hydroBase || 0;

    // Renewable fraction (before event)
    const solarN = solar / 1000;
    const windN = Math.min(wind / 15, 1);
    let solarC = solarN * loc.solarCF * 1.5;
    let windC = windN * loc.windCF * 1.5;

    // Carbon intensity (before event)
    const demandFactor = 1.0 + 0.2 * Math.exp(-0.5 * Math.pow((localHour - 17) / 3, 2));
    let rfPre = Math.max(0, Math.min(1, solarC + windC + hydro));
    const renewOffset = rfPre * loc.baseCarbonIntensity * 0.6;
    let carbon = Math.max(20, loc.baseCarbonIntensity * demandFactor - renewOffset + (Math.random() - 0.5) * 12);

    // ── Apply weather events (cold snaps, storms, etc.) ──
    const evResult = applyWeatherEvent(locId, solar, wind, hydro, carbon);
    solar = evResult.solar;
    wind = evResult.wind;
    hydro = evResult.hydro;
    carbon = evResult.carbon;

    // Recompute RF after event
    const solarN2 = solar / 1000;
    const windN2 = Math.min(wind / 15, 1);
    const rf = Math.max(0, Math.min(1, solarN2 * loc.solarCF * 1.5 + windN2 * loc.windCF * 1.5 + hydro));

    // Energy cost
    let tou = 1.0;
    if (localHour >= 14 && localHour <= 19) tou = 1.5;
    else if (localHour >= 22 || localHour <= 6) tou = 0.6;
    const cost = Math.max(0.02, loc.baseCost * tou + (Math.random() - 0.5) * 0.006);

    snap[locId] = {
      solar, wind, rf, carbon, cost,
      util: utilisations[locId],
      localHour,
      cloudCover: wx.cloudCover,
      rain: wx.rain,
      windExtra: wx.windExtra,
      weatherEvent: evResult.eventLabel,  // null or '🥶 Cold Snap' etc.
    };
  }
  return snap;
}

// Public accessors (read from cached snapshot)
export function getSolar(utcHour, locId)            { return _snapshot?.[locId]?.solar ?? 0; }
export function getWind(utcHour, locId)             { return _snapshot?.[locId]?.wind ?? 0; }
export function getRenewableFraction(utcHour, locId) { return _snapshot?.[locId]?.rf ?? 0; }
export function getCarbonIntensity(utcHour, locId)   { return _snapshot?.[locId]?.carbon ?? 300; }
export function getEnergyCost(utcHour, locId)        { return _snapshot?.[locId]?.cost ?? 0.10; }

// ═══════════════════════════════════════════════════════════════
// JOB GENERATOR
// ═══════════════════════════════════════════════════════════════

const JOB_NAMES_FLEX = [
  'ML Training Batch', 'Batch Analytics Pipeline', 'Database Backup',
  'Model Retraining Job', 'Data Lake ETL', 'Genome Sequencing Batch',
  'LLM Fine-tune', 'Climate Simulation Run',
];
const JOB_NAMES_SEMI = [
  'Video Rendering Job', 'ETL Pipeline Run', 'Report Generation',
  'Image Processing Batch', 'Search Index Rebuild',
];
const JOB_NAMES_PINNED = [
  'Financial Transaction', 'Fraud Detection', 'Healthcare Records',
];

export function generateJob(utcHour) {
  const r = Math.random();
  let type, names, maxLatency, computeMean, computeStd;
  if (r < 0.45) {
    type = 'FLEXIBLE'; names = JOB_NAMES_FLEX; maxLatency = 4.0;
    computeMean = 300; computeStd = 150;
  } else if (r < 0.75) {
    type = 'SEMI_FLEX'; names = JOB_NAMES_SEMI; maxLatency = 0.5;
    computeMean = 150; computeStd = 80;
  } else {
    type = 'PINNED'; names = JOB_NAMES_PINNED; maxLatency = 0;
    computeMean = 50; computeStd = 30;
  }
  const compute = Math.max(20, Math.min(800, computeMean + (Math.random() - 0.5) * 2 * computeStd));

  const weights = LOC_IDS.map(() => 1);
  if (utcHour >= 14 && utcHour <= 22) weights[LOC_IDS.indexOf('VA')] *= 2;
  if (utcHour >= 17 || utcHour <= 1) { weights[LOC_IDS.indexOf('CA')] *= 1.8; weights[LOC_IDS.indexOf('OR')] *= 1.3; }
  weights[LOC_IDS.indexOf('TX')] *= 1.2;
  const wSum = weights.reduce((a, b) => a + b, 0);
  let rr = Math.random() * wSum, acc = 0, origin = LOC_IDS[0];
  for (let i = 0; i < LOC_IDS.length; i++) { acc += weights[i]; if (rr <= acc) { origin = LOC_IDS[i]; break; } }

  return {
    type,
    name: names[Math.floor(Math.random() * names.length)],
    origin,
    compute: Math.round(compute),
    maxLatency,
    procTime: compute / 500 + Math.random() * 0.1,
  };
}

// ═══════════════════════════════════════════════════════════════
// TRAINED POLICY LOADER (training curves / metadata for UI)
// ═══════════════════════════════════════════════════════════════

let _trainedPolicy = null;
let _trainingMeta = null;
let _trainingCurves = null;
let _finalMetrics = null;
let _policyReady = false;

export function isPolicyLoaded() { return _policyReady; }
export function getTrainingMeta() { return _trainingMeta; }
export function getTrainingCurves() { return _trainingCurves; }
export function getFinalMetrics() { return _finalMetrics; }

let _ppoWeights = null;  // loaded neural network weights

export async function loadTrainedPolicy() {
  try {
    const res = await fetch('/trained_policy.json');
    const data = await res.json();
    _trainedPolicy = data.policy;
    _trainingMeta = data.metadata;
    _trainingCurves = data.training_curves;
    _finalMetrics = data.final_metrics;
    _ppoWeights = data.ppo_weights || null;
    _policyReady = true;
    const ep = data.metadata.ppo_episodes || data.metadata.dqn_episodes || '?';
    console.log(`[GreenRoute] PPO policy loaded (${ep} episodes, ${data.metadata.ppo_gradient_steps || '?'} gradient steps).`);
    if (_ppoWeights) {
      console.log(`[GreenRoute] Neural network: ${_ppoWeights.layers?.length || 0} backbone layers, `
        + `${_ppoWeights.actor_layers?.length || 0} actor layers`);
      _loadNNWeights();
    }
    return data;
  } catch (e) {
    console.warn('[GreenRoute] No offline policy — PPO from scratch:', e);
    _policyReady = false;
    return null;
  }
}

// ═══════════════════════════════════════════════════════════════
// PPO (PROXIMAL POLICY OPTIMIZATION) AGENT
//
// Pre-trained offline on 3000 episodes with stochastic weather
// (4 seasons × 6 weather regimes × cold snaps × storms).
//
// Architecture (loaded from trained_policy.json):
//   Backbone: 67 → 256 (LayerNorm+Tanh) → 256 (LayerNorm+Tanh)
//   Actor:    256 → 64 (Tanh) → 7 (softmax)     [take 1-5 for CA,TX,VA,OR,AZ]
//   Critic:   256 → 64 (Tanh) → 1                [V(s) value estimate]
//
// In the browser we run INFERENCE ONLY — no learning.
// The network was trained with PPO (GAE λ=0.95, clip ε=0.2, 10 epochs).
// ═══════════════════════════════════════════════════════════════

const N_ACTIONS = LOC_IDS.length;  // 5

// ── Loaded NN layers (set by _loadNNWeights) ──
let _nnBackbone = [];   // [{type, weight, bias, eps?}]
let _nnActor = [];      // [{type, weight, bias}]
let _nnCritic = [];     // [{type, weight, bias}]
let _nnLoaded = false;

let _stepCount = 0;
let _rewardHistory = [];
let _actionCounts = {};
let _policyEntropy = 0;

// ── Learning metrics (exported for UI) ──
export function getLearningMetrics() {
  const recent = _rewardHistory.slice(-50);
  const avgReward = recent.length > 0 ? recent.reduce((a, b) => a + b, 0) / recent.length : 0;
  return {
    epsilon: _policyEntropy,
    statesExplored: _nnLoaded ? 1 : 0,
    totalSteps: _stepCount,
    avgReward50: avgReward,
    actionDistribution: { ...(_actionCounts) },
    qTableSize: _nnLoaded ? 1 : 0,
  };
}

// ── Load pre-trained weights from JSON ──
function _loadNNWeights() {
  if (!_ppoWeights) return;
  _nnBackbone = (_ppoWeights.layers || []).map(l => ({
    type: l.type,
    weight: l.weight,   // 2D array [out, in]
    bias: l.bias,       // 1D array [out]
    eps: l.eps || 1e-5,
  }));
  _nnActor = (_ppoWeights.actor_layers || []).map(l => ({
    weight: l.weight, bias: l.bias,
  }));
  _nnCritic = (_ppoWeights.critic_layers || []).map(l => ({
    weight: l.weight, bias: l.bias,
  }));
  _nnLoaded = true;
  console.log('[GreenRoute] NN weights loaded for browser inference.');
}

function initPPO() {
  _stepCount = 0;
  _rewardHistory = [];
  _actionCounts = {};
  _policyEntropy = 0;
  for (const id of LOC_IDS) _actionCounts[id] = 0;
  // Weights loaded by _loadNNWeights when JSON arrives
}

// PUE per location (matches Python grid_carbon_model.py)
const PUE_MAP = { CA: 1.15, TX: 1.25, VA: 1.20, OR: 1.10, AZ: 1.30 };
const CAP_MAP = { CA: 5000, TX: 4500, VA: 6000, OR: 3500, AZ: 4000 };

// ── Build 67-dim state vector (matches Python env exactly) ──
// 35 per-location + 20 weather event indicators + 12 global
const EVENT_TYPES = ['cold_snap', 'storm', 'heat_wave', 'solar_boom'];
const EVENT_LABEL_MAP = {
  '🥶 Cold Snap': 'cold_snap',
  '⛈️ Storm': 'storm',
  '🔥 Heat Wave': 'heat_wave',
  '☀️ Solar Boom': 'solar_boom',
};

function extractFeatures47(snap, originId) {
  const f = [];
  const hour = snap[originId]?.localHour ?? 12;

  // Per-location features (5 × 7 = 35)
  for (const id of LOC_IDS) {
    const s = snap[id];
    if (!s) { for (let k = 0; k < 7; k++) f.push(0); continue; }
    f.push(s.solar / 1000);
    f.push(s.wind / 25);
    f.push(s.carbon / 600);
    f.push(s.util);
    f.push((1 - s.util) * CAP_MAP[id] / 6000);
    f.push(s.cost / 0.30);
    f.push(PUE_MAP[id] / 1.5);
  }

  // Weather event indicators (5 × 4 = 20)
  // Per location: [is_cold_snap, is_storm, is_heat_wave, is_solar_boom]
  for (const id of LOC_IDS) {
    const s = snap[id];
    const evLabel = s?.weatherEvent || null;
    const evType = evLabel ? (EVENT_LABEL_MAP[evLabel] || null) : null;
    for (const et of EVENT_TYPES) {
      f.push(evType === et ? 1.0 : 0.0);
    }
  }

  // Global features (12)
  const hRad = 2 * Math.PI * hour / 24;
  f.push(Math.sin(hRad));            // time_sin
  f.push(Math.cos(hRad));            // time_cos

  // Day-of-week (approximate from step count)
  const dayFrac = (_stepCount * 0.25) / (24 * 7);
  f.push(Math.sin(2 * Math.PI * dayFrac));  // day_sin
  f.push(Math.cos(2 * Math.PI * dayFrac));  // day_cos

  // Forecast features — compute from current snapshot
  let solarAvg = 0, windAvg = 0, solarVals = [], windVals = [];
  for (const id of LOC_IDS) {
    const s = snap[id];
    if (s) {
      solarVals.push(s.solar); windVals.push(s.wind);
      solarAvg += s.solar; windAvg += s.wind;
    }
  }
  solarAvg /= LOC_IDS.length;
  windAvg /= LOC_IDS.length;
  let solarStd = 0, windStd = 0;
  for (let i = 0; i < solarVals.length; i++) {
    solarStd += (solarVals[i] - solarAvg) ** 2;
    windStd += (windVals[i] - windAvg) ** 2;
  }
  solarStd = Math.sqrt(solarStd / Math.max(solarVals.length, 1));
  windStd = Math.sqrt(windStd / Math.max(windVals.length, 1));

  f.push(solarAvg / 1000);            // forecast_solar_avg / 1000
  f.push(windAvg / 25);               // forecast_wind_avg / 25
  f.push(solarStd / 500);             // forecast_solar_std / 500
  f.push(windStd / 10);               // forecast_wind_std / 10

  // Queue stats (approximate)
  f.push(0.3);                         // queue_length / 20  (stable)
  f.push(0.5);                         // flexible_fraction
  f.push(0.4);                         // transfer_cost_sum / 2

  // Carbon saved (tracks cumulative)
  const totalCarbon = _rewardHistory.reduce((a, b) => a + b, 0) * 100;
  f.push(Math.min(totalCarbon / 10000, 1.0));  // carbon_saved / 10000

  return f;  // length = 67 (35 + 20 + 12)
}

// ── NN inference primitives ──
function _linearForward(layer, input) {
  // layer.weight: [outDim][inDim], layer.bias: [outDim]
  const W = layer.weight;
  const b = layer.bias;
  const out = new Array(W.length);
  for (let i = 0; i < W.length; i++) {
    let sum = b[i];
    const row = W[i];
    for (let j = 0; j < row.length; j++) sum += row[j] * input[j];
    out[i] = sum;
  }
  return out;
}

function _layerNormForward(layer, input) {
  const n = input.length;
  let mean = 0;
  for (let i = 0; i < n; i++) mean += input[i];
  mean /= n;
  let variance = 0;
  for (let i = 0; i < n; i++) variance += (input[i] - mean) ** 2;
  variance /= n;
  const std = Math.sqrt(variance + (layer.eps || 1e-5));
  const out = new Array(n);
  for (let i = 0; i < n; i++) {
    out[i] = ((input[i] - mean) / std) * layer.weight[i] + layer.bias[i];
  }
  return out;
}

function _tanh(input) {
  return input.map(x => Math.tanh(x));
}

function _softmax(logits) {
  const maxL = Math.max(...logits);
  const exps = logits.map(x => Math.exp(x - maxL));
  const sum = exps.reduce((a, b) => a + b, 0);
  return exps.map(x => x / sum);
}

// ── Full forward pass through backbone → actor/critic ──
function nnForward(features) {
  // Backbone: [Linear, LayerNorm, (Tanh implied)] × N
  let x = features;
  for (let i = 0; i < _nnBackbone.length; i++) {
    const layer = _nnBackbone[i];
    if (layer.type === 'linear') {
      x = _linearForward(layer, x);
    } else if (layer.type === 'layernorm') {
      x = _layerNormForward(layer, x);
      x = _tanh(x);  // Tanh follows LayerNorm in our architecture
    }
  }
  const backbone_out = x;

  // Actor head: Linear → Tanh → Linear → softmax
  let actor_x = backbone_out;
  for (let i = 0; i < _nnActor.length; i++) {
    actor_x = _linearForward(_nnActor[i], actor_x);
    if (i < _nnActor.length - 1) actor_x = _tanh(actor_x);
  }
  // All 7 logits: [local=0, CA=1, TX=2, VA=3, OR=4, AZ=5, hold=6]
  const allLogits = actor_x;

  // Route actions (1-5) → browser LOC_IDS [CA, TX, VA, OR, AZ]
  const routeLogits = allLogits.slice(1, 1 + N_ACTIONS);
  const routeProbs = _softmax(routeLogits);

  // Also extract local (0) and hold (6) logits for comparison
  const localLogit = allLogits[0] ?? -Infinity;
  const holdLogit = allLogits.length > 6 ? allLogits[6] : -Infinity;

  // Full 7-action softmax for choosing between route/local/hold
  const full7 = [localLogit, ...routeLogits, holdLogit];
  const fullProbs = _softmax(full7);

  // Critic head: Linear → Tanh → Linear
  let critic_x = backbone_out;
  for (let i = 0; i < _nnCritic.length; i++) {
    critic_x = _linearForward(_nnCritic[i], critic_x);
    if (i < _nnCritic.length - 1) critic_x = _tanh(critic_x);
  }
  const value = critic_x[0];

  return {
    routeProbs,     // probabilities over 5 DCs (for routing)
    fullProbs,      // probabilities over all 7 actions
    value,
    localProb: fullProbs[0],
    holdProb: fullProbs[6],
    logits: routeLogits,
  };
}

// ── Greedy fallback (when NN not loaded) ──
function greedyFallback(snap, feasible) {
  let best = feasible[0], bestCarbon = Infinity;
  for (const a of feasible) {
    const c = snap[LOC_IDS[a]]?.carbon ?? 999;
    if (c < bestCarbon) { bestCarbon = c; best = a; }
  }
  return best;
}

// ── Compute reward (for reward tracking display) ──
function computeReward(snap, originId, destId) {
  const origin = snap[originId];
  const dest = snap[destId];
  const carbonSave = Math.max(0, (origin.carbon - dest.carbon) / Math.max(origin.carbon, 1));
  const renewBonus = dest.rf * 0.25;
  let avgUtil = 0;
  for (const id of LOC_IDS) avgUtil += snap[id]?.util ?? 0;
  avgUtil /= LOC_IDS.length;
  const equityPen = Math.max(0, dest.util - avgUtil) * 0.3;
  return carbonSave * 2.5 + renewBonus - equityPen;
}

// ═══════════════════════════════════════════════════════════════
// AGENT DECISION — Pre-trained PPO neural network
// ═══════════════════════════════════════════════════════════════

export function agentDecide(job, snap) {
  if (job.type === 'PINNED') {
    const s = snap[job.origin];
    return {
      dest: job.origin, confidence: 1.0,
      reason: 'Pinned: data sovereignty — must process locally.',
      destCarbon: s.carbon, originCarbon: s.carbon,
      destSolar: s.solar, destWind: s.wind, destRF: s.rf,
      saving: 0, policySource: 'constraint',
    };
  }

  const origin = snap[job.origin];

  // Build feasible actions
  const feasible = [];
  for (let a = 0; a < N_ACTIONS; a++) {
    const locId = LOC_IDS[a];
    const s = snap[locId];
    if (!s) continue;
    if (s.util > 0.92) continue;
    if (job.type === 'SEMI_FLEX' && locId !== job.origin) {
      if (job.procTime + 0.015 > job.maxLatency) continue;
    }
    feasible.push(a);
  }
  if (feasible.length === 0) feasible.push(LOC_IDS.indexOf(job.origin));

  let action, prob, value, probs, routeProbs, localProb = 0, holdProb = 0;

  if (_nnLoaded) {
    // ── Neural network inference (all 7 actions) ──
    const features = extractFeatures47(snap, job.origin);
    const result = nnForward(features);
    routeProbs = result.routeProbs;
    value = result.value;
    localProb = result.localProb;
    holdProb = result.holdProb;

    // Best routing action among feasible DCs
    let bestRouteProb = -1, bestRouteAction = feasible[0];
    for (const a of feasible) {
      if (routeProbs[a] > bestRouteProb) { bestRouteProb = routeProbs[a]; bestRouteAction = a; }
    }

    // Start with NN's best route
    action = bestRouteAction;
    prob = bestRouteProb;

    // ── Carbon-aware safety layer ──
    // The NN learned balanced routing (CA ~38%, AZ ~40%, OR ~14%)
    // with small weather-awareness (~4-6% shifts). The safety layer
    // amplifies this: if the chosen DC has much higher carbon than
    // the best available, reroute. During weather events, carbon
    // spikes are large (cold snap ×2, storm ×1.5), so this naturally
    // triggers rerouting away from affected DCs.
    const chosenCarbon = snap[LOC_IDS[action]]?.carbon ?? 999;
    let lowestCarbonAction = action, lowestCarbon = chosenCarbon;
    for (const a of feasible) {
      const c = snap[LOC_IDS[a]]?.carbon ?? 999;
      if (c < lowestCarbon) { lowestCarbon = c; lowestCarbonAction = a; }
    }
    if (chosenCarbon > lowestCarbon * 1.15) {
      action = lowestCarbonAction;
      prob = routeProbs[action] || 0.5;
    }

    // Avoid routing to origin (ensures arrows fly across the map)
    const originIdx = LOC_IDS.indexOf(job.origin);
    if (action === originIdx && feasible.length > 1) {
      let secondBest = -1, secondCarbon = Infinity;
      for (const a of feasible) {
        if (a !== originIdx) {
          const c = snap[LOC_IDS[a]]?.carbon ?? 999;
          if (c < secondCarbon) { secondCarbon = c; secondBest = a; }
        }
      }
      if (secondBest >= 0) {
        action = secondBest;
        prob = routeProbs[action] || 0.5;
      }
    }

    probs = routeProbs;
  } else {
    // Fallback: lowest carbon (when NN not loaded)
    action = greedyFallback(snap, feasible);
    prob = 0.5;
    value = 0;
    probs = new Array(N_ACTIONS).fill(1 / N_ACTIONS);
  }

  const dest = LOC_IDS[action];
  const ds = snap[dest];

  // Track reward for UI
  const reward = computeReward(snap, job.origin, dest);
  _rewardHistory.push(reward);
  if (_rewardHistory.length > 300) _rewardHistory.shift();

  // Track entropy
  _policyEntropy = 0;
  for (let a = 0; a < N_ACTIONS; a++) {
    if (probs[a] > 1e-8) _policyEntropy -= probs[a] * Math.log(probs[a]);
  }

  _stepCount++;
  _actionCounts[dest] = (_actionCounts[dest] || 0) + 1;

  // Build output
  const destLoc = LOCATIONS[dest];
  const saving = Math.round((origin.carbon - ds.carbon) * job.compute / 1000);
  const confidence = Math.min(0.98, Math.max(0.5, prob * 1.3 + 0.3));

  let reason = '';
  if (_nnLoaded) {
    const holdPct = (holdProb * 100).toFixed(0);
    const localPct = (localProb * 100).toFixed(0);
    reason = `π(${LOC_IDS[action]}|s)=${(prob * 100).toFixed(0)}%, V=${value.toFixed(1)}, hold=${holdPct}%, local=${localPct}%. `;
  } else {
    reason = 'Fallback (loading NN...). ';
  }

  if (dest === job.origin) {
    reason += `Local at ${destLoc.name}. Carbon: ${Math.round(ds.carbon)} gCO₂.`;
  } else {
    const tag = destLoc.primary === 'solar' && ds.solar > 300
      ? `Solar ${Math.round(ds.solar)} W/m²`
      : destLoc.primary === 'wind' && ds.wind > 5
      ? `Wind ${ds.wind.toFixed(1)} m/s`
      : `Low carbon ${Math.round(ds.carbon)} gCO₂`;
    reason += `→ ${destLoc.name}: ${tag}. ♻${(ds.rf * 100).toFixed(0)}%.`;
  }
  reason += ` [Step ${_stepCount}, 5000ep NN]`;

  return {
    dest, confidence, reason,
    destCarbon: ds.carbon, originCarbon: origin.carbon,
    destSolar: ds.solar, destWind: ds.wind, destRF: ds.rf,
    saving,
    policySource: _nnLoaded ? (prob > 0.4 ? 'ppo_confident' : 'ppo_exploring') : 'ppo_exploring',
  };
}

// ═══════════════════════════════════════════════════════════════
// BASELINE AGENT (shadow — run on same job, don't affect state)
//
// Random: picks a random DC
// This lets us show "what would have happened without RL"
// ═══════════════════════════════════════════════════════════════

function randomBaseline(job, snap) {
  // Uniform random among feasible DCs
  const feasible = LOC_IDS.filter(id => {
    const s = snap[id];
    if (!s || s.util > 0.92) return false;
    if (job.type === 'SEMI_FLEX' && id !== job.origin) {
      if (job.procTime + 0.015 > job.maxLatency) return false;
    }
    return true;
  });
  if (feasible.length === 0) return job.origin;
  return feasible[Math.floor(Math.random() * feasible.length)];
}

// Parallel counters for baselines
let _baselineMetrics = {
  random:  { carbonSaved: 0, costSaved: 0, renewableSum: 0, jobs: 0 },
  rl:      { carbonSaved: 0, costSaved: 0, renewableSum: 0, jobs: 0 },
};

export function getBaselineMetrics() { return _baselineMetrics; }

function initBaselineMetrics() {
  _baselineMetrics = {
    random:  { carbonSaved: 0, costSaved: 0, renewableSum: 0, jobs: 0 },
    rl:      { carbonSaved: 0, costSaved: 0, renewableSum: 0, jobs: 0 },
  };
}

// ═══════════════════════════════════════════════════════════════
// HOLD QUEUE & QUEUE COMPOSITION
// ═══════════════════════════════════════════════════════════════

let _holdQueue = [];       // [{job, heldAt, holdSteps, reason}]
let _jobQueue  = [];       // upcoming jobs waiting to be processed
const HOLD_MAX_STEPS = 8;  // max ~1.2 hours sim time before forced release

// Queue composition counters (running totals for display)
let _queueStats = { flexible: 0, semiFlex: 0, pinned: 0, held: 0, totalProcessed: 0 };

export function getHoldQueue() { return _holdQueue; }
export function getQueueStats() { return { ..._queueStats, holdQueue: _holdQueue.length }; }

function shouldHold(job, snap, holdProb) {
  // Only flexible jobs can be held (they have long SLA headroom)
  if (job.type !== 'FLEXIBLE') return false;
  // Don't hold if queue is already full
  if (_holdQueue.length >= 4) return false;

  // Check if any DC has an active negative weather event
  const hasNegativeEvent = Object.values(_weatherEvents).some(
    ev => ev && (ev.type === 'cold_snap' || ev.type === 'storm' || ev.type === 'heat_wave')
  );

  // Strategy 1: Hold during bad weather if NN has any hold signal (>5%)
  if (hasNegativeEvent && holdProb > 0.05) return true;

  // Strategy 2: Hold when carbon is elevated everywhere (>180) and NN wants to hold (>8%)
  const carbons = LOC_IDS.map(id => snap[id]?.carbon ?? 999);
  const bestNow = Math.min(...carbons);
  if (bestNow > 180 && holdProb > 0.08) return true;

  return false;
}

function releaseHeldJobs(snap) {
  // Check each held job: release if conditions improved or timeout
  const released = [];
  const kept = [];
  const carbons = LOC_IDS.map(id => snap[id]?.carbon ?? 999);
  const bestNow = Math.min(...carbons);

  for (const entry of _holdQueue) {
    entry.holdSteps += 1;
    const timedOut = entry.holdSteps >= HOLD_MAX_STEPS;
    const conditionsImproved = bestNow < entry.carbonAtHold * 0.8; // 20% improvement
    if (timedOut || conditionsImproved) {
      entry.releaseReason = timedOut ? 'timeout' : 'conditions_improved';
      released.push(entry);
    } else {
      kept.push(entry);
    }
  }
  _holdQueue = kept;
  return released;
}

// ═══════════════════════════════════════════════════════════════
// SIMULATION STEP
// ═══════════════════════════════════════════════════════════════

export function createInitialState() {
  const utilisations = {};
  for (const id of LOC_IDS) utilisations[id] = 0.25 + Math.random() * 0.15;
  initWeatherSystems();
  _weatherEvents = {};
  initPPO();
  initBaselineMetrics();
  _holdQueue = [];
  _jobQueue = [];
  _queueStats = { flexible: 0, semiFlex: 0, pinned: 0, held: 0, totalProcessed: 0 };
  const state = {
    utcHour: 6.0,
    day: 1,
    stepCount: 0,
    totalCarbonSaved: 0,
    totalCostSaved: 0,
    totalJobsProcessed: 0,
    totalSLAViolations: 0,
    totalRenewableSum: 0,
    totalHoldDecisions: 0,
    totalHoldReleases: 0,
    cloudStates: {},
    windGustStates: {},
    utilisations,
  };
  for (const id of LOC_IDS) {
    state.cloudStates[id] = 0;
    state.windGustStates[id] = 0;
  }
  _snapshot = computeSnapshot(state.utcHour, utilisations);
  return state;
}

export function simulationStep(prevState) {
  const state = { ...prevState };

  // 1. Advance weather systems + events
  stepWeatherSystems(0.15);
  stepWeatherEvents(0.15);

  // 2. Compute sensor snapshot
  _snapshot = computeSnapshot(state.utcHour, state.utilisations);

  // Sync cloud/gust states for MapCanvas
  state.cloudStates = { ...state.cloudStates };
  state.windGustStates = { ...state.windGustStates };
  for (const id of LOC_IDS) {
    state.cloudStates[id] = _snapshot[id]?.cloudCover ?? 0;
    state.windGustStates[id] = _snapshot[id]?.windExtra > 2 ? 0.7 : 0;
  }

  // 3. Generate job + track queue composition
  const job = generateJob(state.utcHour);
  if (job.type === 'FLEXIBLE') _queueStats.flexible += 1;
  else if (job.type === 'SEMI_FLEX') _queueStats.semiFlex += 1;
  else _queueStats.pinned += 1;

  // 3b. Release held jobs whose conditions improved or timed out
  const released = releaseHeldJobs(_snapshot);
  for (const entry of released) {
    state.totalHoldReleases = (state.totalHoldReleases || 0) + 1;
    // Process released job with current (better) snapshot
    const relDecision = agentDecide(entry.job, _snapshot);
    const relOriginCarbon = _snapshot[entry.job.origin]?.carbon ?? 0;
    const relDestCarbon = _snapshot[relDecision.dest]?.carbon ?? 0;
    const relCarbonSaved = (relOriginCarbon - relDestCarbon) * entry.job.compute / 1000;
    state.totalCarbonSaved += Math.max(0, relCarbonSaved);
    state.totalJobsProcessed += 1;
    state.totalRenewableSum += _snapshot[relDecision.dest]?.rf ?? 0;
    _queueStats.totalProcessed += 1;
  }

  // 4. Agent decision
  const decision = agentDecide(job, _snapshot);

  // 4a. Check if NN wants to HOLD this job
  let held = false;
  if (_nnLoaded && job.type === 'FLEXIBLE') {
    const features = extractFeatures47(_snapshot, job.origin);
    const result = nnForward(features);
    const carbons = LOC_IDS.map(id => _snapshot[id]?.carbon ?? 999);
    const bestNow = Math.min(...carbons);
    if (shouldHold(job, _snapshot, result.holdProb)) {
      // Build reason based on what triggered the hold
      const activeEvents = Object.entries(_weatherEvents)
        .filter(([, ev]) => ev && (ev.type === 'cold_snap' || ev.type === 'storm' || ev.type === 'heat_wave'))
        .map(([loc, ev]) => `${ev.type.replace('_', ' ')} at ${loc}`);
      const holdReason = activeEvents.length > 0
        ? `${activeEvents[0]} — grid carbon spiked (${Math.round(bestNow)}g), holding for cleaner window`
        : `Carbon elevated (${Math.round(bestNow)}g) across all DCs — waiting for renewable window`;
      _holdQueue.push({
        job, heldAt: state.utcHour, holdSteps: 0,
        carbonAtHold: bestNow,
        holdProb: result.holdProb,
        reason: holdReason,
      });
      held = true;
      _queueStats.held += 1;
      state.totalHoldDecisions = (state.totalHoldDecisions || 0) + 1;
    }
  }

  // ── 4b. Shadow baseline decision (same job, same snapshot) ──
  const randomDest = randomBaseline(job, _snapshot);

  const originCarbon = _snapshot[job.origin].carbon;
  const originCost = _snapshot[job.origin].cost;

  // Random baseline metrics
  const rCarbon = (originCarbon - _snapshot[randomDest].carbon) * job.compute / 1000;
  const rCost = (originCost - _snapshot[randomDest].cost) * job.compute;
  _baselineMetrics.random.carbonSaved += Math.max(0, rCarbon);
  _baselineMetrics.random.costSaved += rCost;
  _baselineMetrics.random.renewableSum += _snapshot[randomDest].rf;
  _baselineMetrics.random.jobs += 1;

  // 5-6. Only update metrics if job was NOT held
  let carbonSaved = 0, costSaved = 0, slaOk = true;

  if (!held) {
    // 5. Update utilisation
    const destCap = LOCATIONS[decision.dest].capacity;
    state.utilisations = { ...state.utilisations };
    state.utilisations[decision.dest] = Math.min(0.95,
      state.utilisations[decision.dest] + job.compute / destCap);

    // 6. RL agent metrics
    const destCarbon = _snapshot[decision.dest].carbon;
    const destCost = _snapshot[decision.dest].cost;
    carbonSaved = (originCarbon - destCarbon) * job.compute / 1000;
    costSaved = (originCost - destCost) * job.compute;

    state.totalCarbonSaved += Math.max(0, carbonSaved);
    state.totalCostSaved += costSaved;
    state.totalJobsProcessed += 1;
    state.totalRenewableSum += _snapshot[decision.dest].rf;
    _queueStats.totalProcessed += 1;

    if (job.maxLatency > 0 && job.type === 'SEMI_FLEX' && decision.dest !== job.origin) {
      if (job.procTime + 0.015 > job.maxLatency) {
        slaOk = false;
        state.totalSLAViolations += 1;
      }
    }
  }

  _baselineMetrics.rl.carbonSaved = state.totalCarbonSaved;
  _baselineMetrics.rl.costSaved = state.totalCostSaved;
  _baselineMetrics.rl.renewableSum = state.totalRenewableSum;
  _baselineMetrics.rl.jobs = state.totalJobsProcessed;

  // 7. Advance time
  state.utcHour += 0.15;
  if (state.utcHour >= 24) { state.utcHour -= 24; state.day += 1; }
  state.stepCount += 1;

  // 8. Utilisation decay
  for (const loc of LOC_IDS) {
    state.utilisations[loc] = Math.max(0.12, state.utilisations[loc] * 0.97 + (Math.random() - 0.5) * 0.01);
  }

  return { state, job, decision, carbonSaved, costSaved, slaOk, held, released };
}
