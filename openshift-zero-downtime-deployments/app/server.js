const express = require('express');
const app = express();
const PORT = process.env.PORT || 8080;

// Deployment colour set via environment variable
// Set to 'blue' or 'green' in the Deployment manifest
const DEPLOYMENT_COLOUR = process.env.DEPLOYMENT_COLOUR || 'unknown';
const APP_VERSION = process.env.APP_VERSION || '1.0.0';

// Health endpoint — used by smoke tests and OpenShift readiness probe
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'healthy',
    colour: DEPLOYMENT_COLOUR,
    version: APP_VERSION,
    timestamp: new Date().toISOString()
  });
});

// Version endpoint — use this to confirm which deployment is serving traffic
app.get('/version', (req, res) => {
  res.status(200).json({
    colour: DEPLOYMENT_COLOUR,
    version: APP_VERSION,
    hostname: process.env.HOSTNAME || 'unknown',
    timestamp: new Date().toISOString()
  });
});

// Root endpoint
app.get('/', (req, res) => {
  res.status(200).json({
    message: `Hello from the ${DEPLOYMENT_COLOUR} deployment`,
    colour: DEPLOYMENT_COLOUR,
    version: APP_VERSION
  });
});

app.listen(PORT, () => {
  console.log(`[${DEPLOYMENT_COLOUR}] Server running on port ${PORT}`);
  console.log(`[${DEPLOYMENT_COLOUR}] Version: ${APP_VERSION}`);
});
