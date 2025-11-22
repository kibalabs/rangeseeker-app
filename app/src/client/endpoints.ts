/* eslint-disable class-methods-use-this */
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
    readonly user: Resources.User | null,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): LoginWithWalletResponse => {
    return new LoginWithWalletResponse(
      obj.user ? Resources.User.fromObject(obj.user as RawObject) : null,
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
