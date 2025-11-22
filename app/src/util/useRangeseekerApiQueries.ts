import { useQuery, UseQueryResult } from '@tanstack/react-query';

import { PoolData, PoolHistoricalData } from '../client/resources';
import { useGlobals } from '../GlobalsContext';

const SECONDS_IN_MILLIS = 1000;
const MINUTES_IN_SECONDS = 60;

export const usePoolDataQuery = (chainId: number, token0Address: string, token1Address: string, staleSeconds: number = 60 * MINUTES_IN_SECONDS): UseQueryResult<PoolData, Error> => {
  const { rangeSeekerClient } = useGlobals();
  return useQuery({
    queryKey: ['poolData', chainId, token0Address, token1Address],
    queryFn: async (): Promise<PoolData> => {
      return rangeSeekerClient.getPoolData(chainId, token0Address, token1Address);
    },
    staleTime: staleSeconds * SECONDS_IN_MILLIS,
    refetchOnWindowFocus: false,
  });
};

export const usePoolHistoricalDataQuery = (chainId: number, token0Address: string, token1Address: string, hoursBack: number, staleSeconds: number = 60 * MINUTES_IN_SECONDS): UseQueryResult<PoolHistoricalData, Error> => {
  const { rangeSeekerClient } = useGlobals();
  return useQuery({
    queryKey: ['poolHistoricalData', chainId, token0Address, token1Address, hoursBack],
    queryFn: async (): Promise<PoolHistoricalData> => {
      return rangeSeekerClient.getPoolHistoricalData(chainId, token0Address, token1Address, hoursBack);
    },
    staleTime: staleSeconds * SECONDS_IN_MILLIS,
    refetchOnWindowFocus: false,
  });
};
