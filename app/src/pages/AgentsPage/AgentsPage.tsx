import React from 'react';

import { useInitialization, useNavigator } from '@kibalabs/core-react';
import { Alignment, Direction, PaddingSize, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import styled from 'styled-components';

import { useAuth } from '../../AuthContext';
import { Agent } from '../../client/resources';
import { GlassCard } from '../../components/GlassCard';
import { useGlobals } from '../../GlobalsContext';

const AgentCard = styled(GlassCard)`
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease;
  border: 1px solid rgba(255, 255, 255, 0.1);

  &:hover {
    transform: translateY(-4px);
    border-color: #2EE4E3;
  }
`;

const CreateCard = styled(GlassCard)`
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease;
  border: 1px dashed rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.02);

  &:hover {
    transform: translateY(-4px);
    border-color: #2EE4E3;
    background: rgba(46, 228, 227, 0.05);
  }
`;

const IconBox = styled.div`
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background-color: rgba(46, 228, 227, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  border: 1px solid #2EE4E3;
  margin-bottom: 16px;
`;

const StatusBadge = styled.div`
  padding: 4px 12px;
  background-color: rgba(46, 228, 227, 0.2);
  border-radius: 20px;
  border: 1px solid rgba(46, 228, 227, 0.5);
  font-size: 12px;
  color: #2EE4E3;
  font-weight: bold;
`;

const ClickableBox = styled.div`
  width: 300px;
  cursor: pointer;
`;

const Divider = styled.div`
  width: 1px;
  height: 30px;
  background-color: rgba(255, 255, 255, 0.1);
`;

const ColoredText = styled.span<{ color: string }>`
  color: ${(props) => props.color};
`;

const CreateIconBox = styled.div`
  width: 60px;
  height: 60px;
  border-radius: 50%;
  border: 2px dashed rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 16px;
`;

export function AgentsPage(): React.ReactElement {
  const navigator = useNavigator();
  const { rangeSeekerClient } = useGlobals();
  const { authToken } = useAuth();
  const [agents, setAgents] = React.useState<Agent[] | null>(null);

  useInitialization(() => {
    const init = async () => {
      if (authToken) {
        const newAgents = await rangeSeekerClient.listAgents(authToken);
        setAgents(newAgents);
      }
    };
    init();
  });

  const onAgentClicked = () => {
    navigator.navigateTo('/dashboard');
  };

  const onCreateClicked = () => {
    navigator.navigateTo('/create');
  };

  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} isScrollableVertically={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='1000px' isFullWidth={true}>
        <Text variant='header1'>Your Agents</Text>
        <Text variant='note'>Manage your autonomous liquidity agents.</Text>
        <Spacing variant={PaddingSize.Wide} />
        <Stack direction={Direction.Horizontal} isFullWidth={true} shouldAddGutters={true} childAlignment={Alignment.Start} contentAlignment={Alignment.Start} shouldWrapItems={true}>
          {agents?.map((agent: Agent): React.ReactElement => (
            <ClickableBox key={agent.agentId} onClick={onAgentClicked}>
              <AgentCard>
                <Stack direction={Direction.Vertical} padding={PaddingSize.Wide} childAlignment={Alignment.Center}>
                  <Stack direction={Direction.Horizontal} isFullWidth={true} contentAlignment={Alignment.End}>
                    <StatusBadge>Active</StatusBadge>
                  </Stack>
                  <IconBox>{agent.emoji}</IconBox>
                  <Text variant='header3'>{agent.name}</Text>
                  <Text variant='note' alignment={TextAlignment.Center}>Strategy</Text>
                  <Spacing variant={PaddingSize.Default} />
                  <Stack direction={Direction.Horizontal} shouldAddGutters={true}>
                    <Stack direction={Direction.Vertical} childAlignment={Alignment.Center}>
                      <Text variant='note'>TVL</Text>
                      <Text variant='bold'>$0</Text>
                    </Stack>
                    <Divider />
                    <Stack direction={Direction.Vertical} childAlignment={Alignment.Center}>
                      <Text variant='note'>APY</Text>
                      <Text variant='bold'><ColoredText color='#2EE4E3'>0%</ColoredText></Text>
                    </Stack>
                  </Stack>
                </Stack>
              </AgentCard>
            </ClickableBox>
          ))}

          {/* Create New Agent Card */}
          <ClickableBox onClick={onCreateClicked}>
            <CreateCard>
              <Stack direction={Direction.Vertical} padding={PaddingSize.Wide} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true} minHeight='250px'>
                <CreateIconBox>
                  +
                </CreateIconBox>
                <Text variant='header3'><ColoredText color='rgba(255,255,255,0.7)'>Create New Agent</ColoredText></Text>
                <Text variant='note' alignment={TextAlignment.Center}>Deploy a new strategy</Text>
              </Stack>
            </CreateCard>
          </ClickableBox>

        </Stack>
      </Stack>
    </Stack>
  );
}
