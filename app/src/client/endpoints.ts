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
