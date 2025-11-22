export interface User {
  userId: string;
  username: string;
  address?: string;
}

export interface Agent {
  agentId: string;
  name: string;
  emoji: string;
  ownerId: string;
}
