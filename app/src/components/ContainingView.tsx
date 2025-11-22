import React from 'react';

import { ISingleAnyChildProps, useLocation, useNavigator, usePreviousValue } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, getVariant, HidingView, IconButton, KibaIcon, LinkBase, PaddingSize, ResponsiveHidingView, ScreenSize, Stack, Text } from '@kibalabs/ui-react';
import { useWeb3Account } from '@kibalabs/web3-react';

import { useAuth } from '../AuthContext';
import { useGlobals } from '../GlobalsContext';

interface IMenuViewProps {
  onMenuItemClicked: () => void;
}

function MenuView(props: IMenuViewProps): React.ReactElement {
  const location = useLocation();
  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} isScrollableVertically={true}>
      <Button
        variant={getVariant('sidebar', location.pathname === '/account' && 'sidebarActive')}
        text='Account'
        onClicked={props.onMenuItemClicked}
        target='/account'
        isFullWidth={true}
        contentAlignment={Alignment.Start}
        isTextFullWidth={false}
        iconLeft={<KibaIcon iconId='ion-person-outline' variant='small' />}
      />
      <Button
        variant={getVariant('sidebar', location.pathname === '/agents' && 'sidebarActive')}
        text='Agents'
        onClicked={props.onMenuItemClicked}
        target='/agents'
        isFullWidth={true}
        contentAlignment={Alignment.Start}
        isTextFullWidth={false}
        iconLeft={<KibaIcon iconId='ion-people-outline' variant='small' />}
      />
    </Stack>
  );
}

interface IContainingViewProps extends ISingleAnyChildProps {
  className?: string;
}

