import React from 'react';

import { Alignment, Box, Direction, PaddingSize, Spacing, Stack, Text } from '@kibalabs/ui-react';
import styled from 'styled-components';


import { GlassCard } from '../../components/GlassCard';
import { PriceChart } from '../../components/PriceChart';

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

export function DashboardPage(): React.ReactElement {
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
                  🤖
                </IconBox>
                <Stack direction={Direction.Vertical}>
                  <Text variant='header3'>Alpha Seeker 1</Text>
                  <Text variant='note'>Aggressive Fee Farming • ETH/USDC</Text>
                </Stack>
              </Stack>
              <StatusBadge>
                <Text variant='bold'><ColoredText color='#2EE4E3'>Active</ColoredText></Text>
              </StatusBadge>
            </FlexRow>

            <Spacing variant={PaddingSize.Default} />

            <Stack direction={Direction.Horizontal} isFullWidth={true} shouldAddGutters={true}>
              <StatBox>
                <Text variant='note'>Total Value</Text>
                <Spacing variant={PaddingSize.Narrow} />
                <Text variant='header2'>$5,432.10</Text>
              </StatBox>
              <StatBox>
                <Text variant='note'>Current APY</Text>
                <Spacing variant={PaddingSize.Narrow} />
                <Text variant='header2'><ColoredText color='#2EE4E3'>12.4%</ColoredText></Text>
              </StatBox>
              <StatBox>
                <Text variant='note'>24h Earnings</Text>
                <Spacing variant={PaddingSize.Narrow} />
                <Text variant='header2'><ColoredText color='#4CAF50'>+$12.40</ColoredText></Text>
              </StatBox>
            </Stack>

            <Spacing variant={PaddingSize.Default} />

            <Box width='100%' height='300px'>
              <PriceChart />
            </Box>

            <Spacing variant={PaddingSize.Default} />

            <Text variant='header4'>Recent Activity</Text>
            <Stack direction={Direction.Vertical} isFullWidth={true}>
              <ActivityItem>
                <Stack direction={Direction.Vertical}>
                  <Text variant='bold'>Rebalanced Position</Text>
                  <Text variant='note'>Price moved out of range (±3.2%)</Text>
                </Stack>
                <Text variant='note'>2 hours ago</Text>
              </ActivityItem>
              <ActivityItem>
                <Stack direction={Direction.Vertical}>
                  <Text variant='bold'>Claimed Rewards</Text>
                  <Text variant='note'>Auto-compounded 0.02 ETH</Text>
                </Stack>
                <Text variant='note'>5 hours ago</Text>
              </ActivityItem>
              <ActivityItem>
                <Stack direction={Direction.Vertical}>
                  <Text variant='bold'>Agent Deployed</Text>
                  <Text variant='note'>Initial deposit: $5,000</Text>
                </Stack>
                <Text variant='note'>1 day ago</Text>
              </ActivityItem>
            </Stack>

          </Stack>
        </GlassCard>
      </Stack>
    </Stack>
  );
}
