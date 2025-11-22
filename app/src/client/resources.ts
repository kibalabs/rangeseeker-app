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

export class Agent {
  public constructor(
    readonly agentId: string,
    readonly userId: string,
    readonly strategyId: string,
    readonly name: string,
    readonly emoji: string,
    readonly createdDate: Date,
    readonly updatedDate: Date,
  ) { }

  public static fromObject = (obj: RawObject): Agent => {
    return new Agent(
      String(obj.agentId),
      String(obj.userId),
      String(obj.strategyId),
      String(obj.name),
      String(obj.emoji),
      dateFromString(String(obj.createdDate)),
      dateFromString(String(obj.updatedDate)),
    );
  };
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
  feeGrowth7d: number;
  feeRate: number;
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

export class Asset {
  public constructor(
    readonly assetId: string,
    readonly chainId: number,
    readonly address: string,
    readonly name: string,
    readonly symbol: string,
    readonly decimals: number,
    readonly createdDate: Date,
    readonly updatedDate: Date,
  ) { }

  public static fromObject = (obj: RawObject): Asset => {
    return new Asset(
      String(obj.assetId),
      Number(obj.chainId),
      String(obj.address),
      String(obj.name),
      String(obj.symbol),
      Number(obj.decimals),
      dateFromString(String(obj.createdDate)),
      dateFromString(String(obj.updatedDate)),
    );
  };
}

export class AssetPrice {
  public constructor(
    readonly assetPriceId: number,
    readonly assetId: string,
    readonly priceUsd: number,
    readonly date: Date,
    readonly createdDate: Date,
    readonly updatedDate: Date,
  ) { }

  public static fromObject = (obj: RawObject): AssetPrice => {
    return new AssetPrice(
      Number(obj.assetPriceId),
      String(obj.assetId),
      Number(obj.priceUsd),
      dateFromString(String(obj.date)),
      dateFromString(String(obj.createdDate)),
      dateFromString(String(obj.updatedDate)),
    );
  };
}

export class AssetBalance {
  public constructor(
    readonly asset: Asset,
    readonly assetPrice: AssetPrice,
    readonly balance: number,
  ) { }

  public static fromObject = (obj: RawObject): AssetBalance => {
    return new AssetBalance(
      Asset.fromObject(obj.asset as RawObject),
      AssetPrice.fromObject(obj.assetPrice as RawObject),
      Number(obj.balance),
    );
  };
}

export class Wallet {
  public constructor(
    readonly walletAddress: string,
    readonly assetBalances: AssetBalance[],
    readonly delegatedSmartWallet: string | null,
  ) { }

  public static fromObject = (obj: RawObject): Wallet => {
    return new Wallet(
      String(obj.walletAddress),
      (obj.assetBalances as RawObject[]).map((balance: RawObject): AssetBalance => AssetBalance.fromObject(balance)),
      obj.delegatedSmartWallet ? String(obj.delegatedSmartWallet) : null,
    );
  };
}

export class PreviewDeposit {
  public constructor(
    readonly swapDescription: string,
    readonly depositDescription: string,
    readonly token0Amount: number,
    readonly token1Amount: number,
    readonly token0Symbol: string,
    readonly token1Symbol: string,
  ) { }

  public static fromObject = (obj: RawObject): PreviewDeposit => {
    return new PreviewDeposit(
      String(obj.swapDescription),
      String(obj.depositDescription),
      Number(obj.token0Amount),
      Number(obj.token1Amount),
      String(obj.token0Symbol),
      String(obj.token1Symbol),
    );
  };
}
