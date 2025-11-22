import React from 'react';

import { KibaException } from '@kibalabs/core';
import { IMultiAnyChildProps, useDeepCompareMemo } from '@kibalabs/core-react';
import { useWeb3Account, useWeb3LoginSignature } from '@kibalabs/web3-react';

import { User } from './client/resources';
import { useGlobals } from './GlobalsContext';

interface AuthContextType {
  user: User | null | undefined;
  authToken: string | null;
  isWeb3AccountConnecting: boolean;
  isWeb3AccountConnected: boolean;
  isWeb3AccountLoggedIn: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  loginWithWallet: () => Promise<User>;
  createUser: (username: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps extends IMultiAnyChildProps {
}

export function AuthProvider(props: AuthProviderProps): React.ReactElement {
  const { rangeSeekerClient, localStorageClient } = useGlobals();
  const account = useWeb3Account();
  const walletAddress = account?.address;
  const loginSignature = useWeb3LoginSignature();
  const isWeb3AccountConnecting = account === undefined || loginSignature === undefined;
  const isWeb3AccountConnected = account != null;
  const isWeb3AccountLoggedIn = account != null && loginSignature != null;
  const [user, setUser] = React.useState<User | null | undefined>(undefined);
  const isAuthenticated = isWeb3AccountLoggedIn && user != null;
  const isAdmin = user !== null && user !== undefined && (user.username === 'krishan711');

  const authToken = useDeepCompareMemo((): string | null => {
    if (!loginSignature) {
      return null;
    }
    return btoa(JSON.stringify(loginSignature));
  }, [loginSignature]);

  const logout = React.useCallback((): void => {
    localStorageClient.clear();
    setUser(null);
    window.location.reload();
  }, [localStorageClient]);

  const loginWithWallet = React.useCallback(async (): Promise<User> => {
    if (!authToken) {
      throw new KibaException('No authToken available');
    }
    if (!walletAddress) {
      throw new KibaException('No walletAddress available');
    }
    try {
      const newUser = await rangeSeekerClient.loginWithWallet(walletAddress, authToken);
      setUser(newUser);
      return newUser;
    } catch (error) {
      console.error(error);
      if (error instanceof KibaException && error.statusCode === 403) {
        logout();
      }
      throw error;
    }
  }, [rangeSeekerClient, authToken, walletAddress, logout]);

  const createUser = React.useCallback(async (username: string): Promise<User> => {
    if (!authToken) {
      throw new KibaException('No authToken available');
    }
    if (!walletAddress) {
      throw new KibaException('No walletAddress available');
    }
    const newUser = await rangeSeekerClient.createUser(walletAddress, username, authToken);
    setUser(newUser);
    return newUser;
  }, [rangeSeekerClient, authToken, walletAddress]);

  const contextValue = useDeepCompareMemo(() => ({
    user,
    authToken,
    isWeb3AccountConnecting,
    isWeb3AccountConnected,
    isWeb3AccountLoggedIn,
    isAuthenticated,
    isAdmin,
    loginWithWallet,
    createUser,
    logout,
  }), [
    user,
    authToken,
    isWeb3AccountConnecting,
    isWeb3AccountConnected,
    isWeb3AccountLoggedIn,
    isAuthenticated,
    isAdmin,
    loginWithWallet,
    createUser,
    logout,
  ]);

  return (
    <AuthContext.Provider value={contextValue}>
      {props.children}
    </AuthContext.Provider>
  );
}

export const useAuth = (): AuthContextType => {
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
