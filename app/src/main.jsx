import "./mobile/fieldNativeDiagnostics.js";
import "./mobile/fieldRuntime.js";
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

import './style.css'
import './responsive.css'
import './pwa.css'

import "./sipucolFinalUi.js";
import "./photoPanelVisualCleanup.js";
import "./hideOnlyPhotoSendBar.js";
import "./clearProjectControl.js";
import "./identityDateTimePersistence.js";
import "./bridgeIdNumericOnly.js";

import './pwaSetup.js'

ReactDOM.createRoot(
  document.getElementById('root')
).render(<App />)