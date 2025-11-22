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
