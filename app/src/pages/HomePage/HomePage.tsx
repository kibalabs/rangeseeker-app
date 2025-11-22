import React from 'react';

import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Dialog, Direction, EqualGrid, getVariant, Image, KibaIcon, PaddingSize, SelectableView, Spacing, Stack, Text, TextAlignment, useColors } from '@kibalabs/ui-react';
import { Eip6963ProviderDetail, useOnLinkWeb3AccountsClicked, useWeb3OnLoginClicked, useWeb3Providers } from '@kibalabs/web3-react';

import { useAuth } from '../../AuthContext';
import { PoolData, PoolHistoricalData, StrategyDefinition } from '../../client/resources';
import { GlowButton } from '../../components/GlowButton';
import { LoadingShimmer } from '../../components/LoadingShimmer';
import { PriceChart } from '../../components/PriceChart';
import { useGlobals } from '../../GlobalsContext';

const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const WETH_ADDRESS = '0x4200000000000000000000000000000000000006';

const EXAMPLE_STRATEGY_TEXT = 'I want tight range fee farming but widen if volatility spikes, and exit entirely to USDC if ETH ever drops below $3000';

const EXAMPLE_STRATEGY_DEFINITION: StrategyDefinition = {
  rules: [
    {
      type: 'RANGE_WIDTH',
      priority: 3,
      parameters: {
        baseRangePercent: 2.0,
        dynamicWidening: {
          enabled: true,
          volatilityThreshold: 0.05,
          widenToPercent: 5.0,
        },
        rebalanceBuffer: 0.1,
      },
    },
    {
      type: 'PRICE_THRESHOLD',
      priority: 1,
      parameters: {
        asset: 'WETH',
        operator: 'LESS_THAN',
        priceUsd: 3000.0,
        action: 'EXIT_TO_STABLE',
        targetAsset: 'USDC',
      },
    },
    {
      type: 'VOLATILITY_TRIGGER',
      priority: 2,
      parameters: {
        threshold: 0.05,
        window: '24h',
        action: 'WIDEN_RANGE',
      },
    },
  ],
  feedRequirements: ['PYTH_PRICE', 'THEGRAPH_VOLATILITY'],
  summary: 'Maintain ±2% range, widen to ±5% if volatility > 5%, exit to USDC if WETH below $3,000',
};

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
  const colors = useColors();
  const { rangeSeekerClient } = useGlobals();
  const { isWeb3AccountConnected, isWeb3AccountLoggedIn } = useAuth();
  const [web3Providers, chooseEip1193Provider] = useWeb3Providers();
  const onLinkAccountsClicked = useOnLinkWeb3AccountsClicked();
  const onAccountLoginClicked = useWeb3OnLoginClicked();
  const [isLoggingIn, setIsLoggingIn] = React.useState<boolean>(false);
  const [isProviderDialogOpen, setIsProviderDialogOpen] = React.useState(false);
  const [poolData, setPoolData] = React.useState<PoolData | null>(null);
  const [historicalData, setHistoricalData] = React.useState<PoolHistoricalData | null>(null);

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

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const [pool, historical] = await Promise.all([
          rangeSeekerClient.getPoolData(8453, WETH_ADDRESS, USDC_ADDRESS),
          rangeSeekerClient.getPoolHistoricalData(8453, WETH_ADDRESS, USDC_ADDRESS, 24),
        ]);
        setPoolData(pool);
        setHistoricalData(historical);
      } catch (error) {
        console.error('Failed to fetch pool data:', error);
      }
    };
    fetchData();
  }, [rangeSeekerClient]);

  return (
    <React.Fragment>
      <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} isScrollableVertically={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='1200px' isFullWidth={true}>
          <Spacing variant={PaddingSize.Wide} />
          <Image source='/assets/logo.svg' alternativeText='Range Seeker' height='80px' />
          <Image source='/assets/wordmark.svg' alternativeText='Range Seeker' height='80px' />
          <Text variant='header2' alignment={TextAlignment.Center}>Agentic Liquidity Provision</Text>
          <Spacing variant={PaddingSize.Wide2} />
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='800px'>
            <Text variant='large' alignment={TextAlignment.Center}>
              <b>Concentrated liquidity provision is hard.</b>
              {' '}
              It&apos;s inhumane to expect anyone to monitor prices 24/7, rebalance positions manually, and calculate optimal ranges in their head.
            </Text>
            <Spacing variant={PaddingSize.Default} />
            <Text variant='large' alignment={TextAlignment.Center}>
              That&apos;s why we built
              <b>Range Seeker</b>
              {' '}
              — AI agents that manage your Uniswap V3 positions automatically, following strategies you define in plain English.
            </Text>
          </Stack>
          <Spacing variant={PaddingSize.Wide2} />
          {!isWeb3AccountConnected ? (
            <GlowButton variant='large-primary' text='Connect Wallet to Get Started' onClicked={onConnectWalletClicked} />
          ) : !isWeb3AccountLoggedIn ? (
            <GlowButton variant='large-primary' text='Sign to Log In' onClicked={onLoginClicked} isLoading={isLoggingIn} />
          ) : isLoggingIn ? (
            <Text>Please check your wallet to sign the login message</Text>
          ) : (
            <GlowButton variant='large-primary' text='Launch App' onClicked={(): void => navigator.navigateTo('/agents')} />
          )}
          <Spacing variant={PaddingSize.Wide3} />
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} isFullWidth={true}>
            <Text variant='header3' alignment={TextAlignment.Center}>See it in action</Text>
            <Text alignment={TextAlignment.Center}>Here&apos;s an example strategy and its performance on the WETH/USDC pool</Text>
          </Stack>
          <Text variant='large' alignment={TextAlignment.Left}>
            &quot;
            {EXAMPLE_STRATEGY_TEXT}
            &quot;
          </Text>
          <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center}>
            <KibaIcon iconId='ion-caret-forward-circle' _color={colors.brandPrimary} />
            <Text>{EXAMPLE_STRATEGY_DEFINITION.summary}</Text>
          </Stack>
          <Spacing variant={PaddingSize.Default} />
          <Box width='100%' height='450px'>
            {historicalData && poolData ? (
              <PriceChart
                priceData={historicalData.pricePoints.map((point) => ({
                  timestamp: point.timestamp,
                  price: point.price,
                }))}
                strategyDefinition={EXAMPLE_STRATEGY_DEFINITION}
                currentPrice={poolData.currentPrice}
              />
            ) : (
              <LoadingShimmer width='100%' height='100%' />
            )}
          </Box>
          <Spacing variant={PaddingSize.Default} />
          <EqualGrid childSizeResponsive={{ base: 12, medium: 6, large: 4 }} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={false}>
            <Box variant='card'>
              <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} padding={PaddingSize.Wide} isFullWidth={true} shouldAddGutters={true}>
                {poolData ? (
                  <Text variant='large-bold-branded'>
                    $
                    {poolData.currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </Text>
                ) : (
                  <LoadingShimmer width='140px' height='32px' />
                )}
                <Text>Current ETH Price</Text>
              </Stack>
            </Box>
            <Box variant='card'>
              <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} padding={PaddingSize.Wide} isFullWidth={true} shouldAddGutters={true}>
                {poolData ? (
                  <Text variant='large-bold-branded'>
                    {(poolData.volatility24h * 100).toFixed(2)}
                    %
                  </Text>
                ) : (
                  <LoadingShimmer width='80px' height='32px' />
                )}
                <Text>24h Volatility</Text>
              </Stack>
            </Box>
            <Box variant='card'>
              <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} padding={PaddingSize.Wide} isFullWidth={true} shouldAddGutters={true}>
                {poolData ? (
                  <Text variant='large-bold-branded'>
                    {(poolData.feeRate * poolData.volatility24h * 365 * 100 * 0.8).toFixed(1)}
                    %-
                    {(poolData.feeRate * poolData.volatility24h * 365 * 100 * 1.5).toFixed(1)}
                    %
                  </Text>
                ) : (
                  <LoadingShimmer width='120px' height='32px' />
                )}
                <Text>Projected APY Range</Text>
              </Stack>
            </Box>
          </EqualGrid>
          <Spacing variant={PaddingSize.Wide3} />
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true}>
            <Text variant='header3' alignment={TextAlignment.Center}>Ready to automate your liquidity?</Text>
            <Spacing variant={PaddingSize.Wide2} />
            {!isWeb3AccountConnected ? (
              <GlowButton variant='large-primary' text='Connect Wallet' onClicked={onConnectWalletClicked} />
            ) : !isWeb3AccountLoggedIn ? (
              <GlowButton variant='large-primary' text='Sign to Log In' onClicked={onLoginClicked} isLoading={isLoggingIn} />
            ) : (
              <GlowButton variant='large-primary' text='Create Your First Agent' onClicked={() => navigator.navigateTo('/agents')} />
            )}
          </Stack>
          <Spacing variant={PaddingSize.Wide2} />
        </Stack>
      </Stack>
      <ProviderDialog
        isOpen={isProviderDialogOpen}
        providers={web3Providers}
        onProviderSelected={onProviderSelected}
        onClose={(): void => setIsProviderDialogOpen(false)}
      />
    </React.Fragment>
  );
}
