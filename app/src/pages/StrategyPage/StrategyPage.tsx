import React, { useState } from 'react';

import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, KibaIcon, MultiLineInput, PaddingSize, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import styled from 'styled-components';

import { useAuth } from '../../AuthContext';
import { StrategyDefinition, StrategyRule } from '../../client/resources';
import { GlassCard } from '../../components/GlassCard';
import { PriceChart } from '../../components/PriceChart';
import { useGlobals } from '../../GlobalsContext';
import { usePoolDataQuery, usePoolHistoricalDataQuery } from '../../util';

const CHAIN_ID = 8453;
const WETH_ADDRESS = '0x4200000000000000000000000000000000000006';
const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

const DropdownBox = styled.div`
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  cursor: pointer;
  min-width: 120px;
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: all 0.2s ease;

  &:hover {
    background-color: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.3);
  }
`;

export function StrategyPage(): React.ReactElement {
  const { rangeSeekerClient } = useGlobals();
  const { authToken } = useAuth();
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
      return rangeRule.parameters.baseRangePercent;
    }
    return undefined;
  }, [strategyDefinition]);

  const { data: poolData, isLoading: isLoadingPool, error: poolDataError } = usePoolDataQuery(CHAIN_ID, WETH_ADDRESS, USDC_ADDRESS);
  const { data: historicalData } = usePoolHistoricalDataQuery(CHAIN_ID, WETH_ADDRESS, USDC_ADDRESS, 24 * 7);

  // Calculate earnings estimate based on strategy range
  const earningsEstimate = React.useMemo(() => {
    if (!poolData || rangePercent === undefined) return null;

    console.log('Calculating earnings with:', {
      feeGrowth7d: poolData.feeGrowth7d,
      feeRate: poolData.feeRate,
      rangePercent,
      currentPrice: poolData.currentPrice,
    });

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

    const weeklyEarningsUsd = poolData.feeGrowth7d * poolData.feeRate * liquidityFor100Raw;
    const weeklyPercent = (weeklyEarningsUsd / INVESTMENT_AMOUNT) * 100;
    const apyPercent = weeklyPercent * 52;

    console.log('Calculated earnings:', {
      liquidityFor100,
      liquidityFor100Raw,
      weeklyEarningsUsd,
      weeklyPercent,
      apyPercent,
    });

    return { weeklyUsd: weeklyEarningsUsd, weeklyPercent, apyPercent };
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
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='1000px' isFullWidth={true}>
        <Text variant='header1'>Create Your Strategy</Text>
        <Text>Define how your agent should manage your liquidity.</Text>
        <Spacing variant={PaddingSize.Wide} />
        <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Start}>
          <Stack direction={Direction.Vertical} shouldAddGutters={true}>
            <Text variant='note'>Chain</Text>
            <DropdownBox>
              <Text>Base</Text>
              <KibaIcon iconId='ion-chevron-down' />
            </DropdownBox>
          </Stack>
          <Stack direction={Direction.Vertical} shouldAddGutters={true}>
            <Text variant='note'>Token 0</Text>
            <DropdownBox>
              <Text>WETH</Text>
              <KibaIcon iconId='ion-chevron-down' />
            </DropdownBox>
          </Stack>
          <Stack direction={Direction.Vertical} shouldAddGutters={true}>
            <Text variant='note'>Token 1</Text>
            <DropdownBox>
              <Text>USDC</Text>
              <KibaIcon iconId='ion-chevron-down' />
            </DropdownBox>
          </Stack>
        </Stack>
        {isLoadingPool ? (
          <Text variant='note'>Loading pool data...</Text>
        ) : poolDataError ? (
          <Text variant='error'>Failed to load pool data</Text>
        ) : poolData ? (
          <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center}>
            <Text variant='note'>{`Current Price: $${poolData.currentPrice.toFixed(4)}`}</Text>
            <Text variant='note'>{`24h Volatility: ${(poolData.volatility24h * 100).toFixed(1)}%`}</Text>
            <Text variant='note'>{`7d Volatility: ${(poolData.volatility7d * 100).toFixed(1)}%`}</Text>
          </Stack>
        ) : null}
        <Spacing variant={PaddingSize.Wide} />
        <Stack direction={Direction.Horizontal} isFullWidth={true} shouldAddGutters={true} childAlignment={Alignment.Start} contentAlignment={Alignment.Start}>
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            <GlassCard>
              <Stack direction={Direction.Vertical} shouldAddGutters={true} padding={PaddingSize.Wide}>
                <Text variant='header3'>Strategy</Text>
                {poolData ? (
                  <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                    <Button
                      variant={selectedPreset === 'conservative' ? 'primary' : 'tertiary'}
                      text='Conservative'
                      onClicked={() => onPresetClicked('conservative')}
                    />
                    <Button
                      variant={selectedPreset === 'balanced' ? 'primary' : 'tertiary'}
                      text='Balanced'
                      onClicked={() => onPresetClicked('balanced')}
                    />
                    <Button
                      variant={selectedPreset === 'aggressive' ? 'primary' : 'tertiary'}
                      text='Aggressive'
                      onClicked={() => onPresetClicked('aggressive')}
                    />
                    <Button
                      variant={selectedPreset === 'custom' ? 'primary' : 'tertiary'}
                      text='Custom'
                      onClicked={() => setSelectedPreset('custom')}
                    />
                  </Stack>
                ) : null}
                <Text>Describe your strategy in plain English:</Text>
                <MultiLineInput
                  value={strategyInput}
                  onValueChanged={onInputChange}
                  placeholderText='e.g. I want tight range fee farming but widen if volatility spikes, and exit entirely to USDC if ETH ever drops below $3000'
                  minRowCount={5}
                />
                <Button variant='primary' text={isGenerating ? 'Generating...' : 'Generate Strategy'} onClicked={onGenerateClicked} isEnabled={!isGenerating} />
                {error && <Text variant='error'>{error}</Text>}
              </Stack>
            </GlassCard>
          </Stack.Item>
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            <GlassCard>
              <Stack direction={Direction.Vertical} shouldAddGutters={true} padding={PaddingSize.Wide}>
                <Text variant='header3'>Price Chart &amp; Strategy Preview</Text>
                <Box width='100%' height='300px'>
                  <PriceChart
                    priceData={historicalData?.pricePoints}
                    strategyDefinition={strategyDefinition}
                    currentPrice={poolData?.currentPrice}
                  />
                </Box>
                {strategyDefinition ? (
                  <React.Fragment>
                    <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                      <Text variant='bold'>{strategyDefinition.summary}</Text>
                      {strategyDefinition.rules.map((rule) => renderRuleDetails(rule))}
                    </Stack>
                    {earningsEstimate && (
                      <GlassCard variant='secondary'>
                        <Stack direction={Direction.Vertical} shouldAddGutters={true} padding={PaddingSize.Default}>
                          <Text variant='header4'>💰 Expected Earnings ($100 Investment)</Text>
                          <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Center}>
                            <Stack direction={Direction.Vertical} childAlignment={Alignment.Center}>
                              <Text variant='note'>Weekly Return</Text>
                              <Text variant='header2'>{`$${earningsEstimate.weeklyUsd.toFixed(2)}`}</Text>
                              <Text variant='note'>{`${earningsEstimate.weeklyPercent.toFixed(2)}%`}</Text>
                            </Stack>
                            <Stack direction={Direction.Vertical} childAlignment={Alignment.Center}>
                              <Text variant='note'>Estimated APY</Text>
                              <Text variant='header2'>{`${earningsEstimate.apyPercent.toFixed(1)}%`}</Text>
                              <Text variant='note'>Annualized</Text>
                            </Stack>
                          </Stack>
                        </Stack>
                      </GlassCard>
                    )}
                    <Button variant='primary' text='Deploy Agent' onClicked={onDeployClicked} />
                  </React.Fragment>
                ) : (
                  <Text variant='note' alignment={TextAlignment.Center}>Generate a strategy to see overlay details</Text>
                )}
              </Stack>
            </GlassCard>
          </Stack.Item>
        </Stack>
      </Stack>
    </Stack>
  );
}
