import React from 'react';

import { createRoot, hydrateRoot } from 'react-dom/client';

import { App } from './App';

// @ts-expect-error
const renderedPath = window.KIBA_RENDERED_PATH;

if (typeof document !== 'undefined') {
  const target = document.getElementById('root') as HTMLElement;
  const rootNode = (
    <React.StrictMode><App /></React.StrictMode>
  );
  if (target.hasChildNodes() && window.location.pathname === renderedPath) {
    hydrateRoot(target, rootNode);
  } else {
    const root = createRoot(target);
    root.render(rootNode);
  }
}
