import { RestMethod, ServiceClient } from '@kibalabs/core';

import * as Endpoints from './endpoints';
import * as Resources from './resources';

export class RangeSeekerClient extends ServiceClient {
  public loginWithWallet = async (address: string, _signature: string): Promise<Resources.User | null> => {
    const method = RestMethod.POST;
    const path = 'v1/users/login-with-wallet';
    const request = new Endpoints.LoginWithWalletRequest(address);
    const response = await this.makeRequest(method, path, request, Endpoints.LoginWithWalletResponse);
    return response.user;
  };

  public createUser = async (address: string, username: string, _signature: string, _referralCode: string | null): Promise<Resources.User> => {
    const method = RestMethod.POST;
    const path = 'v1/users';
    const request = new Endpoints.CreateUserRequest(address, username);
    const response = await this.makeRequest(method, path, request, Endpoints.CreateUserResponse);
    return response.user;
  };
}
