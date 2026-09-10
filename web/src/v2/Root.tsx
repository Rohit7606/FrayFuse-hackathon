/**
 * Two screens, one piece of state between them.
 *
 * The build page turns an archive into a scored network; the console reads
 * that network. Which one is showing, and which network the console is reading,
 * is the whole of the state here — there is no router, because there are two
 * screens and a router would be scaffolding.
 *
 * The console runs on the INGESTED network when there is one. That is the point
 * of the upload: a graph built from filings that then gets walked through like
 * any other. It also means the demo's fixed node IDs no longer apply, so the
 * console derives its trigger, its top-ranked supplier and its funding amount
 * from the data it was handed. On the committed network it still reads the
 * fixture, exactly as before.
 */

import { useState } from 'react';
import './console.css';
import BuildPage from './BuildPage';
import Console from './Console';
import type { IngestResponse } from './types';

type View = 'build' | 'console';

export default function Root() {
  const [view, setView] = useState<View>('build');
  const [ingested, setIngested] = useState<IngestResponse | null>(null);

  if (view === 'build') {
    return (
      <BuildPage
        onEnterConsole={(result) => {
          setIngested(result);
          setView('console');
        }}
        // Rehearsal safety (DEMO_SCENARIO.md §9): if the upload fails or is
        // skipped, this drops straight into the console on the committed
        // network. A failed ingest never leaves a blank stage.
        onUseCommittedNetwork={() => {
          setIngested(null);
          setView('console');
        }}
      />
    );
  }

  return <Console ingested={ingested} onBuildPage={() => setView('build')} />;
}
