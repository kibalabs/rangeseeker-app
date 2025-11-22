import { Requester } from '@kibalabs/core';

import { User } from './resources';

export class RangeSeekerClient {
  protected requester: Requester;
  protected baseUrl: string;

  constructor(requester: Requester, baseUrl: string) {
    this.requester = requester;
    this.baseUrl = baseUrl;
  }

  // eslint-disable-next-line class-methods-use-this
  public async loginWithWallet(address: string, _signature: string): Promise<User> {
    // TODO: Implement actual API call
    return Promise.resolve({
      userId: 'user-1',
      username: 'mock-user',
      address,
    });
  }

  // eslint-disable-next-line class-methods-use-this
  public async createUser(address: string, username: string, _signature: string, _referralCode: string | null): Promise<User> {
    // TODO: Implement actual API call
    return Promise.resolve({
      userId: 'user-1',
      username,
      address,
    });
  }
}
