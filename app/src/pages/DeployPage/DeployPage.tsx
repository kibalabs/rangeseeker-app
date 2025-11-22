import React, { useState } from 'react';


import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Button, Direction, PaddingSize, SingleLineInput, Spacing, Stack, Text } from '@kibalabs/ui-react';
import styled from 'styled-components';

import { useAuth } from '../../AuthContext';
import { GlassCard } from '../../components/GlassCard';
import { useGlobals } from '../../GlobalsContext';
import { useStrategyCreation } from '../../StrategyCreationContext';

const ICONS = ['🤖', '🚀', '💎', '🦁', '🦉', '⚡️'];

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

const SummaryBox = styled.div`
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 16px;
`;

export function DeployPage(): React.ReactElement {
  const navigator = useNavigator();
  const { rangeSeekerClient } = useGlobals();
  const { authToken } = useAuth();
  const { strategyDefinition, strategyDescription } = useStrategyCreation();
  const [agentName, setAgentName] = useState<string>('Range Seeker');
  const [selectedIcon, setSelectedIcon] = useState<string>(ICONS[0]);
  const [isDeploying, setIsDeploying] = useState<boolean>(false);

  const onDeployClicked = async () => {
    if (!authToken || !strategyDefinition) {
      return;
    }
    setIsDeploying(true);
    try {
      await rangeSeekerClient.createAgent(
        agentName,
        selectedIcon,
        agentName, // Using agent name as strategy name for now
        strategyDescription,
        strategyDefinition,
        authToken,
      );
      navigator.navigateTo('/dashboard');
    } catch (error) {
      console.error('Failed to deploy agent:', error);
      setIsDeploying(false);
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

  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} isScrollableVertically={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='600px' isFullWidth={true}>
        <Text variant='header1'>Deploy Your Agent</Text>
        <Text variant='note'>Give your agent a name and an identity.</Text>

        <Spacing variant={PaddingSize.Wide} />

        <GlassCard>
          <Stack direction={Direction.Vertical} shouldAddGutters={true} padding={PaddingSize.Wide}>
            <Text variant='header3'>Agent Details</Text>

            <Stack direction={Direction.Vertical} shouldAddGutters={true}>
              <Text>Name</Text>
              <SingleLineInput
                value={agentName}
                onValueChanged={setAgentName}
                placeholderText='e.g. Alpha Seeker 1'
              />
            </Stack>

            <Stack direction={Direction.Vertical} shouldAddGutters={true}>
              <Text>Icon</Text>
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

            <SummaryBox>
              <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                <Text variant='bold'>Strategy Summary</Text>
                <Text variant='note'>{strategyDefinition.summary}</Text>
              </Stack>
            </SummaryBox>

            <Spacing variant={PaddingSize.Default} />

            <Button
              variant='primary'
              text={isDeploying ? 'Deploying Agent...' : 'Deploy Agent'}
              onClicked={onDeployClicked}
              isEnabled={!isDeploying && agentName.length > 0}
            />
          </Stack>
        </GlassCard>
      </Stack>
    </Stack>
  );
}
