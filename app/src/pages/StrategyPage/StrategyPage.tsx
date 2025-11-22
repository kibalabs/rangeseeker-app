import React, { useState } from 'react';

import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, MultiLineInput, PaddingSize, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';

import { GlassCard } from '../../components/GlassCard';
import { MockChart } from '../../components/MockChart';

export function StrategyPage(): React.ReactElement {
  const navigator = useNavigator();
  const [selectedPreset, setSelectedPreset] = useState<string>('balanced');
  const [strategyInput, setStrategyInput] = useState<string>('Maintain a moderate range (±5%) to earn decent fees while protecting capital. Rebalance when volatility spikes.');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [showPreview, setShowPreview] = useState<boolean>(false);

  const onPresetClicked = (preset: string, text: string) => {
    setSelectedPreset(preset);
    setStrategyInput(text);
  };

  const onInputChange = (value: string) => {
    setStrategyInput(value);
    setSelectedPreset('custom');
  };

  const onGenerateClicked = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      setShowPreview(true);
    }, 1500);
  };

  const onDeployClicked = () => {
    navigator.navigateTo('/deploy');
  };

  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='1000px' isFullWidth={true}>
        <Text variant='header1'>Create Your Agent</Text>
        <Text variant='note'>Define how your agent should manage your liquidity.</Text>

        <Spacing variant={PaddingSize.Wide} />

        <Stack direction={Direction.Horizontal} isFullWidth={true} shouldAddGutters={true} childAlignment={Alignment.Start} contentAlignment={Alignment.Start}>
          {/* Input Section */}
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            <GlassCard>
              <Stack direction={Direction.Vertical} shouldAddGutters={true} padding={PaddingSize.Wide}>
                <Text variant='header3'>Strategy</Text>

                <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                  <Button
                    variant={selectedPreset === 'passive' ? 'primary' : 'tertiary'}
                    text='Passive'
                    onClicked={() => onPresetClicked('passive', 'Keep my range wide (±10%) to minimize rebalancing and avoid impermanent loss. Only rebalance if price moves significantly.')}
                  />
                  <Button
                    variant={selectedPreset === 'balanced' ? 'primary' : 'tertiary'}
                    text='Balanced'
                    onClicked={() => onPresetClicked('balanced', 'Maintain a moderate range (±5%) to earn decent fees while protecting capital. Rebalance when volatility spikes.')}
                  />
                  <Button
                    variant={selectedPreset === 'aggressive' ? 'primary' : 'tertiary'}
                    text='Aggressive'
                    onClicked={() => onPresetClicked('aggressive', 'Maximize fee earnings with a tight range (±2%). Rebalance frequently to stay in range, even if it means higher gas costs.')}
                  />
                  <Button
                    variant={selectedPreset === 'custom' ? 'primary' : 'tertiary'}
                    text='Custom'
                    onClicked={() => setSelectedPreset('custom')}
                  />
                </Stack>

                <Text>Describe your strategy in plain English:</Text>
                <MultiLineInput
                  value={strategyInput}
                  onValueChanged={onInputChange}
                  placeholderText='e.g. I want tight range fee farming but widen if volatility spikes, and exit entirely to USDC if ETH ever drops below $3000'
                  minRowCount={5}
                />

                <Button variant='primary' text={isGenerating ? 'Generating...' : 'Generate Strategy'} onClicked={onGenerateClicked} isEnabled={!isGenerating} />
              </Stack>
            </GlassCard>
          </Stack.Item>

          {/* Preview Section */}
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            {showPreview ? (
              <GlassCard>
                <Stack direction={Direction.Vertical} shouldAddGutters={true} padding={PaddingSize.Wide}>
                  <Text variant='header3'>Strategy Preview</Text>
                  <Box width='100%' height='300px'>
                    <MockChart />
                  </Box>
                  <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                    <Text variant='bold'>Aggressive Fee Farming</Text>
                    <Text variant='note'>Range: ±3.2%</Text>
                    <Text variant='note'>Auto-widen on vol spike &gt; 5%</Text>
                    <Text variant='note'>Stop-loss: $3,000</Text>
                  </Stack>
                  <Button variant='primary' text='Deploy Agent' onClicked={onDeployClicked} />
                </Stack>
              </GlassCard>
            ) : (
              <Box height='400px'>
                <Stack direction={Direction.Vertical} isFullHeight={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Center}>
                  <Text variant='note' alignment={TextAlignment.Center}>Enter a strategy to see a preview</Text>
                </Stack>
              </Box>
            )}
          </Stack.Item>
        </Stack>
      </Stack>
    </Stack>
  );
}
