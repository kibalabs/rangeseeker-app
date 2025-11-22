import React from 'react';

import { useInitialization, useStringRouteParam } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, InputType, KibaIcon, PaddingSize, SingleLineInput, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import { useWeb3 } from '@kibalabs/web3-react';
// eslint-disable-next-line import/no-extraneous-dependencies
import { ethers } from 'ethers';
import styled from 'styled-components';

import { useAuth } from '../../AuthContext';
import { Agent, PreviewDeposit, Strategy, Wallet } from '../../client/resources';
import { GlassCard } from '../../components/GlassCard';
import { PriceChart } from '../../components/PriceChart';
import { useGlobals } from '../../GlobalsContext';

const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const WETH_ADDRESS = '0x4200000000000000000000000000000000000006';

const StatBox = styled.div`
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  border: 1px solid rgba(255, 255, 255, 0.1);
`;

const ActivityItem = styled.div`
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;

  &:last-child {
    border-bottom: none;
  }
`;

const FlexRow = styled.div`
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  width: 100%;
`;

const IconBox = styled.div`
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: rgba(46, 228, 227, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  border: 1px solid #2EE4E3;
`;

const StatusBadge = styled.div`
  padding: 4px 12px;
  background-color: rgba(46, 228, 227, 0.2);
  border-radius: 20px;
  border: 1px solid rgba(46, 228, 227, 0.5);
`;

const ColoredText = styled.span<{ color: string }>`
  color: ${(props) => props.color};
`;

const ClickableIcon = styled.div`
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.7;
  transition: opacity 0.2s;

  &:hover {
    opacity: 1;
  }
`;