export function ContainingView(props: IContainingViewProps): React.ReactElement {
  const location = useLocation();
  const navigator = useNavigator();
  const account = useWeb3Account();
  const previousAccount = usePreviousValue(account);
  const { isWeb3AccountConnecting, isWeb3AccountLoggedIn, isAuthenticated, loginWithWallet } = useAuth();
  const { localStorageClient } = useGlobals();
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [isMenuOpen, setIsMenuOpen] = React.useState<boolean>(false);
  const [loginError, setLoginError] = React.useState<string | null>(null);
  const [needsRegistration, setNeedsRegistration] = React.useState<boolean>(false);
  const [isRestoringDestination, setIsRestoringDestination] = React.useState<boolean>(false);

  React.useEffect((): void => {
    if (previousAccount != null && account?.address !== previousAccount?.address) {
      window.location.reload();
    }
  }, [account, previousAccount]);

  const onMenuItemClicked = (): void => {
    setIsMenuOpen(false);
  };

  const onRetryLoginClicked = (): void => {
    setLoginError(null);
    setIsLoading(false);
  };

  const storeIntendedDestination = React.useCallback((): void => {
    if (location.pathname !== '/') {
      const intendedDestination = {
        pathname: location.pathname,
        search: location.search,
      };
      localStorageClient.setValue('intendedDestination', JSON.stringify(intendedDestination));
    }
  }, [location.pathname, location.search, localStorageClient]);

  const restoreIntendedDestination = React.useCallback((): boolean => {
    const stored = localStorageClient.getValue('intendedDestination');
    if (stored) {
      try {
        const destination = JSON.parse(stored);
        localStorageClient.removeValue('intendedDestination');
        const fullPath = destination.pathname + destination.search;
        setIsRestoringDestination(true);
        navigator.navigateTo(fullPath);
        return true;
      } catch (exception) {
        console.warn('Invalid stored destination:', exception);
        localStorageClient.removeValue('intendedDestination');
      }
    }
    return false;
  }, [localStorageClient, navigator]);

  React.useEffect((): void => {
    if (location.pathname !== '/' && isRestoringDestination) {
      setIsRestoringDestination(false);
    }
    setIsLoading(true);
    const isOnOptionalAuthPage = false;
    // if (location.pathname === '/about') {
    //   isOnOptionalAuthPage = true;
    //   setIsLoading(false);
    // }
    if (isWeb3AccountConnecting) {
      return;
    }
    // NOTE(krishan711): web3 connected but not logged in so need to auth and login
    if (!isWeb3AccountLoggedIn) {
      setIsLoading(false);
      if (!isOnOptionalAuthPage && location.pathname !== '/') {
        storeIntendedDestination();
        navigator.navigateTo('/');
      }
      return;
    }
    if (!isAuthenticated) {
      // NOTE(krishan711): user needs registration
      if (needsRegistration) {
        if (location.pathname !== '/register') {
          navigator.navigateTo('/register');
        }
        setIsLoading(false);
        return;
      }
      // NOTE(krishan711): not authenticated so try login
      if (!loginError) {
        loginWithWallet().catch((error: unknown): void => {
          console.error(`Error during loginWithWallet: ${error}`);
          const errorMessage = error instanceof Error ? error.message : 'Failed to login with wallet';
          if (errorMessage === 'NO_USER') {
            setNeedsRegistration(true);
          } else {
            setLoginError(errorMessage);
            if (location.pathname !== '/') {
              storeIntendedDestination();
              navigator.navigateTo('/');
            }
          }
          setIsLoading(false);
        });
      }
      return;
    }

    // NOTE(krishan711): fully authed so they will see the app
    setNeedsRegistration(false);
    if (location.pathname === '/register') {
      navigator.navigateTo('/');
    }
    setIsLoading(false);
    if (location.pathname === '/') {
      if (!isRestoringDestination && !restoreIntendedDestination()) {
        navigator.navigateTo('/agents');
      }
    }
  }, [navigator, location.pathname, location.search, isWeb3AccountConnecting, isWeb3AccountLoggedIn, isAuthenticated, loginWithWallet, loginError, needsRegistration, isRestoringDestination, restoreIntendedDestination, storeIntendedDestination]);

  const onMenuClicked = (): void => {
    setIsMenuOpen(!isMenuOpen);
  };

  const getPageName = (): string => {
    if (location.pathname === '/agents') {
      return 'Agents';
    }
    if (location.pathname === '/dashboard') {
      return 'Dashboard';
    }
    return '';
  };

  const mainContentView = (
    <Box variant='empty' shouldClipContent={true} isFullHeight={true} isScrollableVertically={false}>
      {isLoading ? (
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true}>
          <Text>Loading...</Text>
        </Stack>
      ) : loginError ? (
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true} shouldAddGutters={true} paddingVertical={PaddingSize.Wide}>
          <Text variant='error'>{`Login Error: ${loginError}`}</Text>
          <Button variant='primary' text='Try Again' onClicked={onRetryLoginClicked} />
        </Stack>
      ) : (
        <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true}>
          <Stack.Item shouldShrinkBelowContentSize={true} growthFactor={1} shrinkFactor={1}>
            <Box shouldClipContent={true} isFullHeight={true} isScrollableVertically={false}>
              {props.children}
            </Box>
          </Stack.Item>
        </Stack>
      )}
    </Box>
  );

  const mobileView = (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} contentAlignment={Alignment.Start} childAlignment={Alignment.Center}>
      {isAuthenticated && location.pathname !== '/' && (
        <Box variant='navBar' zIndex={999} shouldClipContent={true} isFullWidth={true}>
          <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullWidth={true} isFullHeight={false} shouldAddGutters={true}>
            <LinkBase target='/'>
              {/* <Image source='/assets/icon.png' alternativeText='logo' height='32px' fitType='contain' /> */}
              <Text variant='bold'>Range Seeker</Text>
            </LinkBase>
            <Stack.Item growthFactor={1} shrinkFactor={1} shouldShrinkBelowContentSize={true}>
              <Box shouldClipContent={true}>
                <Button variant='navBarLocation' text={getPageName()} onClicked={onMenuClicked} />
              </Box>
            </Stack.Item>
            <IconButton icon={<KibaIcon iconId='ion-menu-outline' />} label='Menu' onClicked={onMenuClicked} />
          </Stack>
        </Box>
      )}
      <Stack.Item growthFactor={1} shrinkFactor={1} shouldShrinkBelowContentSize={true}>
        <HidingView isHidden={!isMenuOpen}>
          <Box variant='navBarMenu' zIndex={1000} isFullHeight={true} shouldClipContent={true}>
            <MenuView
              onMenuItemClicked={onMenuItemClicked}
            />
          </Box>
        </HidingView>
      </Stack.Item>
      <Stack.Item growthFactor={1} shrinkFactor={1} shouldShrinkBelowContentSize={true}>
        <HidingView isHidden={isMenuOpen}>
          {mainContentView}
        </HidingView>
      </Stack.Item>
    </Stack>
  );

  const desktopView = (
    <Stack direction={Direction.Horizontal} childAlignment={Alignment.Start} contentAlignment={Alignment.Fill} shouldAddGutters={false} isFullWidth={true} isFullHeight={true}>
      {isAuthenticated && location.pathname !== '/' && (
        <Box variant='sidebar' width='260px' isFullHeight={true} shouldClipContent={true}>
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Fill} contentAlignment={Alignment.Start} isFullHeight={true} isFullWidth={true}>
            <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} shouldAddGutters={true} paddingHorizontal={PaddingSize.Wide} paddingVertical={PaddingSize.Wide}>
              <LinkBase target='/'>
                {/* <Image source='/assets/icon.png' alternativeText='logo' height='32px' fitType='contain' /> */}
                <Text variant='bold-small-branded'>RANGE SEEKER</Text>
              </LinkBase>
            </Stack>
            <MenuView
              onMenuItemClicked={onMenuItemClicked}
            />
          </Stack>
        </Box>
      )}
      <Stack.Item growthFactor={1} shrinkFactor={1} shouldShrinkBelowContentSize={true}>
        {mainContentView}
      </Stack.Item>
    </Stack>
  );

  return (
    <React.Fragment>
      <Box className={props.className} zIndex={1} position='absolute' isFullWidth={true} isFullHeight={true}>
        <ResponsiveHidingView hiddenAbove={ScreenSize.Medium}>
          {mobileView}
        </ResponsiveHidingView>
        <ResponsiveHidingView hiddenBelow={ScreenSize.Medium}>
          {desktopView}
        </ResponsiveHidingView>
      </Box>
    </React.Fragment>
  );
}
