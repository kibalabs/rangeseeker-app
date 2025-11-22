import { RequestData, ResponseData } from '@kibalabs/core';

import * as Resources from './resources';

export type RawObject = Record<string, unknown>;

export class LoginWithWalletRequest extends RequestData {
  public constructor(
    readonly walletAddress: string,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      walletAddress: this.walletAddress,
    };
  };
}

export class LoginWithWalletResponse extends ResponseData {
  public constructor(
    readonly user: Resources.User,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): LoginWithWalletResponse => {
    return new LoginWithWalletResponse(
      Resources.User.fromObject(obj.user as RawObject),
    );
  };
}

export class CreateUserRequest extends RequestData {
  public constructor(
    readonly walletAddress: string,
    readonly username: string,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      walletAddress: this.walletAddress,
      username: this.username,
    };
  };
}

export class CreateUserResponse extends ResponseData {
  public constructor(
    readonly user: Resources.User,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): CreateUserResponse => {
    return new CreateUserResponse(
      Resources.User.fromObject(obj.user as RawObject),
    );
  };
}

export class ParseStrategyRequest extends RequestData {
  public constructor(
    readonly description: string,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      description: this.description,
    };
  };
}

export class ParseStrategyResponse extends ResponseData {
  public constructor(
    readonly strategyDefinition: Resources.StrategyDefinition,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): ParseStrategyResponse => {
    return new ParseStrategyResponse(
      obj.strategyDefinition as Resources.StrategyDefinition,
    );
  };
}

export class GetPoolDataRequest extends RequestData {
  public constructor(
    readonly chainId: number,
    readonly token0Address: string,
    readonly token1Address: string,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      chainId: this.chainId,
      token0Address: this.token0Address,
      token1Address: this.token1Address,
    };
  };
}

export class GetPoolDataResponse extends ResponseData {
  public constructor(
    readonly poolData: Resources.PoolData,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetPoolDataResponse => {
    return new GetPoolDataResponse(
      obj.poolData as Resources.PoolData,
    );
  };
}

export class GetPoolHistoricalDataRequest extends RequestData {
  public constructor(
    readonly chainId: number,
    readonly token0Address: string,
    readonly token1Address: string,
    readonly hoursBack: number,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      chainId: this.chainId,
      token0Address: this.token0Address,
      token1Address: this.token1Address,
      hoursBack: this.hoursBack,
    };
  };
}

export class GetPoolHistoricalDataResponse extends ResponseData {
  public constructor(
    readonly poolHistoricalData: Resources.PoolHistoricalData,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetPoolHistoricalDataResponse => {
    return new GetPoolHistoricalDataResponse(
      obj.poolHistoricalData as Resources.PoolHistoricalData,
    );
  };
}

export class CreateStrategyRequest extends RequestData {
  public constructor(
    readonly name: string,
    readonly description: string,
    readonly strategyDefinition: Resources.StrategyDefinition,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      name: this.name,
      description: this.description,
      strategyDefinition: this.strategyDefinition,
    };
  };
}

export class CreateStrategyResponse extends ResponseData {
  public constructor(
    readonly strategy: Resources.Strategy,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): CreateStrategyResponse => {
    return new CreateStrategyResponse(
      Resources.Strategy.fromObject(obj.strategy as RawObject),
    );
  };
}

export class ListUserStrategiesResponse extends ResponseData {
  public constructor(
    readonly strategies: Resources.Strategy[],
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): ListUserStrategiesResponse => {
    return new ListUserStrategiesResponse(
      (obj.strategies as RawObject[]).map((strategy: RawObject): Resources.Strategy => Resources.Strategy.fromObject(strategy)),
    );
  };
}

export class GetStrategyResponse extends ResponseData {
  public constructor(
    readonly strategy: Resources.Strategy,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetStrategyResponse => {
    return new GetStrategyResponse(
      Resources.Strategy.fromObject(obj.strategy as RawObject),
    );
  };
}

export class CreateAgentRequest extends RequestData {
  public constructor(
    readonly name: string,
    readonly emoji: string,
    readonly strategyName: string,
    readonly strategyDescription: string,
    readonly strategyDefinition: Resources.StrategyDefinition,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      name: this.name,
      emoji: this.emoji,
      strategyName: this.strategyName,
      strategyDescription: this.strategyDescription,
      strategyDefinition: this.strategyDefinition,
    };
  };
}

export class CreateAgentResponse extends ResponseData {
  public constructor(
    readonly agent: Resources.Agent,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): CreateAgentResponse => {
    return new CreateAgentResponse(
      Resources.Agent.fromObject(obj.agent as RawObject),
    );
  };
}

export class ListAgentsResponse extends ResponseData {
  public constructor(
    readonly agents: Resources.Agent[],
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): ListAgentsResponse => {
    return new ListAgentsResponse(
      (obj.agents as RawObject[]).map((agent: RawObject): Resources.Agent => Resources.Agent.fromObject(agent)),
    );
  };
}

export class GetAgentRequest extends RequestData {
  public constructor(
    readonly agentId: string,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      agentId: this.agentId,
    };
  };
}

export class GetAgentResponse extends ResponseData {
  public constructor(
    readonly agent: Resources.Agent,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetAgentResponse => {
    return new GetAgentResponse(
      Resources.Agent.fromObject(obj.agent as RawObject),
    );
  };
}

export class GetAgentWalletRequest extends RequestData {
  public constructor(
    readonly agentId: string,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      agentId: this.agentId,
    };
  };
}

export class GetAgentWalletResponse extends ResponseData {
  public constructor(
    readonly wallet: Resources.Wallet,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetAgentWalletResponse => {
    return new GetAgentWalletResponse(
      Resources.Wallet.fromObject(obj.wallet as RawObject),
    );
  };
}

export class GetWalletBalancesRequest extends RequestData {
  public constructor(
    readonly chainId: number,
    readonly walletAddress: string,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      chainId: this.chainId,
      walletAddress: this.walletAddress,
    };
  };
}

export class GetWalletBalancesResponse extends ResponseData {
  public constructor(
    readonly balances: Resources.AssetBalance[],
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetWalletBalancesResponse => {
    return new GetWalletBalancesResponse(
      (obj.balances as RawObject[]).map((balance: RawObject): Resources.AssetBalance => Resources.AssetBalance.fromObject(balance)),
    );
  };
}

export class PreviewDepositRequest extends RequestData {
  public constructor(
    readonly agentId: string,
    readonly token0Amount: number,
    readonly token1Amount: number,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      agentId: this.agentId,
      token0Amount: this.token0Amount,
      token1Amount: this.token1Amount,
    };
  };
}

export class PreviewDepositResponse extends ResponseData {
  public constructor(
    readonly preview: Resources.PreviewDeposit,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): PreviewDepositResponse => {
    return new PreviewDepositResponse(
      Resources.PreviewDeposit.fromObject(obj.preview as RawObject),
    );
  };
}

export class DepositMadeToAgentRequest extends RequestData {
  public constructor(
    readonly agentId: string,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      agentId: this.agentId,
    };
  };
}

export class DepositMadeToAgentResponse extends ResponseData {
  public constructor() {
    super();
  }

  public static fromObject = (_obj: RawObject): DepositMadeToAgentResponse => {
    return new DepositMadeToAgentResponse();
  };
}
