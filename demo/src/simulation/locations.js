export const LOCATIONS = {
  CA: {
    id: 'CA', name: 'California', primary: 'solar',
    lat: 37.33, lon: -121.89, colour: '#FFB300', utcOffset: -8,
    peakSolarStart: 11, peakSolarEnd: 15, avgWind: 4.5,
    solarCF: 0.28, windCF: 0.12, baseCarbonIntensity: 200,
    baseCost: 0.18, basePUE: 1.15, capacity: 5000,
  },
  TX: {
    id: 'TX', name: 'Texas', primary: 'wind',
    lat: 32.78, lon: -96.80, colour: '#00BCD4', utcOffset: -6,
    peakSolarStart: 11, peakSolarEnd: 15, avgWind: 7.8,
    solarCF: 0.24, windCF: 0.35, baseCarbonIntensity: 310,
    baseCost: 0.09, basePUE: 1.25, capacity: 4500,
  },
  VA: {
    id: 'VA', name: 'Virginia', primary: 'mixed',
    lat: 39.04, lon: -77.49, colour: '#FF5252', utcOffset: -5,
    peakSolarStart: 11, peakSolarEnd: 14, avgWind: 3.2,
    solarCF: 0.16, windCF: 0.08, baseCarbonIntensity: 380,
    baseCost: 0.11, basePUE: 1.20, capacity: 6000,
  },
  OR: {
    id: 'OR', name: 'Oregon', primary: 'wind',
    lat: 45.52, lon: -122.68, colour: '#4CAF50', utcOffset: -8,
    peakSolarStart: 12, peakSolarEnd: 15, avgWind: 6.5,
    solarCF: 0.14, windCF: 0.30, baseCarbonIntensity: 280,
    baseCost: 0.08, basePUE: 1.12, capacity: 3500,
  },
  AZ: {
    id: 'AZ', name: 'Arizona', primary: 'solar',
    lat: 33.45, lon: -112.07, colour: '#FF9800', utcOffset: -7,
    peakSolarStart: 10, peakSolarEnd: 16, avgWind: 3.8,
    solarCF: 0.32, windCF: 0.10, baseCarbonIntensity: 220,
    baseCost: 0.10, basePUE: 1.30, capacity: 4000,
  },
};

export const LOC_IDS = ['CA', 'TX', 'VA', 'OR', 'AZ'];

export const US_OUTLINE = [
  [-124.7, 48.4], [-123.0, 48.2], [-122.8, 47.1], [-124.6, 46.3],
  [-124.1, 42.0], [-120.0, 42.0], [-120.0, 39.0], [-117.0, 37.5],
  [-114.6, 35.0], [-114.6, 32.7], [-111.1, 31.3], [-108.2, 31.8],
  [-106.6, 31.8], [-103.0, 29.0], [-99.5, 26.5], [-97.1, 25.9],
  [-97.1, 27.8], [-94.0, 29.7], [-89.6, 29.0], [-89.0, 30.2],
  [-85.0, 30.0], [-84.9, 29.5], [-81.1, 25.1], [-80.0, 25.8],
  [-80.5, 28.5], [-81.3, 31.0], [-79.0, 33.0], [-75.5, 35.5],
  [-75.0, 38.0], [-74.0, 39.5], [-72.0, 41.0], [-71.0, 41.5],
  [-70.0, 42.0], [-67.0, 44.8], [-67.0, 47.4], [-69.0, 47.4],
  [-70.7, 45.0], [-71.5, 45.0], [-75.0, 45.0], [-76.8, 44.0],
  [-79.0, 43.3], [-82.5, 41.7], [-83.5, 41.8], [-83.0, 42.3],
  [-82.4, 42.7], [-82.5, 43.8], [-83.2, 45.1], [-84.8, 45.8],
  [-88.0, 48.0], [-89.5, 48.0], [-95.2, 49.0], [-123.3, 49.0],
  [-124.7, 48.4],
];

