import React from 'react';

import { IRoute, Router, SubRouter } from '@kibalabs/core-react';
import { KibaApp } from '@kibalabs/ui-react';

import { HomePage } from './pages/HomePage';
import { buildRangeSeekerTheme } from './theme';

const theme = buildRangeSeekerTheme();

const routes: IRoute<void>[] = [
  { path: '/', page: HomePage },
];

export function App() {
  return (
    <KibaApp theme={theme}>
      <Router>
        <SubRouter routes={routes} />
      </Router>
    </KibaApp>
  );
}
