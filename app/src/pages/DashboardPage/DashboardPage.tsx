import React from 'react';

import { useInitialization, useStringRouteParam } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, EqualGrid, IconButton, InputType, KibaIcon, PaddingSize, SingleLineInput, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import { useOnSwitchToWeb3ChainIdClicked, useWeb3, useWeb3ChainId } from '@kibalabs/web3-react';
// eslint-disable-next-line import/no-extraneous-dependencies
import { ethers } from 'ethers';
import styled from 'styled-components';

import { useAuth } from '../../AuthContext';
import { Agent, PreviewDeposit, Strategy, Wallet } from '../../client/resources';
import { LoadingShimmer } from '../../components/LoadingShimmer';
import { PriceChart } from '../../components/PriceChart';
import { useGlobals } from '../../GlobalsContext';

const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const WETH_ADDRESS = '0x4200000000000000000000000000000000000006';
const BASE_CHAIN_ID = 8453;

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
  const chainId = useWeb3ChainId();
  const onSwitchToWeb3ChainIdClicked = useOnSwitchToWeb3ChainIdClicked();
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
  const [depositError, setDepositError] = React.useState<string | null>(null);
  const [depositSteps, setDepositSteps] = React.useState<Array<{ label: string; status: 'pending' | 'loading' | 'success' | 'error' }>>([]);
  const [isRebalancing, setIsRebalancing] = React.useState(false);
  const [agentEthBalance, setAgentEthBalance] = React.useState<bigint>(BigInt(0));

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

  const fetchAgentEthBalance = React.useCallback(async () => {
    if (web3 && agentWallet) {
      try {
        const provider = web3 as ethers.BrowserProvider;
        const balance = await provider.getBalance(agentWallet.walletAddress);
        setAgentEthBalance(balance);
      } catch (error) {
        console.error('Failed to fetch agent ETH balance:', error);
      }
    }
  }, [web3, agentWallet]);

  React.useEffect(() => {
    fetchAgentEthBalance();
  }, [fetchAgentEthBalance]);

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
    const assetValue = agentWallet.assetBalances.reduce((acc, balance) => {
      const amount = Number(balance.balance) / (10 ** balance.asset.decimals);
      return acc + (amount * balance.assetPrice.priceUsd);
    }, 0);
    const positionsValue = agentWallet.uniswapPositions.reduce((acc: number, position) => {
      return acc + position.totalValueUsd;
    }, 0);
    return assetValue + positionsValue;
  }, [agentWallet]);

  const onRebalanceClicked = async () => {
    if (!authToken || !agentId) {
      return;
    }

    setIsRebalancing(true);
    setDepositError(null);
    try {
      await rangeSeekerClient.depositMadeToAgent(agentId, authToken);

      // Refresh agent wallet
      const newWallet = await rangeSeekerClient.getAgentWallet(agentId, authToken);
      setAgentWallet(newWallet);

      setIsRebalancing(false);
    } catch (error) {
      console.error('Failed to rebalance:', error);
      setDepositError(error instanceof Error ? error.message : 'Rebalance failed. Please try again.');
      setIsRebalancing(false);
    }
  };

  const onDepositClicked = async () => {
    if (!web3 || !agentWallet || (!usdcDepositAmount && !wethDepositAmount) || !authToken || !agentId) {
      return;
    }

    // Check if agent needs ETH for gas
    const minEthBalance = ethers.parseEther('0.0005');
    const ethToDeposit = agentEthBalance < minEthBalance ? ethers.parseEther('0.001') : BigInt(0);

    // Build steps list
    const steps: Array<{ label: string; status: 'pending' | 'loading' | 'success' | 'error' }> = [];
    if (ethToDeposit > BigInt(0)) {
      steps.push({ label: 'Send 0.001 ETH for gas', status: 'pending' });
    }
    if (usdcDepositAmount && Number(usdcDepositAmount) > 0) {
      steps.push({ label: `Send ${usdcDepositAmount} USDC`, status: 'pending' });
    }
    if (wethDepositAmount && Number(wethDepositAmount) > 0) {
      steps.push({ label: `Send ${wethDepositAmount} WETH`, status: 'pending' });
    }
    steps.push({ label: 'Rebalance liquidity', status: 'pending' });
    setDepositSteps(steps);

    setIsDepositing(true);
    setDepositError(null);
    try {
      const signer = await (web3 as ethers.BrowserProvider).getSigner();
      let currentStepIndex = 0;

      // ETH transfer for gas
      if (ethToDeposit > BigInt(0)) {
        setDepositSteps((prev) => prev.map((s, i) => (i === currentStepIndex ? { ...s, status: 'loading' } : s)));
        try {
          const tx = await signer.sendTransaction({
            to: agentWallet.walletAddress,
            value: ethToDeposit,
          });
          await tx.wait();
          setDepositSteps((prev) => prev.map((s, i) => (i === currentStepIndex ? { ...s, status: 'success' } : s)));
          currentStepIndex += 1;
        } catch (error) {
          setDepositSteps((prev) => prev.map((s, i) => (i === currentStepIndex ? { ...s, status: 'error' } : s)));
          throw error;
        }
      }

      // USDC transfer
      if (usdcDepositAmount && Number(usdcDepositAmount) > 0) {
        setDepositSteps((prev) => prev.map((s, i) => (i === currentStepIndex ? { ...s, status: 'loading' } : s)));
        try {
          const ERC20_ABI = ['function transfer(address to, uint256 amount) public returns (bool)'];
          const usdcContract = new ethers.Contract(USDC_ADDRESS, ERC20_ABI, signer);
          const usdcAmountWei = BigInt((Number(usdcDepositAmount) * 10 ** 6).toFixed(0));
          const usdcTx = await usdcContract.transfer(agentWallet.walletAddress, usdcAmountWei);
          await usdcTx.wait();
          setDepositSteps((prev) => prev.map((s, i) => (i === currentStepIndex ? { ...s, status: 'success' } : s)));
          currentStepIndex += 1;
        } catch (error) {
          setDepositSteps((prev) => prev.map((s, i) => (i === currentStepIndex ? { ...s, status: 'error' } : s)));
          throw error;
        }
      }

      // WETH transfer
      if (wethDepositAmount && Number(wethDepositAmount) > 0) {
        setDepositSteps((prev) => prev.map((s, i) => (i === currentStepIndex ? { ...s, status: 'loading' } : s)));
        try {
          const ERC20_ABI = ['function transfer(address to, uint256 amount) public returns (bool)'];
          const wethContract = new ethers.Contract(WETH_ADDRESS, ERC20_ABI, signer);
          const wethAmountWei = ethers.parseEther(wethDepositAmount);
          const wethTx = await wethContract.transfer(agentWallet.walletAddress, wethAmountWei);
          await wethTx.wait();
          setDepositSteps((prev) => prev.map((s, i) => (i === currentStepIndex ? { ...s, status: 'success' } : s)));
          currentStepIndex += 1;
        } catch (error) {
          setDepositSteps((prev) => prev.map((s, i) => (i === currentStepIndex ? { ...s, status: 'error' } : s)));
          throw error;
        }
      }

      // Notify backend and rebalance
      setDepositSteps((prev) => prev.map((s, i) => (i === currentStepIndex ? { ...s, status: 'loading' } : s)));
      try {
        await rangeSeekerClient.depositMadeToAgent(agentId, authToken);
        setDepositSteps((prev) => prev.map((s, i) => (i === currentStepIndex ? { ...s, status: 'success' } : s)));

        setUsdcDepositAmount('');
        setWethDepositAmount('');

        // Refresh balances
        await fetchBalances();

        // Reload agent wallet
        const newWallet = await rangeSeekerClient.getAgentWallet(agentId, authToken);
        setAgentWallet(newWallet);

        // Clear steps after a delay
        setTimeout(() => {
          setDepositSteps([]);
          setIsDepositing(false);
        }, 2000);
      } catch (error) {
        setDepositSteps((prev) => prev.map((s, i) => (i === currentStepIndex ? { ...s, status: 'error' } : s)));
        throw error;
      }
    } catch (error) {
      console.error('Deposit failed:', error);
      setDepositError(error instanceof Error ? error.message : 'Deposit failed. Please try again.');
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
        <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true} childAlignment={Alignment.Start}>
          <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center}>
            <IconBox>{agent.emoji}</IconBox>
            <Stack direction={Direction.Vertical}>
              <Text variant='header3'>{agent.name}</Text>
              {agentWallet?.walletAddress ? (
                <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true} contentAlignment={Alignment.Start}>
                  <Text variant='note'>{`${agentWallet.walletAddress.slice(0, 6)}...${agentWallet.walletAddress.slice(-4)}`}</Text>
                  <IconButton
                    icon={<KibaIcon iconId='ion-copy-outline' variant='small' />}
                    onClicked={() => navigator.clipboard.writeText(agentWallet.walletAddress)}
                  />
                </Stack>
              ) : (
                <LoadingShimmer width='300px' height='16px' />
              )}
              {strategy ? (
                <Text variant='note'>{strategy.summary}</Text>
              ) : (
                <LoadingShimmer width='300px' height='16px' />
              )}
            </Stack>
          </Stack>
          <StatusBadge><Text variant='bold-branded'>Active</Text></StatusBadge>
        </Stack>
        <Spacing variant={PaddingSize.Default} />
        <EqualGrid childSizeResponsive={{ base: 12, medium: 6, large: 4 }} shouldAddGutters={false} isFullHeight={false}>
          <Box variant='card' isFullWidth={true}>
            <Stack direction={Direction.Vertical} shouldAddGutters={false}>
              <Text variant='note'>Available Balance</Text>
              <Spacing variant={PaddingSize.Narrow} />
              {agentWallet ? (
                <React.Fragment>
                  {agentWallet.assetBalances.length > 0 ? (
                    <React.Fragment>
                      {agentWallet.assetBalances.map((balance) => {
                        const amount = Number(balance.balance) / (10 ** balance.asset.decimals);
                        const value = amount * balance.assetPrice.priceUsd;
                        if (amount === 0) {
                          return null;
                        }
                        return (
                          <React.Fragment key={balance.asset.assetId}>
                            <Text variant='bold'>
                              {amount.toFixed(balance.asset.symbol === 'USDC' ? 2 : 6)}
                              {' '}
                              {balance.asset.symbol}
                            </Text>
                            <Text variant='note'>
                              $
                              {value.toFixed(2)}
                            </Text>
                            <Spacing variant={PaddingSize.Narrow} />
                          </React.Fragment>
                        );
                      })}
                    </React.Fragment>
                  ) : (
                    <Text variant='note'>No tokens available</Text>
                  )}
                </React.Fragment>
              ) : (
                <LoadingShimmer width='120px' height='32px' />
              )}
            </Stack>
          </Box>
          <Box variant='card' isFullWidth={true}>
            <Stack direction={Direction.Vertical} shouldAddGutters={false}>
              <Text variant='note'>Uniswap V3 Positions</Text>
              <Spacing variant={PaddingSize.Narrow} />
              {agentWallet ? (
                <React.Fragment>
                  {agentWallet.uniswapPositions.length > 0 ? (
                    <React.Fragment>
                      {agentWallet.uniswapPositions.map((position) => {
                        const token0Amount = Number(position.token0Amount) / (10 ** position.token0.decimals);
                        const token1Amount = Number(position.token1Amount) / (10 ** position.token1.decimals);
                        return (
                          <React.Fragment key={position.tokenId}>
                            <Text variant='bold'>{`$${position.totalValueUsd.toFixed(2)}`}</Text>
                            <Text variant='note'>
                              {token0Amount.toFixed(6)}
                              {' '}
                              {position.token0.symbol}
                              {' ($'}
                              {position.token0ValueUsd.toFixed(2)}
                              )
                            </Text>
                            <Text variant='note'>
                              {token1Amount.toFixed(2)}
                              {' '}
                              {position.token1.symbol}
                              {' ($'}
                              {position.token1ValueUsd.toFixed(2)}
                              )
                            </Text>
                            <Spacing variant={PaddingSize.Narrow} />
                          </React.Fragment>
                        );
                      })}
                    </React.Fragment>
                  ) : (
                    <Text variant='note'>No positions</Text>
                  )}
                </React.Fragment>
              ) : (
                <LoadingShimmer width='120px' height='32px' />
              )}
            </Stack>
          </Box>
          <Box variant='card' isFullWidth={true}>
            <Stack direction={Direction.Vertical} shouldAddGutters={false}>
              <Text variant='note'>Total Value</Text>
              <Spacing variant={PaddingSize.Narrow} />
              {agentWallet ? (
                <Text variant='extraLarge-fancy-bold'>{`$${totalValue.toFixed(2)}`}</Text>
              ) : (
                <LoadingShimmer width='120px' height='32px' />
              )}
              {agentWallet && totalValue > 0 && chainId === BASE_CHAIN_ID && (
                <React.Fragment>
                  <Spacing variant={PaddingSize.Wide} />
                  <Text variant='note'>{`Your agent has $${totalValue.toFixed(2)}. You can rebalance liquidity to optimize returns.`}</Text>
                  <Spacing />
                  <Button
                    variant='secondary'
                    text={isRebalancing ? 'Rebalancing...' : 'Rebalance Liquidity'}
                    onClicked={onRebalanceClicked}
                    isEnabled={!isRebalancing && !isDepositing}
                  />
                  {depositError && (
                    <React.Fragment>
                      <Spacing variant={PaddingSize.Wide} />
                      <Text variant='error'>{depositError}</Text>
                    </React.Fragment>
                  )}
                </React.Fragment>
              )}
            </Stack>
          </Box>
        </EqualGrid>
        <Box variant='card'>
          <Stack direction={Direction.Vertical} padding={PaddingSize.Default} shouldAddGutters={true} maxWidth='400px'>
            {chainId !== BASE_CHAIN_ID ? (
              <Stack direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center}>
                <Text variant='bold'>Wrong Network</Text>
                <Text variant='note' alignment={TextAlignment.Center}>Please switch to the Base network to deposit funds. Range Seeker only supports Base chain.</Text>
                <Button variant='secondary' text='Switch to Base' onClicked={() => onSwitchToWeb3ChainIdClicked(BASE_CHAIN_ID)} />
              </Stack>
            ) : (
              <React.Fragment>
                <Text variant='header4'>Deposit More Funds</Text>
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
                  <Stack direction={Direction.Horizontal} shouldAddGutters={true}>
                    <Text variant='note'>{`$${(Number(usdcDepositAmount || 0) * usdcPrice).toFixed(2)}`}</Text>
                    <Text variant='note'>{usdcBalance ? `Balance: ${Number(usdcBalance).toFixed(4)}` : 'Loading...'}</Text>
                  </Stack>
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
                  <Stack direction={Direction.Horizontal} shouldAddGutters={true}>
                    <Text variant='note'>{`$${(Number(wethDepositAmount || 0) * wethPrice).toFixed(2)}`}</Text>
                    <Text variant='note'>{wethBalance ? `Balance: ${Number(wethBalance).toFixed(4)}` : 'Loading...'}</Text>
                  </Stack>
                </Stack>
                {depositSummary && (
                  <React.Fragment>
                    <Spacing variant={PaddingSize.Default} />
                    {depositSummary}
                    <Spacing variant={PaddingSize.Default} />
                  </React.Fragment>
                )}
                {depositError && (
                  <Text variant='error'>{depositError}</Text>
                )}
                {depositSteps.length > 0 && (
                  <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                    <Text variant='bold'>Transaction Progress:</Text>
                    {depositSteps.map((step) => (
                      <Stack key={step.label} direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
                        <Text>
                          {step.status === 'pending' && '◼'}
                          {step.status === 'loading' && '👀'}
                          {step.status === 'success' && '✅'}
                          {step.status === 'error' && '❌'}
                        </Text>
                        <Text variant={step.status === 'error' ? 'error' : 'default'}>{step.label}</Text>
                      </Stack>
                    ))}
                  </Stack>
                )}
                <Button
                  variant='primary'
                  text={isDepositing ? 'Depositing...' : 'Deposit'}
                  onClicked={onDepositClicked}
                  isEnabled={!isDepositing && !isRebalancing && (usdcDepositAmount.length > 0 || wethDepositAmount.length > 0)}
                />
              </React.Fragment>
            )}
          </Stack>
        </Box>
        <Spacing variant={PaddingSize.Default} />
        <Box width='100%' height='300px'>
          <PriceChart />
        </Box>
      </Stack>
    </Stack>
  );
}