// Simplified internal state border segments
export const STATE_BORDERS = [
  // West coast state divisions
  [[-124.2, 46.3], [-116.9, 46.0]],                  // WA/OR
  [[-124.2, 42.0], [-117.0, 42.0]],                  // OR/CA
  // CA / NV / AZ
  [[-120.0, 42.0], [-120.0, 39.0], [-114.6, 35.0]],  // CA/NV
  [[-114.6, 35.0], [-114.6, 32.7]],                   // CA/AZ (Colorado River)
  // Four Corners region
  [[-114.0, 37.0], [-109.0, 37.0]],                   // AZ/UT
  [[-120.0, 42.0], [-117.0, 42.0], [-117.0, 37.0], [-114.0, 37.0]], // NV borders
  [[-109.0, 37.0], [-109.0, 31.3]],                   // AZ/NM
  [[-109.0, 37.0], [-102.0, 37.0]],                   // CO/NM
  [[-109.0, 41.0], [-102.0, 41.0]],                   // WY/CO
  [[-111.0, 42.0], [-111.0, 37.0]],                   // UT/WY/CO
  [[-104.0, 49.0], [-104.0, 43.0], [-104.0, 37.0]],  // MT/WY/CO line
  [[-102.0, 41.0], [-102.0, 37.0]],                   // CO/KS/NE
  // Texas
  [[-103.0, 36.5], [-103.0, 32.0], [-106.6, 31.8]],  // TX panhandle + NM border
  [[-103.0, 36.5], [-100.0, 36.5]],                   // TX/OK panhandle top
  [[-100.0, 36.5], [-94.4, 36.5]],                    // OK/KS
  // Central vertical lines
  [[-97.0, 49.0], [-97.0, 43.5]],                     // ND/MN
  [[-96.5, 43.5], [-96.5, 40.0]],                     // SD/IA/NE
  // Mississippi River (approx)
  [[-89.5, 47.0], [-90.0, 43.0], [-91.0, 40.0], [-89.5, 37.0], [-90.0, 35.0], [-91.0, 32.0], [-89.5, 29.0]],
  // Great Lakes region
  [[-90.6, 42.5], [-82.5, 42.5]],                     // WI-IL-IN-OH line
  [[-87.5, 47.0], [-87.5, 42.5]],                     // WI/MI
  // East coast
  [[-80.5, 35.2], [-75.5, 35.8]],                     // NC/VA
  [[-83.7, 36.6], [-75.5, 36.6]],                     // VA/TN/NC
  [[-80.5, 32.0], [-81.0, 31.0]],                     // GA/SC
  [[-79.8, 39.7], [-75.0, 39.7]],                     // PA/MD
  [[-79.8, 42.3], [-72.0, 42.0]],                     // NY/PA
  // New England
  [[-73.7, 45.0], [-73.2, 42.0], [-71.8, 42.0]],     // VT/NH/MA borders
];

// Major cities for context dots on the map
export const CITIES = [
  { name: 'Seattle', lon: -122.33, lat: 47.61 },
  { name: 'Portland', lon: -122.68, lat: 45.52 },
  { name: 'San Francisco', lon: -122.42, lat: 37.77 },
  { name: 'Los Angeles', lon: -118.24, lat: 34.05 },
  { name: 'Phoenix', lon: -112.07, lat: 33.45 },
  { name: 'Denver', lon: -104.99, lat: 39.74 },
  { name: 'Dallas', lon: -96.80, lat: 32.78 },
  { name: 'Houston', lon: -95.37, lat: 29.76 },
  { name: 'Chicago', lon: -87.63, lat: 41.88 },
  { name: 'Atlanta', lon: -84.39, lat: 33.75 },
  { name: 'Miami', lon: -80.19, lat: 25.76 },
  { name: 'Washington DC', lon: -77.04, lat: 38.91 },
  { name: 'New York', lon: -74.01, lat: 40.71 },
  { name: 'Boston', lon: -71.06, lat: 42.36 },
];
