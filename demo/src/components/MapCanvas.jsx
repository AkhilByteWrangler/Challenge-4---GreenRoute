import { useRef, useEffect, useState, useCallback } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import { createRoot } from 'react-dom/client';
import { Compass, Eye, EyeOff } from 'lucide-react';
import { LOCATIONS, LOC_IDS } from '../simulation/locations';
import { getSnapshot, getWeatherSystems } from '../simulation/engine';
import NodeTooltip from './NodeTooltip';
import 'leaflet/dist/leaflet.css';

// Canvas rendering component
function CanvasLayer({ packets, advancePackets, paused, setTooltip, nodePositions, darkMode, showInfoCards }) {
  const map = useMap();
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const frameRef = useRef(null);
  const nodePositionsRef = nodePositions;

  const handleClick = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const snap = getSnapshot();

    for (const locId of LOC_IDS) {
      const np = nodePositionsRef.current[locId];
      if (!np) continue;
      if (Math.hypot(mx - np.x, my - np.y) < 25) {
        const loc = LOCATIONS[locId];
        const s = snap?.[locId];
        if (!s) return;
        setTooltip({
          x: np.x + 50,
          y: Math.max(np.y - 100, 10),
          loc,
          solar: s.solar,
          wind: s.wind,
          rf: s.rf,
          carbon: s.carbon,
          cost: s.cost,
          util: s.util,
        });
        return;
      }
    }
    setTooltip(null);
  }, [setTooltip, nodePositionsRef]);

  useEffect(() => {
    const mapContainer = map.getContainer();
    if (!containerRef.current) {
      const overlayDiv = document.createElement('div');
      overlayDiv.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:auto;z-index:400;';
      mapContainer.appendChild(overlayDiv);
      containerRef.current = overlayDiv;

      const canvas = document.createElement('canvas');
      canvas.style.cssText = 'position:absolute;top:0;left:0;display:block;';
      overlayDiv.appendChild(canvas);
      canvasRef.current = canvas;

      overlayDiv.addEventListener('click', handleClick);

      return () => {
        overlayDiv.removeEventListener('click', handleClick);
      };
    }
  }, [map, handleClick]);

  const animate = useCallback(() => {
    const canvas = canvasRef.current;
    const mapContainer = map.getContainer();
    if (!canvas || !mapContainer) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = mapContainer.offsetWidth * dpr;
    canvas.height = mapContainer.offsetHeight * dpr;
    canvas.style.width = mapContainer.offsetWidth + 'px';
    canvas.style.height = mapContainer.offsetHeight + 'px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr);

    const snap = getSnapshot();
    const systems = getWeatherSystems();
    const time = Date.now() / 1000; // Current time in seconds

    // Draw weather systems first (behind everything)
    for (const ws of systems) {
      const point = map.latLngToContainerPoint(L.latLng(ws.lat, ws.lon));
      const radiusPixels = ws.radius * (map.getZoom() / 4) * 15; // Scale with zoom

      if (ws.type === 'cloud') {
        // Dark, threatening clouds
        const cloudAlpha = ws.intensity * 0.32; // Much darker

        // Main dark cloud body
        const mainGrad = ctx.createRadialGradient(point.x, point.y, radiusPixels * 0.2, point.x, point.y, radiusPixels * 0.8);
        mainGrad.addColorStop(0, `rgba(80,95,130,${cloudAlpha})`);
        mainGrad.addColorStop(0.6, `rgba(70,80,110,${cloudAlpha * 0.6})`);
        mainGrad.addColorStop(1, `rgba(70,80,110,0)`);
        ctx.fillStyle = mainGrad;
        ctx.beginPath();
        ctx.arc(point.x, point.y, radiusPixels, 0, Math.PI * 2);
        ctx.fill();

        // Darker turbulent edges
        for (let i = 0; i < 6; i++) {
          const angle = (i / 6) * Math.PI * 2 + time * 0.08;
          const edgeX = point.x + Math.cos(angle) * radiusPixels * 0.75;
          const edgeY = point.y + Math.sin(angle) * radiusPixels * 0.55;
          const edgeGrad = ctx.createRadialGradient(edgeX, edgeY, 0, edgeX, edgeY, radiusPixels * 0.45);
          edgeGrad.addColorStop(0, `rgba(100,115,150,${cloudAlpha * 0.5})`);
          edgeGrad.addColorStop(1, 'rgba(100,115,150,0)');
          ctx.fillStyle = edgeGrad;
          ctx.fillRect(edgeX - radiusPixels * 0.45, edgeY - radiusPixels * 0.45, radiusPixels * 0.9, radiusPixels * 0.9);
        }

      } else if (ws.type === 'storm') {
        // Whirlpool effect — rotating spiral storm
        const stormAlpha = ws.intensity * 0.35;
        const spiralRotation = time * 0.8; // Rotation speed

        // Dark whirlpool center
        const whirlGrad = ctx.createRadialGradient(point.x, point.y, radiusPixels * 0.1, point.x, point.y, radiusPixels);
        whirlGrad.addColorStop(0, `rgba(40,50,75,${stormAlpha})`);
        whirlGrad.addColorStop(0.3, `rgba(50,65,95,${stormAlpha * 0.8})`);
        whirlGrad.addColorStop(0.7, `rgba(60,75,105,${stormAlpha * 0.4})`);
        whirlGrad.addColorStop(1, `rgba(60,75,105,0)`);
        ctx.fillStyle = whirlGrad;
        ctx.beginPath();
        ctx.arc(point.x, point.y, radiusPixels, 0, Math.PI * 2);
        ctx.fill();

        // Spiral whirlpool arms
        const numArms = 3;
        for (let arm = 0; arm < numArms; arm++) {
          ctx.strokeStyle = `rgba(70,85,120,${ws.intensity * 0.25})`;
          ctx.lineWidth = 2;
          ctx.beginPath();

          for (let i = 0; i < 60; i++) {
            const angle = (arm / numArms) * Math.PI * 2 + (i / 60) * Math.PI * 6 + spiralRotation;
            const dist = radiusPixels * 0.2 + (i / 60) * radiusPixels * 0.8;
            const x = point.x + Math.cos(angle) * dist;
            const y = point.y + Math.sin(angle) * dist;
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
          }
          ctx.stroke();
        }

        // Rain streaks in spiral pattern
        const numRainStreaks = Math.floor(ws.intensity * 40);
        for (let i = 0; i < numRainStreaks; i++) {
          const rainAngle = spiralRotation + (i / numRainStreaks) * Math.PI * 2;
          const rainDist = radiusPixels * (0.2 + Math.random() * 0.7);
          const rainX = point.x + Math.cos(rainAngle) * rainDist;
          const rainBaseY = point.y + Math.sin(rainAngle) * rainDist;
          const rainPhase = (time * 3 + i * 0.08) % 1;
          const rainY = rainBaseY + rainPhase * radiusPixels * 0.5;
          const rainAlpha = ws.intensity * 0.25 * (1 - rainPhase);

          ctx.beginPath();
          ctx.moveTo(rainX, rainY);
          ctx.lineTo(rainX - 0.4, rainY + 5);
          ctx.strokeStyle = `rgba(100,140,200,${rainAlpha})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }

      } else if (ws.type === 'clear') {
        // Clear zone — subtle solar enhancement
        const clearGrad = ctx.createRadialGradient(point.x, point.y, 0, point.x, point.y, radiusPixels);
        clearGrad.addColorStop(0, `rgba(220,200,100,${ws.intensity * 0.08})`);
        clearGrad.addColorStop(0.5, `rgba(220,200,100,${ws.intensity * 0.03})`);
        clearGrad.addColorStop(1, 'rgba(220,200,100,0)');
        ctx.fillStyle = clearGrad;
        ctx.fillRect(point.x - radiusPixels, point.y - radiusPixels, radiusPixels * 2, radiusPixels * 2);
      }

      // Wind flow — realistic streamlines
      if (ws.windBoost > 2) {
        const windDir = ws.type === 'storm' ? time * 1.2 : time * 0.3; // Storms rotate faster

        // Multiple wind streamlines with natural variation
        const numStreamlines = Math.floor(ws.windBoost * 3);
        for (let i = 0; i < numStreamlines; i++) {
          const streamAngle = (i / numStreamlines) * Math.PI * 2 + windDir;
          const streamDist = radiusPixels * (0.35 + Math.sin(time * 0.5 + i) * 0.15);
          const streamLength = 40 + Math.sin(time * 0.3 + i * 1.5) * 20;

          // Smooth flowing streamline
          ctx.strokeStyle = `rgba(110,160,210,${ws.windBoost * 0.065})`;
          ctx.lineWidth = 1.3;
          ctx.lineCap = 'round';
          ctx.beginPath();

          // Start point
          const startX = point.x + Math.cos(streamAngle) * streamDist;
          const startY = point.y + Math.sin(streamAngle) * streamDist;

          // Curved path following wind direction
          const ctrl1X = startX + Math.cos(streamAngle + 0.4) * streamLength * 0.4;
          const ctrl1Y = startY + Math.sin(streamAngle + 0.4) * streamLength * 0.4;
          const ctrl2X = startX + Math.cos(streamAngle - 0.4) * streamLength * 0.8;
          const ctrl2Y = startY + Math.sin(streamAngle - 0.4) * streamLength * 0.8;
          const endX = startX + Math.cos(streamAngle) * streamLength;
          const endY = startY + Math.sin(streamAngle) * streamLength;

          ctx.moveTo(startX, startY);
          ctx.bezierCurveTo(ctrl1X, ctrl1Y, ctrl2X, ctrl2Y, endX, endY);
          ctx.stroke();
        }
      }
    }

    // Draw routing arcs (behind)
    for (const p of packets) {
      const o = nodePositionsRef.current[p.origin];
      const d = nodePositionsRef.current[p.dest];
      if (!o || !d) continue;

      const mx = (o.x + d.x) / 2;
      const my = Math.min(o.y, d.y) - 30 - Math.abs(o.x - d.x) * 0.15;
      const t = p.t;
      const x = (1 - t) * (1 - t) * o.x + 2 * (1 - t) * t * mx + t * t * d.x;
      const y = (1 - t) * (1 - t) * o.y + 2 * (1 - t) * t * my + t * t * d.y;

      ctx.beginPath();
      ctx.moveTo(o.x, o.y);
      ctx.quadraticCurveTo(mx, my, d.x, d.y);
      ctx.strokeStyle = p.colour + '15';
      ctx.lineWidth = 1.2;
      ctx.setLineDash([3, 2]);
      ctx.stroke();
      ctx.setLineDash([]);

      const glow = ctx.createRadialGradient(x, y, 0, x, y, 12);
      glow.addColorStop(0, p.colour + '22');
      glow.addColorStop(1, p.colour + '00');
      ctx.fillStyle = glow;
      ctx.fillRect(x - 12, y - 12, 24, 24);

      ctx.beginPath();
      ctx.arc(x, y, 2.5, 0, Math.PI * 2);
      ctx.fillStyle = p.colour;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, y, 0.8, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
    }

    // Draw DC nodes
    for (const locId of LOC_IDS) {
      const loc = LOCATIONS[locId];
      const s = snap?.[locId];
      if (!s) continue;

      const point = map.latLngToContainerPoint(L.latLng(loc.lat, loc.lon));
      nodePositionsRef.current[locId] = { x: point.x, y: point.y };

      const { rf, util } = s;
      const R = 16;

      // Background
      ctx.beginPath();
      ctx.arc(point.x, point.y, R + 8, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0,0,0,0.5)';
      ctx.fill();

      // Renewable arc
      ctx.beginPath();
      ctx.arc(point.x, point.y, R, -Math.PI / 2, -Math.PI / 2 + rf * Math.PI * 2);
      ctx.strokeStyle = '#4ade80';
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.stroke();

      // Background arc
      ctx.beginPath();
      ctx.arc(point.x, point.y, R, -Math.PI / 2 + rf * Math.PI * 2, -Math.PI / 2 + Math.PI * 2);
      ctx.strokeStyle = 'rgba(200,200,220,0.1)';
      ctx.lineWidth = 2.5;
      ctx.stroke();

      // Util arc
      ctx.beginPath();
      ctx.arc(point.x, point.y, R - 4, -Math.PI / 2, -Math.PI / 2 + util * Math.PI * 2);
      ctx.strokeStyle = util > 0.8 ? '#ff6b6b' : '#6b9eff';
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';
      ctx.stroke();

      // Core circle
      ctx.beginPath();
      ctx.arc(point.x, point.y, R - 8, 0, Math.PI * 2);
      const coreGrad = ctx.createRadialGradient(point.x - 2, point.y - 2, 0, point.x, point.y, R - 8);
      coreGrad.addColorStop(0, loc.colour);
      coreGrad.addColorStop(1, loc.colour + 'aa');
      ctx.fillStyle = coreGrad;
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.35)';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Label
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 9px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(locId, point.x, point.y + 3);

      // Weather event badge and visual effects
      if (s.weatherEvent) {
        ctx.font = '600 7px Inter, sans-serif';
        ctx.fillStyle = 'rgba(255,255,255,0.5)';
        ctx.fillText(s.weatherEvent, point.x, point.y - R - 10);

        // Visual effects for each weather event type
        if (s.weatherEvent.includes('Solar')) {
          // Solar Boom — bright golden rays
          ctx.save();
          for (let ray = 0; ray < 8; ray++) {
            const rayAngle = (ray / 8) * Math.PI * 2 + time * 0.7;
            const rayLength = 60 + Math.sin(time * 2 + ray) * 20;
            ctx.strokeStyle = `rgba(255,200,50,${0.4 - (ray % 2) * 0.12})`;
            ctx.lineWidth = 3;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(point.x, point.y);
            ctx.lineTo(
              point.x + Math.cos(rayAngle) * rayLength,
              point.y + Math.sin(rayAngle) * rayLength
            );
            ctx.stroke();
          }
          // Golden halo
          const haloGrad = ctx.createRadialGradient(point.x, point.y, 10, point.x, point.y, 55);
          haloGrad.addColorStop(0, 'rgba(255,240,100,0.2)');
          haloGrad.addColorStop(0.5, 'rgba(255,200,50,0.08)');
          haloGrad.addColorStop(1, 'rgba(255,200,50,0)');
          ctx.fillStyle = haloGrad;
          ctx.beginPath();
          ctx.arc(point.x, point.y, 55, 0, Math.PI * 2);
          ctx.fill();
          // Bright core
          const coreHalo = ctx.createRadialGradient(point.x, point.y, 3, point.x, point.y, 20);
          coreHalo.addColorStop(0, 'rgba(255,255,180,0.3)');
          coreHalo.addColorStop(1, 'rgba(255,220,50,0)');
          ctx.fillStyle = coreHalo;
          ctx.beginPath();
          ctx.arc(point.x, point.y, 20, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();

        } else if (s.weatherEvent.includes('Heat')) {
          // Heat Wave — shimmering distortion waves
          for (let wave = 0; wave < 6; wave++) {
            const waveY = point.y + R + 8 - ((time * 25 + wave * 8) % 50);
            const waveWidth = R + 20 + Math.sin(time * 3 + wave) * 10;
            const alpha = 0.25 * (1 - ((time * 25 + wave * 8) % 50) / 50);
            ctx.beginPath();
            ctx.moveTo(point.x - waveWidth / 2, waveY);
            ctx.quadraticCurveTo(point.x, waveY - 4 * Math.sin(time * 4 + wave), point.x + waveWidth / 2, waveY);
            ctx.strokeStyle = `rgba(255,140,50,${alpha})`;
            ctx.lineWidth = 2.5;
            ctx.lineCap = 'round';
            ctx.stroke();
          }
          // Heat shimmer glow
          const heatGrad = ctx.createRadialGradient(point.x, point.y, R, point.x, point.y, R + 35);
          heatGrad.addColorStop(0, `rgba(255,160,80,${0.15 + Math.sin(time * 2) * 0.08})`);
          heatGrad.addColorStop(1, 'rgba(255,100,50,0)');
          ctx.fillStyle = heatGrad;
          ctx.beginPath();
          ctx.arc(point.x, point.y, R + 35, 0, Math.PI * 2);
          ctx.fill();

        } else if (s.weatherEvent.includes('Cold')) {
          // Cold Snap — snowflakes drifting with icy glow
          for (let i = 0; i < 20; i++) {
            const angle = (time * 0.4 + i * 0.315) % (Math.PI * 2);
            const dist = R + 20 + 25 * Math.sin(time * 0.5 + i * 1.5);
            const fx = point.x + Math.cos(angle) * dist;
            const fy = point.y + Math.sin(angle) * dist * 0.6 + Math.sin(time * 0.8 + i) * 8;
            const alpha = 0.5 + 0.3 * Math.sin(time * 1.8 + i);
            ctx.fillStyle = `rgba(200,240,255,${alpha})`;
            ctx.beginPath();
            ctx.arc(fx, fy, 2.5, 0, Math.PI * 2);
            ctx.fill();
            // Snowflake star pattern
            for (let arm = 0; arm < 6; arm++) {
              const armAngle = (arm / 6) * Math.PI;
              const armX = fx + Math.cos(armAngle) * 3.5;
              const armY = fy + Math.sin(armAngle) * 3.5;
              ctx.strokeStyle = `rgba(220,250,255,${alpha * 0.6})`;
              ctx.lineWidth = 0.8;
              ctx.beginPath();
              ctx.moveTo(fx, fy);
              ctx.lineTo(armX, armY);
              ctx.stroke();
            }
          }
          // Icy blue glow
          const coldGrad = ctx.createRadialGradient(point.x, point.y, R, point.x, point.y, R + 40);
          coldGrad.addColorStop(0, `rgba(150,200,255,${0.12 + Math.sin(time * 1.5) * 0.08})`);
          coldGrad.addColorStop(0.5, 'rgba(100,180,255,0.05)');
          coldGrad.addColorStop(1, 'rgba(100,180,255,0)');
          ctx.fillStyle = coldGrad;
          ctx.beginPath();
          ctx.arc(point.x, point.y, R + 40, 0, Math.PI * 2);
          ctx.fill();

        } else if (s.weatherEvent.includes('Storm')) {
          // Storm — rain, wind, and lightning centered on the DC
          const stormIntensity = Math.min(s.wind / 10, 1); // Scale to wind speed
          
          // Rain streaks falling at angle (wind-driven)
          const rainAngle = 0.3 * (s.wind / 5); // Rain angle increases with wind
          const numRainStreaks = Math.floor(15 + s.wind * 3); // More rain with stronger wind
          for (let i = 0; i < numRainStreaks; i++) {
            const rainX = point.x + (Math.random() - 0.5) * 70;
            const rainBaseY = point.y - 40 + (Math.random() - 0.5) * 70;
            const rainPhase = (time * (2 + s.wind) + i * 0.04) % 1; // Faster with stronger wind
            const rainY = rainBaseY + rainPhase * 80;
            const rainAlpha = stormIntensity * (1 - rainPhase) * 0.4;
            
            ctx.beginPath();
            ctx.moveTo(rainX, rainY);
            ctx.lineTo(rainX + Math.cos(rainAngle) * 8, rainY + Math.sin(rainAngle) * 8 + 6);
            ctx.strokeStyle = `rgba(150,180,220,${rainAlpha})`;
            ctx.lineWidth = 1.2;
            ctx.lineCap = 'round';
            ctx.stroke();
          }
          
          // Wind flow streamlines around the DC - scales with wind speed
          const windDir = time * (0.5 + s.wind * 0.2); // Faster rotation with stronger wind
          const numWindStreams = Math.floor(5 + s.wind * 1.5);
          for (let i = 0; i < numWindStreams; i++) {
            const streamAngle = (i / numWindStreams) * Math.PI * 2 + windDir;
            const streamRadius = 25 + s.wind * 3;
            const streamLength = 20 + Math.sin(time * (1.2 + s.wind * 0.3) + i) * (10 + s.wind * 2);
            
            ctx.strokeStyle = `rgba(100,150,200,${(0.15 + s.wind * 0.04) * stormIntensity})`;
            ctx.lineWidth = 1 + s.wind * 0.15;
            ctx.lineCap = 'round';
            ctx.beginPath();
            
            const startX = point.x + Math.cos(streamAngle) * streamRadius;
            const startY = point.y + Math.sin(streamAngle) * streamRadius;
            const endX = startX + Math.cos(streamAngle) * streamLength;
            const endY = startY + Math.sin(streamAngle) * streamLength;
            
            ctx.moveTo(startX, startY);
            ctx.lineTo(endX, endY);
            ctx.stroke();
          }
          
          // Lightning flashes
          const flashPhase = (time * 4) % 1;
          if (flashPhase < 0.08 || (flashPhase > 0.12 && flashPhase < 0.25) || (flashPhase > 0.35 && flashPhase < 0.4)) {
            const flashAlpha = flashPhase < 0.08 ? 0.5 * (1 - flashPhase / 0.08) : flashPhase > 0.12 && flashPhase < 0.25 ? 0.3 * (1 - (flashPhase - 0.12) / 0.13) : 0.2 * (1 - (flashPhase - 0.35) / 0.05);
            ctx.fillStyle = `rgba(200,220,255,${flashAlpha})`;
            ctx.beginPath();
            ctx.arc(point.x, point.y, R + 20, 0, Math.PI * 2);
            ctx.fill();
            
            // Lightning bolt cracks
            for (let bolt = 0; bolt < 2; bolt++) {
              ctx.strokeStyle = `rgba(255,255,150,${flashAlpha * 0.6})`;
              ctx.lineWidth = 1;
              ctx.beginPath();
              const boltAngle = (bolt / 2) * Math.PI * 2;
              const boltX = point.x + Math.cos(boltAngle) * 15;
              const boltY = point.y + Math.sin(boltAngle) * 15;
              ctx.moveTo(point.x, point.y);
              ctx.lineTo(boltX, boltY);
              ctx.lineTo(boltX + (Math.random() - 0.5) * 8, boltY + (Math.random() - 0.5) * 8);
              ctx.stroke();
            }
          }
          
          // Storm cloud glow - darker/more oppressive, scales with wind
          const stormGrad = ctx.createRadialGradient(point.x, point.y, R, point.x, point.y, R + 45);
          stormGrad.addColorStop(0, `rgba(80,100,140,${0.15 + stormIntensity * 0.12 + Math.sin(time * 1.5) * 0.05})`);
          stormGrad.addColorStop(1, 'rgba(60,80,120,0)');
          ctx.fillStyle = stormGrad;
          ctx.beginPath();
          ctx.arc(point.x, point.y, R + 45, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // Wind animation — visible for any wind speed (unless already showing storm)
      if (s.wind > 1 && !s.weatherEvent?.includes('Storm')) {
        const windIntensity = Math.min(s.wind / 10, 0.6);
        const windDir = time * (0.4 + s.wind * 0.15);
        const numWindStreams = Math.floor(3 + s.wind * 1.2);
        
        for (let i = 0; i < numWindStreams; i++) {
          const streamAngle = (i / numWindStreams) * Math.PI * 2 + windDir;
          const streamRadius = 20 + s.wind * 2;
          const streamLength = 15 + Math.sin(time * (1 + s.wind * 0.2) + i) * (8 + s.wind * 1.5);
          
          ctx.strokeStyle = `rgba(120,160,210,${windIntensity * 0.5})`;
          ctx.lineWidth = 0.8 + s.wind * 0.1;
          ctx.lineCap = 'round';
          ctx.beginPath();
          
          const startX = point.x + Math.cos(streamAngle) * streamRadius;
          const startY = point.y + Math.sin(streamAngle) * streamRadius;
          const endX = startX + Math.cos(streamAngle) * streamLength;
          const endY = startY + Math.sin(streamAngle) * streamLength;
          
          ctx.moveTo(startX, startY);
          ctx.lineTo(endX, endY);
          ctx.stroke();
        }
      }

      // Info card below node — larger and more prominent (only if enabled)
      const { solar, wind, carbon, cost } = s;
      const cardY = point.y + R + 8;
      const cardW = 160, cardH = 100;
      const cardX = point.x - cardW / 2;

      if (showInfoCards) {
        // Card background
        ctx.shadowColor = darkMode ? 'rgba(0,0,0,0.5)' : 'rgba(0,0,0,0.2)';
        ctx.shadowBlur = 12;
        ctx.shadowOffsetY = 3;
        ctx.fillStyle = darkMode ? 'rgba(8,12,24,0.95)' : 'rgba(255,255,255,0.95)';
        ctx.strokeStyle = darkMode ? 'rgba(80,120,180,0.25)' : 'rgba(200,200,220,0.3)';
        ctx.lineWidth = 1;

        // Rounded rect
        const radius = 6;
        ctx.beginPath();
        ctx.moveTo(cardX + radius, cardY);
        ctx.lineTo(cardX + cardW - radius, cardY);
        ctx.quadraticCurveTo(cardX + cardW, cardY, cardX + cardW, cardY + radius);
        ctx.lineTo(cardX + cardW, cardY + cardH - radius);
        ctx.quadraticCurveTo(cardX + cardW, cardY + cardH, cardX + cardW - radius, cardY + cardH);
        ctx.lineTo(cardX + radius, cardY + cardH);
        ctx.quadraticCurveTo(cardX, cardY + cardH, cardX, cardY + cardH - radius);
        ctx.lineTo(cardX, cardY + radius);
        ctx.quadraticCurveTo(cardX, cardY, cardX + radius, cardY);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // Accent line
        const accentAlpha = rf > 0.5 ? 0.15 : carbon > 300 ? 0.12 : 0.1;
        const accentColor = rf > 0.5 ? 'rgba(74,222,128,' : carbon > 300 ? 'rgba(239,68,68,' : 'rgba(120,160,220,';
        ctx.fillStyle = accentColor + accentAlpha + ')';
        ctx.fillRect(cardX + 6, cardY + 3, cardW - 12, 1.2);

        // Card text — larger and spaced out
        ctx.font = '700 12px Space Mono, monospace';
        ctx.textAlign = 'left';

        // Solar
        ctx.fillStyle = solar > 100 ? (darkMode ? '#f0e68c' : '#d4a800') : (darkMode ? '#6b7280' : '#555555');
        ctx.fillText(`☀ ${Math.round(solar)} W/m²`, cardX + 10, cardY + 22);

        // Wind
        ctx.fillStyle = wind > 4 ? (darkMode ? '#00d4ff' : '#0088cc') : (darkMode ? '#6b7280' : '#555555');
        ctx.fillText(`💨 ${wind.toFixed(1)} m/s`, cardX + 10, cardY + 39);

        // Carbon
        if (carbon < 200) {
          ctx.fillStyle = darkMode ? '#90ee90' : '#228822';
        } else if (carbon < 400) {
          ctx.fillStyle = darkMode ? '#f0e68c' : '#cc8800';
        } else {
          ctx.fillStyle = '#cc0000';
        }
        ctx.fillText(`⚡ ${Math.round(carbon)} gCO₂`, cardX + 10, cardY + 56);

        // Renewable %
        ctx.fillStyle = rf > 0.5 ? (darkMode ? '#90ee90' : '#228822') : (darkMode ? '#a0a0a0' : '#666666');
        ctx.fillText(`♻ ${(rf * 100).toFixed(0)}%`, cardX + 10, cardY + 73);

        // Load % (right aligned)
        ctx.textAlign = 'right';
        ctx.fillStyle = util > 0.8 ? '#cc0000' : (darkMode ? '#6b9eff' : '#0044dd');
        ctx.fillText(`Load: ${(util * 100).toFixed(0)}%`, cardX + cardW - 10, cardY + 73);
      }
    }

    if (!paused) advancePackets();
    frameRef.current = requestAnimationFrame(animate);
  }, [packets, paused, advancePackets, map, showInfoCards]);

  useEffect(() => {
    frameRef.current = requestAnimationFrame(animate);
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [animate]);

  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      if (canvas) {
        const mapContainer = map.getContainer();
        const dpr = window.devicePixelRatio || 1;
        canvas.width = mapContainer.offsetWidth * dpr;
        canvas.height = mapContainer.offsetHeight * dpr;
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [map]);

  return null;
}

// Info cards visibility toggle control
function InfoCardsToggle({ showInfoCards, setShowInfoCards }) {
  const map = useMap();

  useEffect(() => {
    const button = document.createElement('button');
    button.className = 'leaflet-control-zoom-in map-info-toggle';
    button.type = 'button';
    button.title = showInfoCards ? 'Hide info cards' : 'Show info cards';
    button.setAttribute('aria-label', showInfoCards ? 'Hide info cards' : 'Show info cards');

    const container = document.createElement('div');
    container.style.cssText = 'display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;';
    button.appendChild(container);

    const root = createRoot(container);
    root.render(showInfoCards ? <Eye size={18} strokeWidth={2.5} /> : <EyeOff size={18} strokeWidth={2.5} />);

    button.style.cssText = `
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      background: white;
      border: 2px solid rgba(0,0,0,0.2);
      border-radius: 4px;
      cursor: pointer;
      color: #333;
      margin-top: 4px;
      padding: 0;
      transition: all 0.2s ease;
      font-size: 0;
    `;

    button.onmouseenter = () => {
      button.style.background = '#f5f5f5';
      button.style.borderColor = 'rgba(0,0,0,0.3)';
    };
    button.onmouseleave = () => {
      button.style.background = 'white';
      button.style.borderColor = 'rgba(0,0,0,0.2)';
    };
    button.onclick = () => setShowInfoCards(!showInfoCards);

    const zoomControls = map.getContainer().querySelector('.leaflet-control-zoom');
    if (zoomControls) {
      zoomControls.appendChild(button);
    }

    return () => {
      if (button.parentNode) {
        button.parentNode.removeChild(button);
      }
      root.unmount();
    };
  }, [map, showInfoCards, setShowInfoCards]);

  return null;
}

// Reset map view button control
function MapResetControl() {
  const map = useMap();

  const handleReset = useCallback(() => {
    map.setView([38.5, -96], 5);
  }, [map]);

  useEffect(() => {
    const button = document.createElement('button');
    button.className = 'leaflet-control-zoom-in map-reset-button';
    button.type = 'button';
    button.title = 'Reset map view';
    button.setAttribute('aria-label', 'Reset map view');

    const container = document.createElement('div');
    container.style.cssText = 'display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;';
    button.appendChild(container);

    const root = createRoot(container);
    root.render(<Compass size={18} strokeWidth={2.5} />);

    button.style.cssText = `
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      background: white;
      border: 2px solid rgba(0,0,0,0.2);
      border-radius: 4px;
      cursor: pointer;
      color: #333;
      margin-top: 8px;
      padding: 0;
      transition: all 0.2s ease;
      font-size: 0;
    `;

    button.onmouseenter = () => {
      button.style.background = '#f5f5f5';
      button.style.borderColor = 'rgba(0,0,0,0.3)';
    };
    button.onmouseleave = () => {
      button.style.background = 'white';
      button.style.borderColor = 'rgba(0,0,0,0.2)';
    };
    button.onclick = handleReset;

    const zoomControls = map.getContainer().querySelector('.leaflet-control-zoom');
    if (zoomControls) {
      zoomControls.appendChild(button);
    }

    return () => {
      if (button.parentNode) {
        button.parentNode.removeChild(button);
      }
      root.unmount();
    };
  }, [map, handleReset]);

  return null;
}

export default function MapCanvas({ simState, packets, advancePackets, paused, darkMode }) {
  const [tooltip, setTooltip] = useState(null);
  const [showInfoCards, setShowInfoCards] = useState(true);
  const nodePositions = useRef({});

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={[38.5, -96]}
        zoom={5}
        className="w-full h-full"
        zoomControl={true}
        scrollWheelZoom={true}
        dragging={!paused}
        maxZoom={10}
        minZoom={3}
      >
        <TileLayer
          key={darkMode ? 'dark' : 'light'}
          url={darkMode ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"}
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          maxZoom={18}
          minZoom={3}
        />
        <MapResetControl />
        <InfoCardsToggle showInfoCards={showInfoCards} setShowInfoCards={setShowInfoCards} />
        <CanvasLayer
          packets={packets}
          advancePackets={advancePackets}
          paused={paused}
          setTooltip={setTooltip}
          nodePositions={nodePositions}
          darkMode={darkMode}
          showInfoCards={showInfoCards}
        />
      </MapContainer>

      {tooltip && <NodeTooltip data={tooltip} onClose={() => setTooltip(null)} />}

      {paused && (
        <div className="absolute inset-0 bg-black/40 flex items-center justify-center z-50 pointer-events-none">
          <div className="text-center">
            <div className="text-3xl font-bold text-green-400 mb-2">⏸ PAUSED</div>
            <div className="text-sm text-gray-300">Click Resume to continue simulation</div>
          </div>
        </div>
      )}
    </div>
  );
}