export function DashboardPage(): React.ReactElement {
  const agentId = useStringRouteParam('agentId');
  const { rangeSeekerClient } = useGlobals();
  const { authToken } = useAuth();
  const web3 = useWeb3();
  const [agent, setAgent] = React.useState<Agent | null>(null);
  const [strategy, setStrategy] = React.useState<Strategy | null>(null);
  const [agentWallet, setAgentWallet] = React.useState<Wallet | null>(null);
  const [usdcDepositAmount, setUsdcDepositAmount] = React.useState('');
  const [wethDepositAmount, setWethDepositAmount] = React.useState('');
  const [usdcBalance, setUsdcBalance] = React.useState<string | null>(null);
  const [wethBalance, setWethBalance] = React.useState<string | null>(null);
  const [usdcPrice, setUsdcPrice] = React.useState<number>(0);
  const [wethPrice, setWethPrice] = React.useState<number>(0);
  const [isDepositing, setIsDepositing] = React.useState(false);
  const [depositPreview, setDepositPreview] = React.useState<PreviewDeposit | null>(null);

  useInitialization(() => {
    const init = async () => {
      if (authToken && agentId) {
        const newAgent = await rangeSeekerClient.getAgent(agentId, authToken);
        setAgent(newAgent);
        const newStrategy = await rangeSeekerClient.getStrategy(newAgent.strategyId, authToken);
        setStrategy(newStrategy);
        const newWallet = await rangeSeekerClient.getAgentWallet(agentId, authToken);
        setAgentWallet(newWallet);
      }
    };
    init();
  });

  const fetchBalances = React.useCallback(async () => {
    if (web3) {
      try {
        const signer = await (web3 as ethers.BrowserProvider).getSigner();
        const address = await signer.getAddress();

        const balances = await rangeSeekerClient.getWalletBalances(8453, address);
        const usdc = balances.find((b) => b.asset.address.toLowerCase() === USDC_ADDRESS.toLowerCase());
        const weth = balances.find((b) => b.asset.address.toLowerCase() === WETH_ADDRESS.toLowerCase());

        if (usdc) {
          setUsdcBalance((Number(usdc.balance) / (10 ** usdc.asset.decimals)).toString());
          setUsdcPrice(usdc.assetPrice.priceUsd);
        } else {
          setUsdcBalance('0');
        }

        if (weth) {
          setWethBalance((Number(weth.balance) / (10 ** weth.asset.decimals)).toString());
          setWethPrice(weth.assetPrice.priceUsd);
        } else {
          setWethBalance('0');
        }
      } catch (error) {
        console.error('Failed to fetch balances:', error);
      }
    }
  }, [web3, rangeSeekerClient]);

  React.useEffect(() => {
    fetchBalances();
  }, [fetchBalances]);

  const depositSummary = React.useMemo(() => {
    if (!depositPreview) {
      return null;
    }

    return (
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true}>
        <Text variant='note' alignment={TextAlignment.Center}>
          {depositPreview.swapDescription}
        </Text>
        <Text variant='note' alignment={TextAlignment.Center}>
          {depositPreview.depositDescription}
        </Text>
      </Stack>
    );
  }, [depositPreview]);

  const totalValue = React.useMemo(() => {
    if (!agentWallet) {
      return 0;
    }
    return agentWallet.assetBalances.reduce((acc, balance) => {
      const amount = Number(balance.balance) / (10 ** balance.asset.decimals);
      return acc + (amount * balance.assetPrice.priceUsd);
    }, 0);
  }, [agentWallet]);

  const onDepositClicked = async () => {
    if (!web3 || !agentWallet || (!usdcDepositAmount && !wethDepositAmount)) {
      return;
    }
    setIsDepositing(true);
    try {
      // TODO: Implement deposit logic for both assets
      // const signer = await (web3 as ethers.BrowserProvider).getSigner();
      // ...
      await new Promise((resolve) => { setTimeout(resolve, 1000); }); // Mock delay
      setUsdcDepositAmount('');
      setWethDepositAmount('');
      // eslint-disable-next-line no-alert
      alert('Deposit functionality coming soon!');
    } catch (error) {
      console.error('Deposit failed:', error);
      // eslint-disable-next-line no-alert
      alert('Deposit failed. See console for details.');
    } finally {
      setIsDepositing(false);
    }
  };

  React.useEffect(() => {
    const updatePreview = async () => {
      if (!agentId || !authToken) {
        return;
      }
      const usdc = Number(usdcDepositAmount || 0);
      const weth = Number(wethDepositAmount || 0);
      if (usdc === 0 && weth === 0) {
        setDepositPreview(null);
        return;
      }
      try {
        const preview = await rangeSeekerClient.previewDeposit(agentId, weth, usdc, authToken);
        setDepositPreview(preview);
      } catch (error) {
        console.error(error);
      }
    };
    const timeoutId = setTimeout(updatePreview, 500);
    return (): void => clearTimeout(timeoutId);
  }, [usdcDepositAmount, wethDepositAmount, agentId, authToken, rangeSeekerClient]);

  if (!agent) {
    return (
      <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Center}>
        <Text>Loading agent...</Text>
      </Stack>
    );
  }

  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} isScrollableVertically={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='1000px' isFullWidth={true}>
        <Text variant='header1'>Dashboard</Text>
        <Spacing variant={PaddingSize.Wide} />
        <GlassCard>
          <Stack direction={Direction.Vertical} shouldAddGutters={true} padding={PaddingSize.Wide}>
            <FlexRow>
              <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center}>
                <IconBox>
                  {agent.emoji}
                </IconBox>
                <Stack direction={Direction.Vertical}>
                  <Text variant='header3'>{agent.name}</Text>
                  <Text variant='note'>
                    {strategy ? strategy.summary : 'Loading strategy...'}
                  </Text>
                </Stack>
              </Stack>
              <StatusBadge>
                <Text variant='bold'>
                  <ColoredText color='#2EE4E3'>Active</ColoredText>
                </Text>
              </StatusBadge>
            </FlexRow>
            <Spacing variant={PaddingSize.Default} />
            <Stack direction={Direction.Horizontal} isFullWidth={true} shouldAddGutters={true}>
              <StatBox>
                <Text variant='note'>Total Value</Text>
                <Spacing variant={PaddingSize.Narrow} />
                <Text variant='header2'>
                  $
                  {totalValue.toFixed(2)}
                </Text>
              </StatBox>
              <StatBox>
                <Text variant='note'>Current APY</Text>
                <Spacing variant={PaddingSize.Narrow} />
                <Text variant='header2'>
                  <ColoredText color='#2EE4E3'>0%</ColoredText>
                </Text>
              </StatBox>
              <StatBox>
                <Text variant='note'>Wallet Address</Text>
                <Spacing variant={PaddingSize.Narrow} />
                <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
                  <Text variant='note'>{agentWallet?.walletAddress ? `${agentWallet.walletAddress.slice(0, 6)}...${agentWallet.walletAddress.slice(-4)}` : 'Loading...'}</Text>
                  <KibaIcon iconId='ion-copy-outline' />
                </Stack>
              </StatBox>
            </Stack>
            <Spacing variant={PaddingSize.Wide} />
            <Text variant='header4'>Deposit Funds</Text>
            <GlassCard>
              <Stack direction={Direction.Vertical} padding={PaddingSize.Default} shouldAddGutters={true} maxWidth='400px'>
                <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                  <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
                    <Text variant='bold'>USDC</Text>
                    <ClickableIcon onClick={fetchBalances}>
                      <KibaIcon iconId='ion-refresh' variant='small' />
                    </ClickableIcon>
                  </Stack>
                  <SingleLineInput
                    inputType={InputType.Number}
                    value={usdcDepositAmount}
                    onValueChanged={setUsdcDepositAmount}
                    placeholderText='0.00'
                  />
                  <FlexRow>
                    <Text variant='note'>{`$${(Number(usdcDepositAmount || 0) * usdcPrice).toFixed(2)}`}</Text>
                    <Text variant='note'>{usdcBalance ? `Balance: ${Number(usdcBalance).toFixed(4)}` : 'Loading...'}</Text>
                  </FlexRow>
                </Stack>
                <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                  <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
                    <Text variant='bold'>WETH</Text>
                    <ClickableIcon onClick={fetchBalances}>
                      <KibaIcon iconId='ion-refresh' variant='small' />
                    </ClickableIcon>
                  </Stack>
                  <SingleLineInput
                    inputType={InputType.Number}
                    value={wethDepositAmount}
                    onValueChanged={setWethDepositAmount}
                    placeholderText='0.00'
                  />
                  <FlexRow>
                    <Text variant='note'>
                      $
                      {(Number(wethDepositAmount || 0) * wethPrice).toFixed(2)}
                    </Text>
                    <Text variant='note'>{wethBalance ? `Balance: ${Number(wethBalance).toFixed(4)}` : 'Loading...'}</Text>
                  </FlexRow>
                </Stack>
                {depositSummary && (
                  <React.Fragment>
                    <Spacing variant={PaddingSize.Default} />
                    {depositSummary}
                    <Spacing variant={PaddingSize.Default} />
                  </React.Fragment>
                )}
                <Button
                  variant='primary'
                  text={isDepositing ? 'Depositing...' : 'Deposit'}
                  onClicked={onDepositClicked}
                  isEnabled={!isDepositing && (usdcDepositAmount.length > 0 || wethDepositAmount.length > 0)}
                />
              </Stack>
            </GlassCard>
            <Spacing variant={PaddingSize.Default} />
            <Box width='100%' height='300px'>
              <PriceChart />
            </Box>
            <Spacing variant={PaddingSize.Default} />
            <Text variant='header4'>Recent Activity</Text>
            <Stack direction={Direction.Vertical} isFullWidth={true}>
              <ActivityItem>
                <Stack direction={Direction.Vertical}>
                  <Text variant='bold'>Agent Deployed</Text>
                  <Text variant='note'>Waiting for funds...</Text>
                </Stack>
                <Text variant='note'>Just now</Text>
              </ActivityItem>
            </Stack>
          </Stack>
        </GlassCard>
      </Stack>
    </Stack>
  );
}
