import { useRef, useEffect, useCallback, useState } from 'react';
import { LOCATIONS, LOC_IDS, US_OUTLINE, STATE_BORDERS, CITIES } from '../simulation/locations';
import { getSnapshot, getWeatherSystems, getWeatherEvents } from '../simulation/engine';
import NodeTooltip from './NodeTooltip';

// Map projection — Albers-like simple conic for continental US
function project(lon, lat, W, H) {
  const padX = 0.06, padY = 0.08;
  const x = padX * W + ((lon + 125) / 58) * W * (1 - 2 * padX);
  const y = padY * H + ((50 - lat) / 26) * H * (1 - 2 * padY);
  return [x, y];
}

export default function MapCanvas({ simState, packets, advancePackets }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const dimRef = useRef({ W: 800, H: 500 });
  const nodePositions = useRef({});
  const frameRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);

  // Resize
  const resize = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const rect = container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    dimRef.current = { W: rect.width, H: rect.height };
  }, []);

  useEffect(() => {
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, [resize]);

  // Time reference for smooth animations
  const tRef = useRef(0);

  // Main render loop
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const { W, H } = dimRef.current;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    tRef.current += 0.016;
    const t = tRef.current;
    const hour = simState.utcHour;
    const snap = getSnapshot();

    // 1. Sky background with day/night gradient
    drawSkyBackground(ctx, hour, W, H);

    // 2. Star field (visible in dark regions)
    drawStars(ctx, hour, W, H, t);

    // 3. US landmass
    drawLandmass(ctx, hour, W, H);

    // 4. State borders
    drawStateBorders(ctx, W, H);

    // 5. City dots
    drawCities(ctx, W, H);

    // 6. Day/night terminator overlay
    drawDayNightOverlay(ctx, hour, W, H);

    // 7. Weather — clouds + wind field
    drawWeather(ctx, hour, simState, snap, W, H, t);

    // 8. Routing arcs
    drawRoutingArcs(ctx, packets, nodePositions);
    advancePackets();

    // 9. DC nodes with gauges
    drawDCNodes(ctx, hour, snap, simState, W, H, nodePositions, t);

    frameRef.current = requestAnimationFrame(render);
  }, [simState, packets, advancePackets]);

  useEffect(() => {
    frameRef.current = requestAnimationFrame(render);
    return () => { if (frameRef.current) cancelAnimationFrame(frameRef.current); };
  }, [render]);

  // Click → tooltip
  const handleClick = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const snap = getSnapshot();
    for (const locId of LOC_IDS) {
      const np = nodePositions.current[locId];
      if (!np) continue;
      if (Math.hypot(mx - np.x, my - np.y) < 40) {
        const loc = LOCATIONS[locId];
        const s = snap?.[locId];
        if (!s) return;
        setTooltip({
          x: np.x + 50, y: Math.max(np.y - 100, 10),
          loc, solar: s.solar, wind: s.wind, rf: s.rf,
          carbon: s.carbon, cost: s.cost, util: s.util,
        });
        return;
      }
    }
    setTooltip(null);
  };

  return (
    <div ref={containerRef} className="relative w-full h-full overflow-hidden">
      <canvas ref={canvasRef} onClick={handleClick} className="block w-full h-full cursor-crosshair" />
      {tooltip && <NodeTooltip data={tooltip} onClose={() => setTooltip(null)} />}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// DRAWING LAYERS
// ═══════════════════════════════════════════════════════════════

// Sun longitude at a given UTC hour
function sunLon(utcHour) { return (12 - utcHour) * 15; }

// ── 1. Sky background ──
function drawSkyBackground(ctx, utcHour, W, H) {
  const sLon = sunLon(utcHour);
  // Average brightness across the US (-125 to -67)
  const usCenterLon = -96;
  const hourAngle = Math.abs(sLon - usCenterLon);
  const brightness = Math.max(0, Math.min(1, 1 - hourAngle / 90));

  const grad = ctx.createLinearGradient(0, 0, 0, H);
  if (brightness > 0.5) {
    grad.addColorStop(0, `rgba(10,20,50,${1 - brightness * 0.4})`);
    grad.addColorStop(1, '#0d1117');
  } else {
    grad.addColorStop(0, '#050810');
    grad.addColorStop(1, '#0a0e1a');
  }
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);
}

