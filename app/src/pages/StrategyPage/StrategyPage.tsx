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
  const { data: poolData, isLoading: isLoadingPool, error: poolDataError } = usePoolDataQuery(CHAIN_ID, WETH_ADDRESS, USDC_ADDRESS);
  const { data: historicalData } = usePoolHistoricalDataQuery(CHAIN_ID, WETH_ADDRESS, USDC_ADDRESS, 24 * 7);
  const [selectedPreset, setSelectedPreset] = useState<string>('conservative');
  const [strategyInput, setStrategyInput] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [strategyDefinition, setStrategyDefinition] = useState<StrategyDefinition | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    // TODO: Navigate to agent creation page with strategy definition
    navigator.navigateTo('/deploy');
  };

  const renderRuleDetails = (rule: StrategyRule) => {
    if (rule.type === 'RANGE_WIDTH' && 'baseRangePercent' in rule.parameters) {
      const rebalanceThreshold = rule.parameters.baseRangePercent * (1 + rule.parameters.rebalanceBuffer);
      return (
        <Stack direction={Direction.Vertical} key={`${rule.type}-${rule.priority}`}>
          <Text variant='note'>
            Range: ±
            {rule.parameters.baseRangePercent}
            % • Rebalances when price moves
            {' '}
            {rebalanceThreshold.toFixed(1)}
            % from center
          </Text>
          {rule.parameters.dynamicWidening && (
            <Text variant='note'>
              Widens to ±
              {rule.parameters.dynamicWidening.widenToPercent}
              % if volatility &gt;
              {' '}
              {rule.parameters.dynamicWidening.volatilityThreshold * 100}
              %
            </Text>
          )}
        </Stack>
      );
    }
    if (rule.type === 'PRICE_THRESHOLD' && 'priceUsd' in rule.parameters) {
      return (
        <Text variant='note' key={`${rule.type}-${rule.priority}`}>
          {rule.parameters.action}
          :
          {rule.parameters.asset}
          {' '}
          {rule.parameters.operator === 'LESS_THAN' ? '<' : '>'}
          {' '}
          $
          {rule.parameters.priceUsd.toLocaleString()}
        </Text>
      );
    }
    if (rule.type === 'VOLATILITY_TRIGGER' && 'threshold' in rule.parameters) {
      return (
        <Text variant='note' key={`${rule.type}-${rule.priority}`}>
          {rule.parameters.action}
          {' '}
          if volatility &gt;
          {rule.parameters.threshold * 100}
          %
        </Text>
      );
    }
    return null;
  };

  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='1000px' isFullWidth={true}>
        <Text variant='header1'>Create Your Strategy</Text>
        <Text variant='note'>Define how your agent should manage your liquidity.</Text>
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
