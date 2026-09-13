import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Root from './v2/Root.tsx'

// Root owns the only stylesheet, src/v2/console.css. The v1 screen and its
// competing design system (src/App.tsx, src/index.css, src/components/) were
// unreachable from here once Root took over, and have been removed rather
// than left to be found and mistaken for live code.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)
