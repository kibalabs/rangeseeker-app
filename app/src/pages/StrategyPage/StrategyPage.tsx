import React, { useState } from 'react';

import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, KibaIcon, MultiLineInput, PaddingSize, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import styled from 'styled-components';

import { useAuth } from '../../AuthContext';
import { StrategyDefinition, StrategyRule } from '../../client/resources';
import { LoadingShimmer } from '../../components/LoadingShimmer';
import { PriceChart } from '../../components/PriceChart';
import { useGlobals } from '../../GlobalsContext';
import { useStrategyCreation } from '../../StrategyCreationContext';
import { usePoolDataQuery, usePoolHistoricalDataQuery } from '../../util';

const CHAIN_ID = 8453;
const WETH_ADDRESS = '0x4200000000000000000000000000000000000006';
const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

const DropdownBox = styled.div`
  background-color: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  cursor: pointer;
  min-width: 140px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: all 0.2s ease;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);

  &:hover {
    background-color: rgba(255, 255, 255, 0.08);
    border-color: rgba(110, 211, 233, 0.4);
    box-shadow: 0 0 20px rgba(110, 211, 233, 0.1);
  }
`;

const PriceInfoBox = styled.div`
  background: linear-gradient(135deg, rgba(110, 211, 233, 0.1) 0%, rgba(196, 242, 200, 0.1) 100%);
  border: 1px solid rgba(110, 211, 233, 0.2);
  border-radius: 12px;
  padding: 16px 24px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
`;

const EarningsBox = styled.div`
  background: linear-gradient(135deg, rgba(110, 211, 233, 0.15), rgba(196, 242, 200, 0.15));
  border: 1px solid rgba(110, 211, 233, 0.3);
  border-radius: 16px;
  padding: ${PaddingSize.Wide};
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
`;

