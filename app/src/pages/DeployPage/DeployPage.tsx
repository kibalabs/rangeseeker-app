import React, { useState } from 'react';


import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, PaddingSize, SingleLineInput, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import { useWeb3Account, useOnSwitchToWeb3ChainIdClicked, useWeb3ChainId } from '@kibalabs/web3-react';
import styled from 'styled-components';

import { useAuth } from '../../AuthContext';
import { Agent, AssetBalance, Wallet } from '../../client/resources';
import { useGlobals } from '../../GlobalsContext';
import { useStrategyCreation } from '../../StrategyCreationContext';
import { executeDepositToAgent } from '../../util/depositHelper';

const ICONS = ['🤖', '🚀', '💎', '🦁', '🦉', '⚡️'];
const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const WETH_ADDRESS = '0x4200000000000000000000000000000000000006';
const REQUIRED_ETH_GAS = '0.001';
const BASE_CHAIN_ID = 8453;

const IconBox = styled.div<{ isSelected: boolean }>`
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  cursor: pointer;
  background-color: ${(props) => (props.isSelected ? 'rgba(46, 228, 227, 0.2)' : 'rgba(255, 255, 255, 0.05)')};
  border: ${(props) => (props.isSelected ? '2px solid #2EE4E3' : '1px solid rgba(255, 255, 255, 0.1)')};
  transition: all 0.2s ease;

  &:hover {
    background-color: rgba(46, 228, 227, 0.1);
  }
`;

