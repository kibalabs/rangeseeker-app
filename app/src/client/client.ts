import { RestMethod, ServiceClient } from '@kibalabs/core';

import * as Endpoints from './endpoints';
import * as Resources from './resources';

export class RangeSeekerClient extends ServiceClient {
  // eslint-disable-next-line class-methods-use-this
  private getHeaders = (authToken: string | null = null): Record<string, string> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (authToken) {
      headers.Authorization = `Signature ${authToken}`;
    }
    return headers;
  };

  public loginWithWallet = async (address: string, authToken: string): Promise<Resources.User> => {
    const method = RestMethod.POST;
    const path = 'v1/users/login-with-wallet';
    const request = new Endpoints.LoginWithWalletRequest(address);
    const response = await this.makeRequest(method, path, request, Endpoints.LoginWithWalletResponse, this.getHeaders(authToken));
    return response.user;
  };

  public createUser = async (address: string, username: string, authToken: string): Promise<Resources.User> => {
    const method = RestMethod.POST;
    const path = 'v1/users';
    const request = new Endpoints.CreateUserRequest(address, username);
    const response = await this.makeRequest(method, path, request, Endpoints.CreateUserResponse, this.getHeaders(authToken));
    return response.user;
  };

  public parseStrategy = async (description: string, authToken: string): Promise<Resources.StrategyDefinition> => {
    const method = RestMethod.POST;
    const path = 'v1/strategies/parse';
    const request = new Endpoints.ParseStrategyRequest(description);
    const response = await this.makeRequest(method, path, request, Endpoints.ParseStrategyResponse, this.getHeaders(authToken));
    return response.strategyDefinition;
  };

  public getPoolData = async (chainId: number, token0Address: string, token1Address: string): Promise<Resources.PoolData> => {
    const method = RestMethod.GET;
    const path = `v1/pools?chainId=${chainId}&token0Address=${token0Address}&token1Address=${token1Address}`;
    const response = await this.makeRequest(method, path, undefined, Endpoints.GetPoolDataResponse, this.getHeaders());
    return response.poolData;
  };

  public getPoolHistoricalData = async (chainId: number, token0Address: string, token1Address: string, hoursBack: number): Promise<Resources.PoolHistoricalData> => {
    const method = RestMethod.GET;
    const path = `v1/pools/historical-data?chainId=${chainId}&token0Address=${token0Address}&token1Address=${token1Address}&hoursBack=${hoursBack}`;
    const response = await this.makeRequest(method, path, undefined, Endpoints.GetPoolHistoricalDataResponse, this.getHeaders());
    return response.poolHistoricalData;
  };

  public createStrategy = async (name: string, description: string, strategyDefinition: Resources.StrategyDefinition, authToken: string): Promise<Resources.Strategy> => {
    const method = RestMethod.POST;
    const path = 'v1/strategies';
    const request = new Endpoints.CreateStrategyRequest(name, description, strategyDefinition);
    const response = await this.makeRequest(method, path, request, Endpoints.CreateStrategyResponse, this.getHeaders(authToken));
    return response.strategy;
  };

  public listUserStrategies = async (authToken: string): Promise<Resources.Strategy[]> => {
    const method = RestMethod.GET;
    const path = 'v1/strategies';
    const response = await this.makeRequest(method, path, undefined, Endpoints.ListUserStrategiesResponse, this.getHeaders(authToken));
    return response.strategies;
  };

  public createAgent = async (name: string, emoji: string, strategyName: string, strategyDescription: string, strategyDefinition: Resources.StrategyDefinition, authToken: string): Promise<Resources.Agent> => {
    const method = RestMethod.POST;
    const path = 'v1/agents';
    const request = new Endpoints.CreateAgentRequest(name, emoji, strategyName, strategyDescription, strategyDefinition);
    const response = await this.makeRequest(method, path, request, Endpoints.CreateAgentResponse, this.getHeaders(authToken));
    return response.agent;
  };
}
