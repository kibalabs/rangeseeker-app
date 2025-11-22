import React, { useEffect, useState } from 'react';

import { KibaException } from '@kibalabs/core';
import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Button, Checkbox, Direction, IconButton, KibaIcon, PaddingSize, ScreenSize, SingleLineInput, Spacing, Stack, Text, TextAlignment, useResponsiveScreenSize } from '@kibalabs/ui-react';
import { useWeb3Account } from '@kibalabs/web3-react';

import { useAuth } from '../AuthContext';

export function RegisterPage(): React.ReactElement {
  const navigator = useNavigator();
  const { createUser, isWeb3AccountLoggedIn, isAuthenticated, logout } = useAuth();
  const account = useWeb3Account();
  const [username, setUsername] = useState<string>('');
  const [isRegistering, setIsRegistering] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasAcceptedTerms, setHasAcceptedTerms] = useState<boolean>(false);
  const responsiveScreenSize = useResponsiveScreenSize();

  useEffect((): void => {
    if (!isWeb3AccountLoggedIn || isAuthenticated) {
      navigator.navigateTo('/');
    }
  }, [navigator, isWeb3AccountLoggedIn, isAuthenticated]);

  const onUsernameChanged = (value: string): void => {
    setUsername(value.trim());
    setError(null);
  };

  const onRegisterClicked = async (): Promise<void> => {
    if (!account) {
      navigator.navigateTo('/');
      return;
    }
    if (!hasAcceptedTerms) {
      setError('Please accept the disclaimer to continue');
      return;
    }
    setIsRegistering(true);
    setError(null);
    try {
      const finalUsername = username || `user_${account.address.substring(2, 15).toLowerCase()}`;
      await createUser(finalUsername);
      navigator.navigateTo('/');
    } catch (caughtError) {
      console.error('Failed to register:', caughtError);
      setError(caughtError instanceof KibaException ? caughtError.message : 'An unknown error occurred. Please try again.');
    } finally {
      setIsRegistering(false);
    }
  };

  const onDisconnectWalletClicked = (): void => {
    logout();
  };

  return (
    <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullHeight={true} isFullWidth={true} isScrollableVertically={true} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Fill} contentAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='600px'>
        <Text variant='header1' alignment={TextAlignment.Center}>Create Your Account</Text>
        <Spacing variant={PaddingSize.Wide} />
        <Stack direction={Direction.Horizontal} shouldAddGutters={true} contentAlignment={Alignment.Center}>
          <Text variant='bold-large'>Welcome to Range Seeker</Text>
        </Stack>
        <Spacing variant={PaddingSize.Wide} />
        <Text alignment={TextAlignment.Center}>Create your account to start using agentic liquidity provision.</Text>
        <Spacing variant={PaddingSize.Wide} />
        {account && (
          <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={false} contentAlignment={Alignment.Start} childAlignment={Alignment.Center}>
            <Text>
              Wallet:
              {account.address.slice(0, 6)}
              ...
              {account.address.slice(-4)}
            </Text>
            {responsiveScreenSize === ScreenSize.Base || responsiveScreenSize === ScreenSize.Small ? (
              <IconButton
                variant='tertiary'
                icon={<KibaIcon iconId='ion-exit-outline' />}
                onClicked={onDisconnectWalletClicked}
              />
            ) : (
              <Button
                variant='tertiary-passive'
                text='Disconnect'
                onClicked={onDisconnectWalletClicked}
              />
            )}
          </Stack>
        )}
        <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true} childAlignment={Alignment.Center}>
          <Text>Username: </Text>
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            <SingleLineInput
              label='Your Username'
              placeholderText='Enter your username (optional)'
              value={username}
              onValueChanged={onUsernameChanged}
            />
          </Stack.Item>
        </Stack>
        <Spacing variant={PaddingSize.Wide} />
        <Checkbox
          isChecked={hasAcceptedTerms}
          onToggled={() => setHasAcceptedTerms(!hasAcceptedTerms)}
          gutter={PaddingSize.Wide}
          text='I have read and accept the disclaimer below'
        />
        <Spacing variant={PaddingSize.Wide} />
        {error && (
          <Text variant='error'>{error}</Text>
        )}
        <Button
          variant='primary'
          text='Create Account'
          onClicked={onRegisterClicked}
          isLoading={isRegistering}
        />
        <Spacing variant={PaddingSize.Default} />
        <Text variant='note'>Disclaimer: I understand that Range Seeker uses AI agents to autonomously provide liquidity in DeFi protocols on my behalf. By using the platform, I authorize the AI agent to execute transactions for me. I acknowledge that DeFi carries inherent risks, including loss of funds due to smart contract vulnerabilities, market volatility, or system errors. By proceeding, I accept full responsibility for the AI agent&apos;s actions and agree that the platform&apos;s creators are not liable for any resulting losses.</Text>
      </Stack>
    </Stack>
  );
}