// ── 2. Stars ──
function drawStars(ctx, utcHour, W, H, t) {
  const sLon = sunLon(utcHour);
  // Seed-based star positions (deterministic)
  for (let i = 0; i < 120; i++) {
    const sx = ((i * 7919 + 104729) % 10000) / 10000 * W;
    const sy = ((i * 6271 + 31547) % 10000) / 10000 * H;
    const starLon = -125 + (sx / W) * 58;
    const distFromSun = Math.abs(sLon - starLon);
    if (distFromSun < 40) continue;
    const twinkle = 0.3 + 0.7 * Math.abs(Math.sin(t * 0.5 + i * 1.3));
    ctx.fillStyle = `rgba(200,210,255,${twinkle * 0.4})`;
    ctx.fillRect(sx, sy, 1.5, 1.5);
  }
}

// ── 3. US landmass ──
function drawLandmass(ctx, utcHour, W, H) {
  ctx.beginPath();
  US_OUTLINE.forEach(([lon, lat], i) => {
    const [x, y] = project(lon, lat, W, H);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.closePath();
  // Terrain-like gradient fill
  const tGrad = ctx.createLinearGradient(0, 0, W, H);
  tGrad.addColorStop(0, 'rgba(22,40,55,0.6)');
  tGrad.addColorStop(0.3, 'rgba(18,35,45,0.55)');
  tGrad.addColorStop(0.6, 'rgba(25,38,42,0.5)');
  tGrad.addColorStop(1, 'rgba(20,32,40,0.55)');
  ctx.fillStyle = tGrad;
  ctx.fill();
  ctx.strokeStyle = 'rgba(100,160,200,0.3)';
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

// ── 4. State borders ──
function drawStateBorders(ctx, W, H) {
  ctx.strokeStyle = 'rgba(80,130,170,0.15)';
  ctx.lineWidth = 0.8;
  for (const seg of STATE_BORDERS) {
    ctx.beginPath();
    seg.forEach(([lon, lat], i) => {
      const [x, y] = project(lon, lat, W, H);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
  }
}

// ── 5. City dots ──
function drawCities(ctx, W, H) {
  ctx.fillStyle = 'rgba(140,160,180,0.25)';
  for (const city of CITIES) {
    const [cx, cy] = project(city.lon, city.lat, W, H);
    ctx.beginPath();
    ctx.arc(cx, cy, 1.5, 0, Math.PI * 2);
    ctx.fill();
  }
}

// ── 6. Day/night overlay ──
function drawDayNightOverlay(ctx, utcHour, W, H) {
  const sLon = sunLon(utcHour);
  // The terminator is at sLon ± 90°. For the US map range (-125 to -67):
  const [termX] = project(sLon - 90, 40, W, H);
  const [termX2] = project(sLon + 90, 40, W, H);

  // Night side gradient (dark overlay on the side away from sun)
  const nightGrad = ctx.createLinearGradient(
    Math.min(termX, termX2) - 100, 0,
    Math.max(termX, termX2) + 100, 0
  );

  // Determine which side is night
  if (sLon > -96) {
    // Sun is east of center → west side is darker
    nightGrad.addColorStop(0, 'rgba(0,0,20,0.5)');
    nightGrad.addColorStop(0.4, 'rgba(0,0,20,0.2)');
    nightGrad.addColorStop(0.7, 'rgba(0,0,0,0)');
    nightGrad.addColorStop(1, 'rgba(0,0,0,0)');
  } else {
    // Sun is west of center → east side is darker
    nightGrad.addColorStop(0, 'rgba(0,0,0,0)');
    nightGrad.addColorStop(0.3, 'rgba(0,0,0,0)');
    nightGrad.addColorStop(0.6, 'rgba(0,0,20,0.2)');
    nightGrad.addColorStop(1, 'rgba(0,0,20,0.5)');
  }
  ctx.fillStyle = nightGrad;
  ctx.fillRect(0, 0, W, H);

  // Sun glow
  const [sx, sy] = project(Math.max(-125, Math.min(-67, sLon)), 48, W, H);
  if (sx > -100 && sx < W + 100) {
    const sunGrad = ctx.createRadialGradient(sx, sy - 20, 0, sx, sy - 20, W * 0.35);
    sunGrad.addColorStop(0, 'rgba(255,200,80,0.12)');
    sunGrad.addColorStop(0.3, 'rgba(255,180,60,0.05)');
    sunGrad.addColorStop(1, 'rgba(255,180,60,0)');
    ctx.fillStyle = sunGrad;
    ctx.fillRect(0, 0, W, H);

    // Sun disc
    ctx.beginPath();
    ctx.arc(sx, Math.max(sy - 25, 15), 12, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255,220,100,0.8)';
    ctx.fill();
    ctx.beginPath();
    ctx.arc(sx, Math.max(sy - 25, 15), 20, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,220,100,0.2)';
    ctx.lineWidth = 2;
    ctx.stroke();
  }
}

// ── 7. Weather: moving fronts, cloud banks, rain, wind field ──
function drawWeather(ctx, utcHour, state, snap, W, H, t) {
  const systems = getWeatherSystems();

  // ── A. Draw moving weather front systems ──
  for (const ws of systems) {
    const [cx, cy] = project(ws.lon, ws.lat, W, H);
    const rPx = ws.radius * (W / 58);  // radius in pixels

    if (ws.type === 'cloud' || ws.type === 'storm') {
      // Large cloud bank — multiple overlapping ellipses
      const alpha = ws.intensity * (ws.type === 'storm' ? 0.35 : 0.2);
      const numBlobs = 6 + Math.floor(ws.intensity * 6);
      for (let i = 0; i < numBlobs; i++) {
        const angle = (i / numBlobs) * Math.PI * 2 + t * 0.1;
        const dist = rPx * 0.4 * (0.3 + 0.7 * ((i * 3 + 7) % 11) / 11);
        const bx = cx + Math.cos(angle) * dist;
        const by = cy + Math.sin(angle) * dist * 0.5;
        const blobR = rPx * (0.25 + 0.15 * Math.sin(i * 2.3 + t * 0.2));

        ctx.beginPath();
        ctx.ellipse(bx, by, blobR, blobR * 0.6, 0, 0, Math.PI * 2);
        ctx.fillStyle = ws.type === 'storm'
          ? `rgba(100,110,130,${alpha})`
          : `rgba(170,185,200,${alpha})`;
        ctx.fill();
      }

      // Storm: rain particles
      if (ws.type === 'storm') {
        const numDrops = Math.floor(ws.intensity * 30);
        for (let i = 0; i < numDrops; i++) {
          const dx = cx + (((i * 7919) % 1000) / 1000 - 0.5) * rPx * 1.6;
          const rainPhase = (t * 3 + i * 0.37) % 1;
          const dy = cy + rainPhase * rPx * 0.8 - rPx * 0.1;
          const dropAlpha = ws.intensity * 0.3 * (1 - rainPhase);
          ctx.beginPath();
          ctx.moveTo(dx, dy);
          ctx.lineTo(dx - 0.5, dy + 4 + ws.intensity * 3);
          ctx.strokeStyle = `rgba(130,160,220,${dropAlpha})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }
    } else {
      // Clear zone — subtle golden glow
      const clearGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, rPx);
      clearGrad.addColorStop(0, `rgba(255,220,120,${ws.intensity * 0.06})`);
      clearGrad.addColorStop(1, 'rgba(255,220,120,0)');
      ctx.fillStyle = clearGrad;
      ctx.fillRect(cx - rPx, cy - rPx, rPx * 2, rPx * 2);
    }

    // Wind arrows at front edges
    if (ws.windBoost > 3) {
      const numArrows = Math.floor(ws.windBoost * 1.5);
      for (let i = 0; i < numArrows; i++) {
        const a = (i / numArrows) * Math.PI * 2;
        const edgeDist = rPx * (0.8 + 0.3 * Math.sin(t + i * 1.7));
        const ax = cx + Math.cos(a) * edgeDist;
        const ay = cy + Math.sin(a) * edgeDist * 0.5;
        const windAngle = -0.2 + Math.sin(a) * 0.3;  // generally eastward
        const len = 6 + ws.windBoost;
        const phase = (t * 1.5 + i * 0.8) % 2;
        if (phase > 1.5) continue;
        const windAlpha = 0.2 * (1 - phase / 1.5);

        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax + Math.cos(windAngle) * len, ay + Math.sin(windAngle) * len);
        ctx.strokeStyle = `rgba(100,200,255,${windAlpha})`;
        ctx.lineWidth = 1;
        ctx.stroke();

        // Arrowhead
        const ex = ax + Math.cos(windAngle) * len;
        const ey = ay + Math.sin(windAngle) * len;
        ctx.beginPath();
        ctx.moveTo(ex, ey);
        ctx.lineTo(ex - 3 * Math.cos(windAngle - 0.5), ey - 3 * Math.sin(windAngle - 0.5));
        ctx.moveTo(ex, ey);
        ctx.lineTo(ex - 3 * Math.cos(windAngle + 0.5), ey - 3 * Math.sin(windAngle + 0.5));
        ctx.stroke();
      }
    }
  }

  // ── B. Per-DC wind indicators (animated streaks near each data center) ──
  if (!snap) return;
  for (const locId of LOC_IDS) {
    const s = snap[locId];
    if (!s || s.wind < 3) continue;
    const loc = LOCATIONS[locId];
    const [dcx, dcy] = project(loc.lon, loc.lat, W, H);
    const intensity = Math.min(1, s.wind / 18);
    const numStreaks = Math.floor(2 + intensity * 5);

    for (let i = 0; i < numStreaks; i++) {
      const ang = -0.2 + Math.sin(i * 2.7 + loc.lon * 0.1) * 0.35;
      const dist = 45 + i * 10 + Math.sin(t * 1.2 + i * 2.5) * 12;
      const phase = (t * (1 + intensity) + i * 0.9) % 2.5;
      if (phase > 2) continue;
      const len = 6 + intensity * 10;
      const sx = dcx + Math.cos(ang + i * 0.7) * dist;
      const sy = dcy + Math.sin(ang + i * 0.7) * dist * 0.4;
      const a = intensity * 0.3 * (1 - phase / 2);

      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(sx + Math.cos(ang) * len, sy + Math.sin(ang) * len);
      ctx.strokeStyle = `rgba(80,210,255,${a})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }
}

// ── 8. Routing arcs ──
function drawRoutingArcs(ctx, packets, nodePositions) {
  for (const p of packets) {
    const o = nodePositions.current[p.origin];
    const d = nodePositions.current[p.dest];
    if (!o || !d) continue;

    const mx = (o.x + d.x) / 2;
    const my = Math.min(o.y, d.y) - 40 - Math.abs(o.x - d.x) * 0.15;
    const t = p.t;
    const x = (1 - t) * (1 - t) * o.x + 2 * (1 - t) * t * mx + t * t * d.x;
    const y = (1 - t) * (1 - t) * o.y + 2 * (1 - t) * t * my + t * t * d.y;

    // Arc trail (faint)
    ctx.beginPath();
    ctx.moveTo(o.x, o.y);
    ctx.quadraticCurveTo(mx, my, d.x, d.y);
    ctx.strokeStyle = p.colour + '18';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Glow
    const glow = ctx.createRadialGradient(x, y, 0, x, y, 14);
    glow.addColorStop(0, p.colour + 'aa');
    glow.addColorStop(0.5, p.colour + '33');
    glow.addColorStop(1, p.colour + '00');
    ctx.fillStyle = glow;
    ctx.fillRect(x - 14, y - 14, 28, 28);

    // Packet dot
    ctx.beginPath();
    ctx.arc(x, y, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = p.colour;
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 0.5;
    ctx.stroke();
  }
}

// ── 9. DC nodes with gauges + readings ──
function drawDCNodes(ctx, utcHour, snap, state, W, H, nodePositions, t) {
  if (!snap) return;

  for (const locId of LOC_IDS) {
    const loc = LOCATIONS[locId];
    const s = snap[locId];
    if (!s) continue;
    const [nx, ny] = project(loc.lon, loc.lat, W, H);
    nodePositions.current[locId] = { x: nx, y: ny };

    const { solar, wind, rf, carbon, cost, util } = s;
    const R = 28;  // node radius

    // ── Outer glow (pulsing based on renewable fraction) ──
    const pulse = 1 + 0.08 * Math.sin(t * 2 + locId.charCodeAt(0));
    const glowR = (R + 15) * pulse;
    const glowGrad = ctx.createRadialGradient(nx, ny, R * 0.5, nx, ny, glowR);
    if (rf > 0.5) {
      glowGrad.addColorStop(0, `rgba(0,230,118,${0.2 + rf * 0.15})`);
      glowGrad.addColorStop(1, 'rgba(0,230,118,0)');
    } else {
      glowGrad.addColorStop(0, `rgba(255,82,82,${0.15 + (1 - rf) * 0.1})`);
      glowGrad.addColorStop(1, 'rgba(255,82,82,0)');
    }
    ctx.fillStyle = glowGrad;
    ctx.beginPath();
    ctx.arc(nx, ny, glowR, 0, Math.PI * 2);
    ctx.fill();

    // ── Renewable fraction arc (outer ring) ──
    ctx.beginPath();
    ctx.arc(nx, ny, R, -Math.PI / 2, -Math.PI / 2 + rf * Math.PI * 2);
    ctx.strokeStyle = '#00e676';
    ctx.lineWidth = 4;
    ctx.lineCap = 'round';
    ctx.stroke();
    ctx.lineCap = 'butt';

    // Background arc
    ctx.beginPath();
    ctx.arc(nx, ny, R, -Math.PI / 2 + rf * Math.PI * 2, -Math.PI / 2 + Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.lineWidth = 4;
    ctx.stroke();

    // ── Utilisation arc (inner ring) ──
    ctx.beginPath();
    ctx.arc(nx, ny, R - 6, -Math.PI / 2, -Math.PI / 2 + util * Math.PI * 2);
    ctx.strokeStyle = util > 0.8 ? '#ff5252' : '#40c4ff';
    ctx.lineWidth = 3;
    ctx.stroke();

    // ── Core circle ──
    ctx.beginPath();
    ctx.arc(nx, ny, R - 12, 0, Math.PI * 2);
    const coreGrad = ctx.createRadialGradient(nx - 3, ny - 3, 0, nx, ny, R - 12);
    coreGrad.addColorStop(0, loc.colour);
    coreGrad.addColorStop(1, loc.colour + '88');
    ctx.fillStyle = coreGrad;
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.5)';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // ── Location label ──
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 12px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(locId, nx, ny + 4);

    // ── Weather event badge above node ──
    const weatherEvent = s.weatherEvent;
    if (weatherEvent) {
      const badgeY = ny - R - 22;
      const evPulse = 0.7 + 0.3 * Math.sin(t * 4);

      // Event ring overlay
      let evColor = 'rgba(255,100,100,0.6)';
      if (weatherEvent.includes('Cold'))  evColor = `rgba(100,180,255,${0.4 * evPulse})`;
      if (weatherEvent.includes('Storm')) evColor = `rgba(150,100,220,${0.5 * evPulse})`;
      if (weatherEvent.includes('Heat'))  evColor = `rgba(255,120,50,${0.4 * evPulse})`;
      if (weatherEvent.includes('Solar')) evColor = `rgba(255,220,50,${0.4 * evPulse})`;

      ctx.beginPath();
      ctx.arc(nx, ny, R + 5, 0, Math.PI * 2);
      ctx.strokeStyle = evColor;
      ctx.lineWidth = 3;
      ctx.stroke();

      // Badge background
      ctx.font = 'bold 10px Inter, sans-serif';
      const badgeW = ctx.measureText(weatherEvent).width + 12;
      ctx.fillStyle = 'rgba(0,0,0,0.85)';
      ctx.strokeStyle = evColor;
      ctx.lineWidth = 1.5;
      roundRect(ctx, nx - badgeW / 2, badgeY - 8, badgeW, 18, 4);

      // Badge text
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.fillText(weatherEvent, nx, badgeY + 5);
      ctx.textAlign = 'left';
    }

    // ── Info card below node ──
    const cardY = ny + R + 10;
    const cardW = 110, cardH = 62;
    const cardX = nx - cardW / 2;

    // Card background
    ctx.fillStyle = 'rgba(10,14,26,0.85)';
    ctx.strokeStyle = 'rgba(100,160,200,0.2)';
    ctx.lineWidth = 1;
    roundRect(ctx, cardX, cardY, cardW, cardH, 6);

    // Readings
    ctx.font = '600 9px JetBrains Mono, monospace';
    ctx.textAlign = 'left';
    const rx = cardX + 6;
    let ry = cardY + 13;

    // Solar
    ctx.fillStyle = solar > 100 ? '#FFB300' : '#64748b';
    ctx.fillText(`☀ ${Math.round(solar)} W/m²`, rx, ry);
    ry += 12;

    // Wind
    ctx.fillStyle = wind > 4 ? '#00BCD4' : '#64748b';
    ctx.fillText(`💨 ${wind.toFixed(1)} m/s`, rx, ry);
    ry += 12;

    // Carbon
    ctx.fillStyle = carbon < 200 ? '#00e676' : carbon < 400 ? '#FFB300' : '#ff5252';
    ctx.fillText(`⚡ ${Math.round(carbon)} gCO₂`, rx, ry);
    ry += 12;

    // Renewable %  +  Util %
    ctx.fillStyle = rf > 0.5 ? '#00e676' : '#94a3b8';
    ctx.fillText(`♻ ${(rf * 100).toFixed(0)}%`, rx, ry);
    ctx.textAlign = 'right';
    ctx.fillStyle = util > 0.8 ? '#ff5252' : '#40c4ff';
    ctx.fillText(`${(util * 100).toFixed(0)}% load`, cardX + cardW - 6, ry);
    ctx.textAlign = 'left';
  }
}

// Rounded rectangle helper
function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
}
