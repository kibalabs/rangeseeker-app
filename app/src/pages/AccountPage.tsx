import React from 'react';

import { Alignment, Box, Button, Direction, PaddingSize, Spacing, Stack, Text } from '@kibalabs/ui-react';
import { useWeb3Account } from '@kibalabs/web3-react';

import { useAuth } from '../AuthContext';

export function AccountPage(): React.ReactElement {
  const { user, logout } = useAuth();
  const account = useWeb3Account();

  const onLogoutClicked = (): void => {
    logout();
  };

  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide} isScrollableVertically={true}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Fill} shouldAddGutters={true} maxWidth='800px' isFullWidth={true}>
        <Text variant='header1'>Account</Text>
        <Spacing variant={PaddingSize.Wide} />

        <Box variant='card' isFullWidth={true}>
          <Stack direction={Direction.Vertical} shouldAddGutters={true} padding={PaddingSize.Wide}>
            <Text variant='header3'>Profile</Text>
            <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center}>
              <Text variant='bold'>Username:</Text>
              <Text>{user?.username}</Text>
            </Stack>
            <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center}>
              <Text variant='bold'>User ID:</Text>
              <Text variant='note'>{user?.userId}</Text>
            </Stack>
            {account && (
              <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center}>
                <Text variant='bold'>Wallet:</Text>
                <Text variant='note'>{account.address}</Text>
              </Stack>
            )}
          </Stack>
        </Box>

        <Spacing variant={PaddingSize.Wide} />

        <Box variant='card' isFullWidth={true}>
          <Stack direction={Direction.Vertical} shouldAddGutters={true} padding={PaddingSize.Wide}>
            <Text variant='header3'>Account Actions</Text>
            <Button
              variant='error'
              text='Logout'
              onClicked={onLogoutClicked}
            />
          </Stack>
        </Box>
      </Stack>
    </Stack>
  );
}
