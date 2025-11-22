import React from 'react';

import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, PaddingSize, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';

import { GlassCard } from '../../components/GlassCard';
import { MockChart } from '../../components/MockChart';

export function HomePage(): React.ReactElement {
  const navigator = useNavigator();

  const onConnectClicked = () => {
    navigator.navigateTo('/create');
  };

  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='1000px' isFullWidth={true}>
        <Text variant='header1' alignment={TextAlignment.Center}>Range Seeker</Text>
        <Text variant='large' alignment={TextAlignment.Center}>Agentic Liquidity Provision</Text>

        <Box width='100%' height='400px'>
          <MockChart />
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

        <Button variant='primary' text='Connect Wallet' onClicked={onConnectClicked} />
      </Stack>
    </Stack>
  );
}
