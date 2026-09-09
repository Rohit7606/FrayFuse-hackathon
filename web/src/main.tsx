import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Console from './v2/Console.tsx'

// The v2 console owns its own stylesheet (src/v2/console.css) and does not
// import src/index.css. The two are separate design systems and loading both
// would let the older tokens win on specificity in places.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Console />
  </StrictMode>,
)
