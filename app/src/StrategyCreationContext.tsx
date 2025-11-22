import React from 'react';

import { StrategyDefinition } from './client/resources';

export interface IStrategyCreationContext {
  strategyDefinition: StrategyDefinition | null;
  strategyDescription: string;
  setStrategy: (definition: StrategyDefinition, description: string) => void;
}

export const StrategyCreationContext = React.createContext<IStrategyCreationContext | null>(null);

export function StrategyCreationProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [strategyDefinition, setStrategyDefinition] = React.useState<StrategyDefinition | null>(null);
  const [strategyDescription, setStrategyDescription] = React.useState<string>('');

  const setStrategy = React.useCallback((definition: StrategyDefinition, description: string) => {
    setStrategyDefinition(definition);
    setStrategyDescription(description);
  }, []);

  const value = React.useMemo(() => ({
    strategyDefinition,
    strategyDescription,
    setStrategy,
  }), [strategyDefinition, strategyDescription, setStrategy]);

  return (
    <StrategyCreationContext.Provider value={value}>
      {children}
    </StrategyCreationContext.Provider>
  );
}

export const useStrategyCreation = (): IStrategyCreationContext => {
  const context = React.useContext(StrategyCreationContext);
  if (!context) {
    throw new Error('useStrategyCreation must be used within a StrategyCreationProvider');
  }
  return context;
};