export function DeployPage(): React.ReactElement {
  const navigator = useNavigator();
  const { rangeSeekerClient } = useGlobals();
  const { authToken } = useAuth();
  const { strategyDefinition, strategyDescription } = useStrategyCreation();
  const account = useWeb3Account();
  const chainId = useWeb3ChainId();
  const onSwitchToWeb3ChainIdClicked = useOnSwitchToWeb3ChainIdClicked();

  // Agent creation state
  const [agentName, setAgentName] = useState<string>('Range Seeker');
  const [selectedIcon, setSelectedIcon] = useState<string>(ICONS[0]);
  const [isDeploying, setIsDeploying] = useState<boolean>(false);
  const [createdAgent, setCreatedAgent] = useState<Agent | null>(null);

  // Deposit state
  const [usdcAmount, setUsdcAmount] = useState<string>('');
  const [wethAmount, setWethAmount] = useState<string>('');
  const [ethAmount, setEthAmount] = useState<string>(REQUIRED_ETH_GAS);
  const [isDepositing, setIsDepositing] = useState<boolean>(false);
  const [userUsdcBalance, setUserUsdcBalance] = useState<string | null>(null);
  const [userWethBalance, setUserWethBalance] = useState<string | null>(null);
  const [userEthBalance, setUserEthBalance] = useState<string | null>(null);
  const [depositError, setDepositError] = useState<string | null>(null);
  const [depositSteps, setDepositSteps] = useState<Array<{label: string; status: 'pending' | 'loading' | 'success' | 'error'}>>([]);
  const [agentWallet, setAgentWallet] = useState<Wallet | null>(null);
  const [isRebalancing, setIsRebalancing] = useState<boolean>(false);

  // Fetch user balances and agent wallet after agent creation
  React.useEffect(() => {
    if (createdAgent && account?.address && authToken) {
      const fetchBalances = async () => {
        try {
          // Fetch user balances
          const balances = await rangeSeekerClient.getWalletBalances(8453, account.address);
          const usdc = balances.find((b) => b.asset.address.toLowerCase() === USDC_ADDRESS.toLowerCase());
          const weth = balances.find((b) => b.asset.address.toLowerCase() === WETH_ADDRESS.toLowerCase());

          if (usdc) {
            setUserUsdcBalance((Number(usdc.balance) / (10 ** usdc.asset.decimals)).toString());
          } else {
            setUserUsdcBalance('0');
          }

          if (weth) {
            setUserWethBalance((Number(weth.balance) / (10 ** weth.asset.decimals)).toString());
          } else {
            setUserWethBalance('0');
          }

          // Get ETH balance from provider
          if (account.signer) {
            const ethBalanceWei = await account.signer.provider?.getBalance(account.address);
            if (ethBalanceWei) {
              const ethers = await import('ethers');
              setUserEthBalance(ethers.formatEther(ethBalanceWei));
            }
          }

          // Fetch agent wallet
          const wallet = await rangeSeekerClient.getAgentWallet(createdAgent.agentId, authToken);
          setAgentWallet(wallet);
        } catch (error) {
          console.error('Failed to fetch balances:', error);
        }
      };
      fetchBalances();
    }
  }, [createdAgent, account, authToken, rangeSeekerClient]);

  const onDeployClicked = async () => {
    if (!authToken || !strategyDefinition) {
      return;
    }
    setIsDeploying(true);
    try {
      const agent = await rangeSeekerClient.createAgent(
        agentName,
        selectedIcon,
        agentName,
        strategyDescription,
        strategyDefinition,
        authToken,
      );
      setCreatedAgent(agent);
    } catch (error) {
      console.error('Failed to deploy agent:', error);
    } finally {
      setIsDeploying(false);
    }
  };

  const onRebalanceClicked = async () => {
    if (!createdAgent || !authToken) {
      return;
    }

    setIsRebalancing(true);
    setDepositError(null);
    try {
      await rangeSeekerClient.depositMadeToAgent(createdAgent.agentId, authToken);

      // Navigate to dashboard after success
      setTimeout(() => {
        navigator.navigateTo('/dashboard');
      }, 1500);
    } catch (error) {
      console.error('Failed to rebalance:', error);
      setDepositError(error instanceof Error ? error.message : 'Rebalance failed. Please try again.');
      setIsRebalancing(false);
    }
  };

  const onDepositClicked = async () => {
    if (!createdAgent || !account?.signer || !authToken) {
      return;
    }

    // Validate ETH amount
    if (Number(ethAmount) < Number(REQUIRED_ETH_GAS)) {
      setDepositError(`You must send at least ${REQUIRED_ETH_GAS} ETH for gas`);
      return;
    }

    // Validate at least one token is being deposited
    if ((!usdcAmount || Number(usdcAmount) === 0) && (!wethAmount || Number(wethAmount) === 0)) {
      setDepositError('You must deposit at least some USDC or WETH');
      return;
    }

    // Build steps list
    const steps: Array<{label: string; status: 'pending' | 'loading' | 'success' | 'error'}> = [];
    if (ethAmount && Number(ethAmount) > 0) {
      steps.push({ label: `Send ${ethAmount} ETH`, status: 'pending' });
    }
    if (usdcAmount && Number(usdcAmount) > 0) {
      steps.push({ label: `Send ${usdcAmount} USDC`, status: 'pending' });
    }
    if (wethAmount && Number(wethAmount) > 0) {
      steps.push({ label: `Send ${wethAmount} WETH`, status: 'pending' });
    }
    steps.push({ label: 'Rebalance liquidity', status: 'pending' });
    setDepositSteps(steps);

    setIsDepositing(true);
    setDepositError(null);
    try {
      const { ethers } = await import('ethers');
      const agentWallet = await rangeSeekerClient.getAgentWallet(createdAgent.agentId, authToken);
      let currentStepIndex = 0;

      // ETH transfer
      if (ethAmount && Number(ethAmount) > 0) {
        setDepositSteps(prev => prev.map((s, i) => i === currentStepIndex ? {...s, status: 'loading'} : s));
        try {
          const ethAmountWei = ethers.parseEther(ethAmount);
          const ethTx = await account.signer.sendTransaction({
            to: agentWallet.walletAddress,
            value: ethAmountWei,
          });
          await ethTx.wait();
          setDepositSteps(prev => prev.map((s, i) => i === currentStepIndex ? {...s, status: 'success'} : s));
          currentStepIndex++;
        } catch (error) {
          setDepositSteps(prev => prev.map((s, i) => i === currentStepIndex ? {...s, status: 'error'} : s));
          throw error;
        }
      }

      // USDC transfer
      if (usdcAmount && Number(usdcAmount) > 0) {
        setDepositSteps(prev => prev.map((s, i) => i === currentStepIndex ? {...s, status: 'loading'} : s));
        try {
          const ERC20_ABI = ['function transfer(address to, uint256 amount) public returns (bool)'];
          const usdcContract = new ethers.Contract(USDC_ADDRESS, ERC20_ABI, account.signer);
          const usdcAmountWei = BigInt((Number(usdcAmount) * 10 ** 6).toFixed(0));
          const usdcTx = await usdcContract.transfer(agentWallet.walletAddress, usdcAmountWei);
          await usdcTx.wait();
          setDepositSteps(prev => prev.map((s, i) => i === currentStepIndex ? {...s, status: 'success'} : s));
          currentStepIndex++;
        } catch (error) {
          setDepositSteps(prev => prev.map((s, i) => i === currentStepIndex ? {...s, status: 'error'} : s));
          throw error;
        }
      }

      // WETH transfer
      if (wethAmount && Number(wethAmount) > 0) {
        setDepositSteps(prev => prev.map((s, i) => i === currentStepIndex ? {...s, status: 'loading'} : s));
        try {
          const ERC20_ABI = ['function transfer(address to, uint256 amount) public returns (bool)'];
          const wethContract = new ethers.Contract(WETH_ADDRESS, ERC20_ABI, account.signer);
          const wethAmountWei = ethers.parseEther(wethAmount);
          const wethTx = await wethContract.transfer(agentWallet.walletAddress, wethAmountWei);
          await wethTx.wait();
          setDepositSteps(prev => prev.map((s, i) => i === currentStepIndex ? {...s, status: 'success'} : s));
          currentStepIndex++;
        } catch (error) {
          setDepositSteps(prev => prev.map((s, i) => i === currentStepIndex ? {...s, status: 'error'} : s));
          throw error;
        }
      }

      // Notify backend and rebalance
      setDepositSteps(prev => prev.map((s, i) => i === currentStepIndex ? {...s, status: 'loading'} : s));
      try {
        await rangeSeekerClient.depositMadeToAgent(createdAgent.agentId, authToken);
        setDepositSteps(prev => prev.map((s, i) => i === currentStepIndex ? {...s, status: 'success'} : s));

        // Navigate to dashboard after success
        setTimeout(() => {
          navigator.navigateTo('/dashboard');
        }, 1500);
      } catch (error) {
        setDepositSteps(prev => prev.map((s, i) => i === currentStepIndex ? {...s, status: 'error'} : s));
        throw error;
      }
    } catch (error) {
      console.error('Failed to deposit:', error);
      setDepositError(error instanceof Error ? error.message : 'Deposit failed. Please try again.');
      setIsDepositing(false);
    }
  };

  if (!strategyDefinition) {
    return (
      <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Center}>
        <Text>No strategy defined. Please go back and create a strategy.</Text>
        <Spacing variant={PaddingSize.Default} />
        <Button variant='primary' text='Create Strategy' onClicked={() => navigator.navigateTo('/create')} />
      </Stack>
    );
  }

  // Show deposit form after agent is created
  if (createdAgent) {
    return (
      <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} isScrollableVertically={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='600px' isFullWidth={true}>
          <Text variant='header1'>✅ Agent Deployed!</Text>
          <Text>Now deposit funds to activate {createdAgent.emoji} {createdAgent.name}</Text>
          <Spacing variant={PaddingSize.Wide} />
          <Box variant='card'>
            <Stack direction={Direction.Vertical} shouldAddGutters={true} padding={PaddingSize.Wide}>
              <Text variant='header3'>Deposit Funds</Text>
              <Text variant='note'>Send tokens to your agent&apos;s wallet to get started</Text>
              <Spacing variant={PaddingSize.Default} />

              {chainId !== BASE_CHAIN_ID ? (
                <Stack direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center}>
                  <Text variant='bold'>Wrong Network</Text>
                  <Text variant='note' alignment={TextAlignment.Center}>Please switch to the Base network to deposit funds. Range Seeker only supports Base chain.</Text>
                  <Button variant='secondary' text='Switch to Base' onClicked={() => onSwitchToWeb3ChainIdClicked(BASE_CHAIN_ID)} />
                </Stack>
              ) : (
                <React.Fragment>
              {/* ETH for gas */}
              <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center}>
                  <Text variant='bold'>ETH (for gas) *</Text>
                  <Spacing />
                  {userEthBalance && <Text variant='note'>Balance: {Number(userEthBalance).toFixed(4)} ETH</Text>}
                </Stack>
                <SingleLineInput
                  value={ethAmount}
                  onValueChanged={setEthAmount}
                  placeholderText={`Minimum: ${REQUIRED_ETH_GAS}`}
                />
                <Text variant='note'>Agent needs ETH to pay for transaction fees</Text>
              </Stack>

              {/* USDC */}
              <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center}>
                  <Text variant='bold'>USDC</Text>
                  <Spacing />
                  {userUsdcBalance && <Text variant='note'>Balance: {Number(userUsdcBalance).toFixed(2)} USDC</Text>}
                </Stack>
                <SingleLineInput
                  value={usdcAmount}
                  onValueChanged={setUsdcAmount}
                  placeholderText='0.00'
                />
              </Stack>

              {/* WETH */}
              <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center}>
                  <Text variant='bold'>WETH</Text>
                  <Spacing />
                  {userWethBalance && <Text variant='note'>Balance: {Number(userWethBalance).toFixed(6)} WETH</Text>}
                </Stack>
                <SingleLineInput
                  value={wethAmount}
                  onValueChanged={setWethAmount}
                  placeholderText='0.00'
                />
              </Stack>

              <Spacing variant={PaddingSize.Default} />
              {depositError && (
                <Text variant='error'>{depositError}</Text>
              )}
              {depositSteps.length > 0 && (
                <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                  <Text variant='bold'>Transaction Progress:</Text>
                  {depositSteps.map((step, index) => (
                    <Stack key={index} direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
                      <Text>
                        {step.status === 'pending' && '⏳'}
                        {step.status === 'loading' && '⏺'}
                        {step.status === 'success' && '✅'}
                        {step.status === 'error' && '❌'}
                      </Text>
                      <Text variant={step.status === 'error' ? 'error' : 'default'}>{step.label}</Text>
                    </Stack>
                  ))}
                </Stack>
              )}
              {agentWallet && agentWallet.assetBalances.some((b: AssetBalance) =>
                (b.asset.address.toLowerCase() === USDC_ADDRESS.toLowerCase() ||
                 b.asset.address.toLowerCase() === WETH_ADDRESS.toLowerCase()) &&
                Number(b.balance) > 0
              ) && (
                <React.Fragment>
                  <Text variant='note' alignment={TextAlignment.Center}>Your agent already has funds. You can rebalance without depositing more.</Text>
                  <Button
                    variant='secondary'
                    text={isRebalancing ? 'Rebalancing...' : 'Rebalance Liquidity'}
                    onClicked={onRebalanceClicked}
                    isEnabled={!isRebalancing && !isDepositing}
                  />
                  <Text variant='note' alignment={TextAlignment.Center}>— or deposit more —</Text>
                </React.Fragment>
              )}
              <Button
                variant='primary'
                text={isDepositing ? 'Depositing...' : 'Deposit & Activate'}
                onClicked={onDepositClicked}
                isEnabled={!isDepositing && !isRebalancing && Number(ethAmount) >= Number(REQUIRED_ETH_GAS) && (Number(usdcAmount) > 0 || Number(wethAmount) > 0)}
              />
              <Text variant='note'>* At least {REQUIRED_ETH_GAS} ETH and some USDC or WETH required</Text>
                </React.Fragment>
              )}
            </Stack>
          </Box>
        </Stack>
      </Stack>
    );
  }

  // Show initial agent creation form
  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} isScrollableVertically={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='600px' isFullWidth={true}>
        <Text variant='header1'>Deploy Your Agent</Text>
        <Text>Give your agent an identity.</Text>
        <Spacing variant={PaddingSize.Wide} />
        <Box variant='card'>
          <Stack direction={Direction.Vertical} shouldAddGutters={true} padding={PaddingSize.Wide}>
            <Stack direction={Direction.Vertical} shouldAddGutters={true}>
              <Text variant='bold'>Name</Text>
              <SingleLineInput
                value={agentName}
                onValueChanged={setAgentName}
                placeholderText='e.g. Alpha Seeker 1'
              />
            </Stack>
            <Stack direction={Direction.Vertical} shouldAddGutters={true}>
              <Text variant='bold'>Icon</Text>
              <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center}>
                {ICONS.map((icon) => (
                  <IconBox
                    key={icon}
                    isSelected={selectedIcon === icon}
                    onClick={() => setSelectedIcon(icon)}
                  >
                    {icon}
                  </IconBox>
                ))}
              </Stack>
            </Stack>
            <Spacing variant={PaddingSize.Default} />
            <Stack direction={Direction.Vertical} shouldAddGutters={true}>
              <Text variant='bold'>Strategy description</Text>
              <Text>{strategyDefinition.summary}</Text>
            </Stack>
            <Spacing variant={PaddingSize.Default} />
            <Button
              variant='primary'
              text={isDeploying ? 'Deploying Agent...' : 'Deploy Agent'}
              onClicked={onDeployClicked}
              isEnabled={!isDeploying && agentName.length > 0}
            />
          </Stack>
        </Box>
      </Stack>
    </Stack>
  );
}