export function StrategyPage(): React.ReactElement {
  const { rangeSeekerClient } = useGlobals();
  const { authToken } = useAuth();
  const { setStrategy } = useStrategyCreation();
  const navigator = useNavigator();
  const [selectedPreset, setSelectedPreset] = useState<string>('conservative');
  const [strategyInput, setStrategyInput] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [strategyDefinition, setStrategyDefinition] = useState<StrategyDefinition | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Extract range percent from strategy definition
  const rangePercent = React.useMemo(() => {
    if (!strategyDefinition) return undefined;
    const rangeRule = strategyDefinition.rules.find((rule) => rule.type === 'RANGE_WIDTH');
    if (rangeRule && 'baseRangePercent' in rangeRule.parameters) {
      // baseRangePercent is a whole number (e.g., 4 for 4%), convert to decimal (0.04)
      return rangeRule.parameters.baseRangePercent / 100;
    }
    return undefined;
  }, [strategyDefinition]);

  const { data: poolData, isLoading: isLoadingPool, error: poolDataError } = usePoolDataQuery(CHAIN_ID, WETH_ADDRESS, USDC_ADDRESS);
  const { data: historicalData, isLoading: isLoadingHistorical } = usePoolHistoricalDataQuery(CHAIN_ID, WETH_ADDRESS, USDC_ADDRESS, 24 * 7);

  // Calculate earnings estimate based on strategy range
  const earningsEstimate = React.useMemo(() => {
    if (!poolData || rangePercent === undefined) return null;
    if (!poolData.feeGrowth7d || !poolData.feeRate) {
      console.error('Missing feeGrowth7d or feeRate in poolData', poolData);
      return null;
    }

    const TOKEN0_DECIMALS = 18; // WETH
    const TOKEN1_DECIMALS = 6; // USDC
    const INVESTMENT_AMOUNT = 100; // USD

    const price = poolData.currentPrice;
    const priceA = price * (1 - rangePercent);
    const priceB = price * (1 + rangePercent);

    const sqrtP = Math.sqrt(price);
    const sqrtPa = Math.sqrt(priceA);
    const sqrtPb = Math.sqrt(priceB);

    const denominator = (2 * sqrtP) - (price / sqrtPb) - sqrtPa;
    const liquidityFor100 = denominator > 0 ? INVESTMENT_AMOUNT / denominator : 0;

    const liquidityAdjustment = 10 ** ((TOKEN0_DECIMALS + TOKEN1_DECIMALS) / 2);
    const liquidityFor100Raw = liquidityFor100 * liquidityAdjustment;

    // Base weekly earnings assuming 100% time in range, no costs
    const maxWeeklyEarningsUsd = poolData.feeGrowth7d * poolData.feeRate * liquidityFor100Raw;

    // Calculate volatility to range ratio - key metric for time in range
    const volatilityRatio = poolData.volatility7d / rangePercent;

    // Estimate time in range
    // Note: Auto-rebalancing means we get back in range quickly, and mean reversion helps
    // Best case: favorable conditions (trending market, good timing)
    // Worst case: unfavorable conditions (choppy market, bad timing) but not catastrophic
    let bestCaseTimeInRange = 0.95;
    let worstCaseTimeInRange = 0.7; // Still reasonable even in worst case

    if (volatilityRatio > 4) {
      // Extremely tight relative to volatility (e.g., ±2% with 8% vol)
      // These are high-risk/high-reward strategies
      bestCaseTimeInRange = 0.7; // Good conditions with quick rebalancing
      worstCaseTimeInRange = 0.45; // Choppy market, but auto-rebalance helps
    } else if (volatilityRatio > 2.5) {
      // Very tight (e.g., ±4% with 10% vol)
      bestCaseTimeInRange = 0.8;
      worstCaseTimeInRange = 0.55;
    } else if (volatilityRatio > 1.5) {
      // Moderately tight
      bestCaseTimeInRange = 0.85;
      worstCaseTimeInRange = 0.65;
    } else if (volatilityRatio > 0.8) {
      // Balanced
      bestCaseTimeInRange = 0.9;
      worstCaseTimeInRange = 0.75;
    }

    // Rebalancing on Base L2 (cheaper than mainnet)
    const gasPerRebalance = 3; // ~$3 on Base

    // Rebalancing frequency scales with how tight the range is
    // Best case: price stays stable, occasional rebalances
    // Worst case: choppy market, more frequent rebalances but capped at reasonable limit
    const bestCaseRebalancesPerWeek = Math.max(0.3, volatilityRatio * 0.25);
    const bestCaseGasCosts = bestCaseRebalancesPerWeek * gasPerRebalance;

    // Cap worst case at 2 rebalances/week even for aggressive strategies
    // (more than that and you'd likely pause the strategy)
    const worstCaseRebalancesPerWeek = Math.min(2, Math.max(0.5, volatilityRatio * 0.5));
    const worstCaseGasCosts = worstCaseRebalancesPerWeek * gasPerRebalance;

    // Calculate range
    const bestCaseWeeklyUsd = (maxWeeklyEarningsUsd * bestCaseTimeInRange) - bestCaseGasCosts;
    const worstCaseWeeklyUsd = (maxWeeklyEarningsUsd * worstCaseTimeInRange) - worstCaseGasCosts;

    const bestCaseWeeklyPercent = (bestCaseWeeklyUsd / INVESTMENT_AMOUNT) * 100;
    const worstCaseWeeklyPercent = (worstCaseWeeklyUsd / INVESTMENT_AMOUNT) * 100;

    // Compound weekly returns to annual (more realistic than simple multiplication)
    const bestCaseAPY = ((1 + bestCaseWeeklyPercent / 100) ** 52 - 1) * 100;
    const worstCaseAPY = worstCaseWeeklyUsd > 0
      ? ((1 + worstCaseWeeklyPercent / 100) ** 52 - 1) * 100
      : worstCaseWeeklyPercent * 52; // If negative, just multiply for negative APY

    return {
      bestCase: {
        weeklyUsd: bestCaseWeeklyUsd,
        weeklyPercent: bestCaseWeeklyPercent,
        apyPercent: bestCaseAPY,
      },
      worstCase: {
        weeklyUsd: worstCaseWeeklyUsd,
        weeklyPercent: worstCaseWeeklyPercent,
        apyPercent: worstCaseAPY,
      },
    };
  }, [poolData, rangePercent]);

  React.useEffect(() => {
    if (poolData && !strategyInput) {
      const conservativeText = generatePresetText('conservative', poolData.currentPrice, poolData.volatility24h);
      setStrategyInput(conservativeText);
    }
  }, [poolData, strategyInput]);

  const generatePresetText = (preset: string, price: number, volatility: number): string => {
    const conservativeExit = (price * 0.9).toFixed(0);
    const balancedExit = (price * 0.92).toFixed(0);
    const aggressiveExit = (price * 0.95).toFixed(0);
    const volatilityPercent = (volatility * 100).toFixed(0);

    switch (preset) {
      case 'conservative':
        return `Maintain a wide ±8% range to capture fees with minimal rebalancing. Widen to ±15% if volatility exceeds ${volatilityPercent}% (current: ${volatilityPercent}%). Exit to USDC if ETH drops below $${conservativeExit} to protect capital.`;
      case 'balanced':
        return `Use a ±4% range for steady fee generation. Dynamically widen to ±8% when volatility goes above ${(volatility * 0.8 * 100).toFixed(0)}% (current: ${volatilityPercent}%). Exit to USDC if ETH falls below $${balancedExit}.`;
      case 'aggressive':
        return `Tight ±2% range to maximize fee capture in the most active price zone. Accept frequent rebalancing for higher returns. Pause rebalancing if volatility exceeds ${(volatility * 1.2 * 100).toFixed(0)}% (current: ${volatilityPercent}%). Exit to USDC if ETH drops below $${aggressiveExit} to lock in profits.`;
      default:
        return '';
    }
  };

  const onPresetClicked = (preset: string) => {
    if (!poolData) return;
    setSelectedPreset(preset);
    const text = generatePresetText(preset, poolData.currentPrice, poolData.volatility24h);
    setStrategyInput(text);
  };

  const onInputChange = (value: string) => {
    setStrategyInput(value);
    setSelectedPreset('custom');
  };

  const onGenerateClicked = async () => {
    if (!authToken) {
      setError('Please connect your wallet first');
      return;
    }
    setIsGenerating(true);
    setError(null);
    setStrategyDefinition(null);
    try {
      const parsedStrategy = await rangeSeekerClient.parseStrategy(strategyInput, authToken);
      setStrategyDefinition(parsedStrategy);
    } catch (err) {
      console.error('Error parsing strategy:', err);
      setError('Failed to parse strategy. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const onDeployClicked = async () => {
    if (!strategyDefinition) {
      return;
    }
    setStrategy(strategyDefinition, strategyInput);
    navigator.navigateTo('/deploy');
  };

  const renderRuleDetails = (rule: StrategyRule) => {
    if (rule.type === 'RANGE_WIDTH' && 'baseRangePercent' in rule.parameters) {
      const rebalanceThreshold = rule.parameters.baseRangePercent * (1 + rule.parameters.rebalanceBuffer);
      return (
        <Stack direction={Direction.Vertical} key={`${rule.type}-${rule.priority}`}>
          <Text>{`Range: ±${rule.parameters.baseRangePercent}% • Rebalances when price moves ${rebalanceThreshold.toFixed(1)}% from center`}</Text>
          {rule.parameters.dynamicWidening && (
            <Text>{`Widens to ±${rule.parameters.dynamicWidening.widenToPercent}% if volatility > ${rule.parameters.dynamicWidening.volatilityThreshold * 100}%`}</Text>
          )}
        </Stack>
      );
    }
    if (rule.type === 'PRICE_THRESHOLD' && 'priceUsd' in rule.parameters) {
      return (
        <Text key={`${rule.type}-${rule.priority}`}>{`${rule.parameters.action}: ${rule.parameters.asset} ${rule.parameters.operator === 'LESS_THAN' ? '<' : '>'} $${rule.parameters.priceUsd.toLocaleString()}`}</Text>
      );
    }
    if (rule.type === 'VOLATILITY_TRIGGER' && 'threshold' in rule.parameters) {
      return (
        <Text key={`${rule.type}-${rule.priority}`}>{`${rule.parameters.action} if volatility > ${rule.parameters.threshold * 100}%`}</Text>
      );
    }
    return null;
  };

  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} isScrollableVertically={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='1200px' isFullWidth={true}>
        <Text variant='header1'>Create Your Strategy</Text>
        <Text variant='note'>Define how your agent should manage your liquidity.</Text>
        <Spacing variant={PaddingSize.Wide2} />

        <Box variant='card' isFullWidth={true}>
          <Stack direction={Direction.Vertical} shouldAddGutters={true} defaultGutter={PaddingSize.Wide}>
            <Text variant='header4'>Choose your tokens</Text>
            <Stack direction={Direction.Horizontal} shouldAddGutters={true} defaultGutter={PaddingSize.Wide} childAlignment={Alignment.End} contentAlignment={Alignment.Start}>
              <Stack direction={Direction.Vertical} shouldAddGutters={true} defaultGutter={PaddingSize.Narrow}>
                <Text variant='note'>Chain</Text>
                <DropdownBox>
                  <Text variant='bold'>Base</Text>
                  <KibaIcon iconId='ion-chevron-down' />
                </DropdownBox>
              </Stack>
              <Stack direction={Direction.Vertical} shouldAddGutters={true} defaultGutter={PaddingSize.Narrow}>
                <Text variant='note'>Token 0</Text>
                <DropdownBox>
                  <Text variant='bold'>WETH</Text>
                  <KibaIcon iconId='ion-chevron-down' />
                </DropdownBox>
              </Stack>
              <Stack direction={Direction.Vertical} shouldAddGutters={true} defaultGutter={PaddingSize.Narrow}>
                <Text variant='note'>Token 1</Text>
                <DropdownBox>
                  <Text variant='bold'>USDC</Text>
                  <KibaIcon iconId='ion-chevron-down' />
                </DropdownBox>
              </Stack>
            </Stack>

            {isLoadingPool ? (
              <LoadingShimmer height='80px' />
            ) : poolDataError ? (
              <Text variant='error'>Failed to load pool data</Text>
            ) : poolData ? (
              <PriceInfoBox>
                <Stack direction={Direction.Vertical} shouldAddGutters={true} defaultGutter={PaddingSize.Narrow} childAlignment={Alignment.Center}>
                  <Text variant='large-bold'>{`Current Price: $${poolData.currentPrice.toFixed(2)}`}</Text>
                  <Stack direction={Direction.Horizontal} shouldAddGutters={true} defaultGutter={PaddingSize.Wide} childAlignment={Alignment.Center}>
                    <Text variant='note'>{`24h Vol: ${(poolData.volatility24h * 100).toFixed(1)}%`}</Text>
                    <Text variant='note'>•</Text>
                    <Text variant='note'>{`7d Vol: ${(poolData.volatility7d * 100).toFixed(1)}%`}</Text>
                  </Stack>
                </Stack>
              </PriceInfoBox>
            ) : null}
          </Stack>
        </Box>

        {!isLoadingPool && (
          <React.Fragment>
            <Spacing variant={PaddingSize.Wide2} />
            <Stack direction={Direction.Horizontal} isFullWidth={true} shouldAddGutters={true} defaultGutter={PaddingSize.Wide2} childAlignment={Alignment.Start} contentAlignment={Alignment.Start}>
              <Stack.Item growthFactor={1} shrinkFactor={1}>
                <Box variant='card'>
                  <Stack direction={Direction.Vertical} shouldAddGutters={true} defaultGutter={PaddingSize.Wide} padding={PaddingSize.Wide}>
                    <Text variant='header4'>Strategy</Text>
                    {poolData ? (
                      <Stack direction={Direction.Vertical} shouldAddGutters={true} defaultGutter={PaddingSize.Default}>
                        <Button
                          variant={selectedPreset === 'conservative' ? 'secondary' : 'tertiary'}
                          text='Conservative'
                          onClicked={() => onPresetClicked('conservative')}
                          isFullWidth={true}
                        />
                        <Button
                          variant={selectedPreset === 'balanced' ? 'secondary' : 'tertiary'}
                          text='Balanced'
                          onClicked={() => onPresetClicked('balanced')}
                          isFullWidth={true}
                        />
                        <Button
                          variant={selectedPreset === 'aggressive' ? 'secondary' : 'tertiary'}
                          text='Aggressive'
                          onClicked={() => onPresetClicked('aggressive')}
                          isFullWidth={true}
                        />
                        <Button
                          variant={selectedPreset === 'custom' ? 'secondary' : 'tertiary'}
                          text='Custom'
                          onClicked={() => setSelectedPreset('custom')}
                          isFullWidth={true}
                        />
                      </Stack>
                    ) : null}
                    <Spacing variant={PaddingSize.Default} />
                    <Text variant='bold'>Describe your strategy in plain English:</Text>
                    <MultiLineInput
                      value={strategyInput}
                      onValueChanged={onInputChange}
                      placeholderText='e.g. Tight ±2% range for maximum fees. Widen to ±8% if volatility spikes above 15%. Exit to USDC if ETH drops below $2500.'
                      minRowCount={6}
                    />
                    <Button variant='primary' text={isGenerating ? 'Generating...' : 'Generate Strategy'} onClicked={onGenerateClicked} isEnabled={!isGenerating} isFullWidth={true} />
                    {error && <Text variant='error'>{error}</Text>}
                  </Stack>
                </Box>
              </Stack.Item>
              <Stack.Item growthFactor={1} shrinkFactor={1}>
                <Box variant='card'>
                  <Stack direction={Direction.Vertical} shouldAddGutters={true} defaultGutter={PaddingSize.Wide} padding={PaddingSize.Wide}>
                    <Text variant='header4'>Price Chart &amp; Strategy Preview</Text>
                    {isLoadingHistorical ? (
                      <LoadingShimmer height='300px' />
                    ) : (
                      <Box width='100%' height='300px'>
                        <PriceChart
                          priceData={historicalData?.pricePoints}
                          strategyDefinition={strategyDefinition}
                          currentPrice={poolData?.currentPrice}
                        />
                      </Box>
                    )}
                    {strategyDefinition ? (
                      <React.Fragment>
                        <Stack direction={Direction.Vertical} shouldAddGutters={true} defaultGutter={PaddingSize.Wide}>
                          <Stack direction={Direction.Vertical} shouldAddGutters={true} defaultGutter={PaddingSize.Default}>
                            <Text variant='header5'>Strategy Summary</Text>
                            <Text variant='bold'>{strategyDefinition.summary}</Text>
                          </Stack>
                          <Stack direction={Direction.Vertical} shouldAddGutters={true} defaultGutter={PaddingSize.Default}>
                            <Text variant='header5'>Rules</Text>
                            {strategyDefinition.rules.map((rule) => renderRuleDetails(rule))}
                          </Stack>
                        </Stack>
                        {earningsEstimate && (
                          <EarningsBox>
                            <Stack direction={Direction.Vertical} shouldAddGutters={true} defaultGutter={PaddingSize.Default}>
                              <Text variant='header5'>💰 Estimated earnings on $100 investment</Text>
                              <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} defaultGutter={PaddingSize.Wide2}>
                                <Stack direction={Direction.Vertical} childAlignment={Alignment.Center}>
                                  <Text variant='note'>Good case</Text>
                                  <Text variant='header3'>{`$${earningsEstimate.bestCase.weeklyUsd.toFixed(2)}/wk`}</Text>
                                  <Text variant='bold'>{`${earningsEstimate.bestCase.apyPercent.toFixed(1)}% APY`}</Text>
                                </Stack>
                                <Text variant='header3'>→</Text>
                                <Stack direction={Direction.Vertical} childAlignment={Alignment.Center}>
                                  <Text variant='note'>Bad case</Text>
                                  <Text variant='header3'>{`$${earningsEstimate.worstCase.weeklyUsd.toFixed(2)}/wk`}</Text>
                                  <Text variant='bold'>{`${earningsEstimate.worstCase.apyPercent.toFixed(1)}% APY`}</Text>
                                </Stack>
                              </Stack>
                              <Text variant='note' alignment={TextAlignment.Center}>Range based on time-in-range and gas costs</Text>
                            </Stack>
                          </EarningsBox>
                        )}
                        <Spacing variant={PaddingSize.Wide} />
                        <Button variant='primary' text='Deploy Agent' onClicked={onDeployClicked} isFullWidth={true} />
                      </React.Fragment>
                    ) : (
                      <Text variant='note' alignment={TextAlignment.Center}>Generate a strategy to see overlay details</Text>
                    )}
                  </Stack>
                </Box>
              </Stack.Item>
            </Stack>
          </React.Fragment>
        )}
      </Stack>
    </Stack>
  );
}
