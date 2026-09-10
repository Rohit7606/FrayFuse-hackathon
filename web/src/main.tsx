import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Root from './v2/Root.tsx'

// Root owns the stylesheet (src/v2/console.css) and neither screen imports
// src/index.css. The two are separate design systems and loading both would
// let the older tokens win on specificity in places.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)
