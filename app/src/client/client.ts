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

  public createUser = async (address: string, username: string, authToken: string, referralCode: string | null): Promise<Resources.User> => {
    const method = RestMethod.POST;
    const path = 'v1/users';
    const request = new Endpoints.CreateUserRequest(address, username);
    const response = await this.makeRequest(method, path, request, Endpoints.CreateUserResponse, this.getHeaders(authToken));
    return response.user;
  };
}
