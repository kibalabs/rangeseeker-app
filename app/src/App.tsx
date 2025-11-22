import React from 'react';

import { IRoute, Router, SubRouter } from '@kibalabs/core-react';
import { KibaApp } from '@kibalabs/ui-react';

import { DashboardPage } from './pages/DashboardPage';
import { DeployPage } from './pages/DeployPage';
import { HomePage } from './pages/HomePage';
import { StrategyPage } from './pages/StrategyPage';
import { AgentsPage } from './pages/AgentsPage';
import { buildRangeSeekerTheme } from './theme';

const theme = buildRangeSeekerTheme();

const routes: IRoute<void>[] = [
  { path: '/agents', page: AgentsPage },
  { path: '/create', page: StrategyPage },
  { path: '/deploy', page: DeployPage },
  { path: '/dashboard', page: DashboardPage },
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
