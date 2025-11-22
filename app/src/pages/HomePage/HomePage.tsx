import React from 'react';

import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Dialog, Direction, getVariant, Image, KibaIcon, PaddingSize, SelectableView, Spacing, Stack, Text, TextAlignment, useColors } from '@kibalabs/ui-react';
import { Eip6963ProviderDetail, useOnLinkWeb3AccountsClicked, useWeb3OnLoginClicked, useWeb3Providers } from '@kibalabs/web3-react';

import { useAuth } from '../../AuthContext';
import { GlassCard } from '../../components/GlassCard';
import { PriceChart } from '../../components/PriceChart';

interface IProviderDialogProps {
  isOpen: boolean;
  providers: Eip6963ProviderDetail[];
  onProviderSelected: (provider: Eip6963ProviderDetail) => void;
  onClose: () => void;
}

function ProviderDialog(props: IProviderDialogProps): React.ReactElement {
  const colors = useColors();
  const hasProviders = props.providers.length > 0;
  return (
    <Dialog
      isOpen={props.isOpen}
      onCloseClicked={props.onClose}
      isClosableByBackdrop={true}
      isClosableByEscape={true}
      maxWidth='calc(min(90%, 600px))'
      maxHeight='90%'
    >
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} paddingHorizontal={PaddingSize.Wide} paddingVertical={PaddingSize.Wide}>
        <Text variant='header2' alignment={TextAlignment.Center}>Connect Wallet</Text>
        <Spacing />
        {hasProviders && (
          <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullWidth={true} maxWidth='400px'>
            {props.providers.map((provider: Eip6963ProviderDetail): React.ReactElement => (
              <SelectableView
                key={provider.info.uuid}
                onClicked={(): void => props.onProviderSelected(provider)}
                isSelected={false}
                isFullWidth={true}
              >
                <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullWidth={true}>
                  <Box width='2.5rem' height='2.5rem'>
                    <Image
                      source={provider.info.icon}
                      alternativeText={`${provider.info.name} icon`}
                      isFullWidth={true}
                      isFullHeight={true}
                    />
                  </Box>
                  <Spacing variant={PaddingSize.Wide} />
                  <Stack.Item growthFactor={1} shrinkFactor={1}>
                    <Stack direction={Direction.Vertical} childAlignment={Alignment.Start} isFullWidth={true}>
                      <Text variant={getVariant(provider.info.uuid !== 'ethers' && 'bold')}>{provider.info.name}</Text>
                      {provider.info.uuid !== 'ethers' && (
                        <Text variant='note'>Installed</Text>
                      )}
                    </Stack>
                  </Stack.Item>
                  <Spacing variant={PaddingSize.Wide} />
                  <KibaIcon
                    iconId='ion-arrow-forward'
                    _color={provider.info.uuid !== 'ethers' ? colors.backgroundLight95 : colors.backgroundLight75}
                  />
                </Stack>
              </SelectableView>
            ))}
          </Stack>
        )}
        {!hasProviders && (
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true}>
            <Spacing />
            <Text alignment={TextAlignment.Center}>You don&apos;t have any Web3 wallets installed.</Text>
            <Spacing />
            <Text alignment={TextAlignment.Center}>A Web3 wallet lets you securely store, send, and receive crypto assets.</Text>
            <Spacing />
            <Button target='https://blog.thirdweb.com/web3-wallet/' text='What is a Web3 wallet?' />
          </Stack>
        )}
        <Spacing />
        <Button variant='tertiary-passive' text='Cancel' onClicked={props.onClose} />
      </Stack>
    </Dialog>
  );
}

export function HomePage(): React.ReactElement {
  const navigator = useNavigator();
  const { isWeb3AccountConnected, isWeb3AccountLoggedIn } = useAuth();
  const [web3Providers, chooseEip1193Provider] = useWeb3Providers();
  const onLinkAccountsClicked = useOnLinkWeb3AccountsClicked();
  const onAccountLoginClicked = useWeb3OnLoginClicked();
  const [isLoggingIn, setIsLoggingIn] = React.useState<boolean>(false);
  const [isProviderDialogOpen, setIsProviderDialogOpen] = React.useState(false);

  const onConnectWalletClicked = async (): Promise<void> => {
    const accountsLinked = await onLinkAccountsClicked();
    if (!accountsLinked) {
      setIsProviderDialogOpen(true);
    }
  };

  const onProviderSelected = React.useCallback(async (provider: Eip6963ProviderDetail): Promise<void> => {
    chooseEip1193Provider(provider.info.rdns);
    setIsProviderDialogOpen(false);
    await onLinkAccountsClicked();
  }, [chooseEip1193Provider, onLinkAccountsClicked]);

  const onLoginClicked = async (): Promise<void> => {
    setIsLoggingIn(true);
    await onAccountLoginClicked('I have read and agree to the Range Seeker Terms of Service');
    setIsLoggingIn(false);
  };

  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='1000px' isFullWidth={true}>
        <Text variant='header1' alignment={TextAlignment.Center}>Range Seeker</Text>
        <Text variant='large' alignment={TextAlignment.Center}>Agentic Liquidity Provision</Text>

        <Box width='100%' height='400px'>
          <PriceChart />
        </Box>

        <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Center}>
          <GlassCard width='200px'>
            <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} padding={PaddingSize.Wide}>
              <Text variant='note'>Current Price</Text>
              <Text variant='header2'>$3,427</Text>
            </Stack>
          </GlassCard>
          <GlassCard width='200px'>
            <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} padding={PaddingSize.Wide}>
              <Text variant='note'>24h Volatility</Text>
              <Text variant='header2'>4.1%</Text>
            </Stack>
          </GlassCard>
          <GlassCard width='200px'>
            <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} padding={PaddingSize.Wide}>
              <Text variant='note'>Fees Earned (24h)</Text>
              <Text variant='header2'>$124.50</Text>
            </Stack>
          </GlassCard>
        </Stack>

        <Spacing variant={PaddingSize.Wide} />

        {!isWeb3AccountConnected ? (
          <Button variant='primary' text='Connect Wallet' onClicked={onConnectWalletClicked} />
        ) : !isWeb3AccountLoggedIn ? (
          <Button variant='primary' text='Sign to log in' onClicked={onLoginClicked} isLoading={isLoggingIn} />
        ) : isLoggingIn ? (
          <Text>Please check your wallet to sign the login message</Text>
        ) : (
          <Button variant='primary' text='Go to Agents' onClicked={() => navigator.navigateTo('/agents')} />
        )}
      </Stack>
      <ProviderDialog
        isOpen={isProviderDialogOpen}
        providers={web3Providers}
        onProviderSelected={onProviderSelected}
        onClose={(): void => setIsProviderDialogOpen(false)}
      />
    </Stack>
  );
}
