import { dateFromString } from '@kibalabs/core';

import { RawObject } from './endpoints';

export class User {
  public constructor(
    readonly userId: string,
    readonly username: string,
    readonly createdDate: Date,
    readonly updatedDate: Date,
  ) { }

  public static fromObject = (obj: RawObject): User => {
    return new User(
      String(obj.userId),
      String(obj.username),
      dateFromString(String(obj.createdDate)),
      dateFromString(String(obj.updatedDate)),
    );
  };
}

export interface Agent {
  agentId: string;
  name: string;
  emoji: string;
  ownerId: string;
}

export interface DynamicWidening {
  enabled: boolean;
  volatilityThreshold: number;
  widenToPercent: number;
}

export interface RangeWidthParameters {
  baseRangePercent: number;
  dynamicWidening: DynamicWidening | null;
  rebalanceBuffer: number;
}

export interface PriceThresholdParameters {
  asset: string;
  operator: string;
  priceUsd: number;
  action: string;
  targetAsset: string;
}

export interface VolatilityTriggerParameters {
  threshold: number;
  window: string;
  action: string;
}

export interface StrategyRule {
  type: string;
  priority: number;
  parameters: RangeWidthParameters | PriceThresholdParameters | VolatilityTriggerParameters;
}

export interface StrategyDefinition {
  rules: StrategyRule[];
  feedRequirements: string[];
  summary: string;
}

export interface PoolData {
  chainId: number;
  token0Address: string;
  token1Address: string;
  poolAddress: string;
  currentPrice: number;
  volatility24h: number;
  volatility7d: number;
}

export interface PricePoint {
  timestamp: number;
  price: number;
}

export interface PoolHistoricalData {
  chainId: number;
  token0Address: string;
  token1Address: string;
  poolAddress: string;
  pricePoints: PricePoint[];
}

export class Strategy {
  public constructor(
    readonly strategyId: string,
    readonly userId: string,
    readonly name: string,
    readonly description: string,
    readonly rulesJson: RawObject,
    readonly feedRequirements: string[],
    readonly summary: string,
    readonly createdDate: Date,
    readonly updatedDate: Date,
  ) { }

  public static fromObject = (obj: RawObject): Strategy => {
    return new Strategy(
      String(obj.strategyId),
      String(obj.userId),
      String(obj.name),
      String(obj.description),
      obj.rulesJson as RawObject,
      obj.feedRequirements as string[],
      String(obj.summary),
      dateFromString(String(obj.createdDate)),
      dateFromString(String(obj.updatedDate)),
    );
  };
}
