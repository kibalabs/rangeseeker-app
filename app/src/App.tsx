import React from 'react';

import { LocalStorageClient, Requester } from '@kibalabs/core';
import { IRoute, MockStorage, Router, SubRouter } from '@kibalabs/core-react';
import { ComponentDefinition, KibaApp } from '@kibalabs/ui-react';
import { buildToastThemes, Toast, ToastContainer, ToastThemedStyle, useToastManager } from '@kibalabs/ui-react-toast';
import { Web3AccountControlProvider } from '@kibalabs/web3-react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

import { AuthProvider } from './AuthContext';
import { RangeSeekerClient } from './client/client';
import { AnimatedBackground } from './components/AnimatedBackground';
import { ContainingView } from './components/ContainingView';
import { GlobalsProvider, IGlobals } from './GlobalsContext';
import { AccountPage } from './pages/AccountPage';
import { AgentsPage } from './pages/AgentsPage';
import { DashboardPage } from './pages/DashboardPage';
import { DeployPage } from './pages/DeployPage';
import { HomePage } from './pages/HomePage';
import { RegisterPage } from './pages/RegisterPage';
import { StrategyPage } from './pages/StrategyPage';
import { StrategyCreationProvider } from './StrategyCreationContext';
import { buildRangeSeekerTheme } from './theme';

declare global {
  export interface Window {
    KRT_API_URL?: string;
    KRT_IS_NEXT?: string;
  }
}

const requester = new Requester();
const baseUrl = typeof window !== 'undefined' && window.KRT_API_URL ? window.KRT_API_URL : 'https://rangeseeker-api.tokenpage.xyz';
const rangeSeekerClient = new RangeSeekerClient(requester, baseUrl);
const localStorageClient = new LocalStorageClient(typeof window !== 'undefined' ? window.localStorage : new MockStorage());
const sessionStorageClient = new LocalStorageClient(typeof window !== 'undefined' ? window.sessionStorage : new MockStorage());
const theme = buildRangeSeekerTheme();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      retry: (failureCount: number, error: Error): boolean => {
        if (error instanceof Error && (error.message.includes('401') || error.message.includes('403'))) {
          return false;
        }
        return failureCount < 3;
      },
      refetchOnWindowFocus: true,
      refetchOnReconnect: false,
    },
  },
});

const globals: IGlobals = {
  requester,
  localStorageClient,
  sessionStorageClient,
  rangeSeekerClient,
};

const routes: IRoute<IGlobals>[] = [
  { path: '/account', page: AccountPage },
  { path: '/agents', page: AgentsPage },
  { path: '/agents/:agentId', page: DashboardPage },
  { path: '/create', page: StrategyPage },
  { path: '/deploy', page: DeployPage },
  { path: '/register', page: RegisterPage },
  { path: '/', page: HomePage },
];

// @ts-expect-error
const extraComponentDefinitions: ComponentDefinition[] = [{
  component: Toast,
  themeMap: buildToastThemes(theme.colors, theme.dimensions, theme.boxes, theme.texts, theme.icons),
  themeCssFunction: ToastThemedStyle,
}];

export function App(): React.ReactElement {
  const toastManager = useToastManager();

  const onWeb3AccountError = React.useCallback((error: Error): void => {
    toastManager.showTextToast(error.message, 'error');
  }, [toastManager]);

  return (
    <KibaApp theme={theme} isFullPageApp={true} extraComponentDefinitions={extraComponentDefinitions}>
      <AnimatedBackground />
      <GlobalsProvider globals={globals}>
        <QueryClientProvider client={queryClient}>
          <Router>
            <Web3AccountControlProvider localStorageClient={localStorageClient} onError={onWeb3AccountError}>
              <AuthProvider>
                <StrategyCreationProvider>
                  <ContainingView>
                    <SubRouter routes={routes} />
                  </ContainingView>
                </StrategyCreationProvider>
              </AuthProvider>
              <ToastContainer />
            </Web3AccountControlProvider>
          </Router>
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      </GlobalsProvider>
    </KibaApp>
  );
}
