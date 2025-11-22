import React from 'react';

import { useInitialization, useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Direction, EqualGrid, LoadingSpinner, PaddingSize, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import styled from 'styled-components';

import { useAuth } from '../../AuthContext';
import { Agent } from '../../client/resources';
import { useGlobals } from '../../GlobalsContext';

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

  const onAgentClicked = (agentId: string) => {
    navigator.navigateTo(`/agents/${agentId}`);
  };

  const onCreateClicked = () => {
    navigator.navigateTo('/create');
  };

  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} isScrollableVertically={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='1000px' isFullWidth={true}>
        <Text variant='header1'>Your Agents</Text>
        <Spacing variant={PaddingSize.Wide} />
        {!agents ? (
          <Stack direction={Direction.Vertical} isFullWidth={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} padding={PaddingSize.Wide3}>
            <LoadingSpinner />
          </Stack>
        ) : (
          <EqualGrid childSizeResponsive={{ base: 12, medium: 6, extraLarge: 4 }} childAlignment={Alignment.Fill} contentAlignment={Alignment.Start}>
            {agents.map((agent: Agent): React.ReactElement => (
              <ClickableBox key={agent.agentId} onClick={() => onAgentClicked(agent.agentId)}>
                <Box variant='card'>
                  <Stack direction={Direction.Vertical} padding={PaddingSize.Wide} childAlignment={Alignment.Center}>
                    <IconBox>{agent.emoji}</IconBox>
                    <Text variant='header3'>{agent.name}</Text>
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
                </Box>
              </ClickableBox>
            ))}
            <ClickableBox onClick={onCreateClicked}>
              <Box variant='card'>
                <Stack direction={Direction.Vertical} padding={PaddingSize.Wide} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true} minHeight='200px'>
                  <CreateIconBox>+</CreateIconBox>
                  <Text alignment={TextAlignment.Center} variant='header3'><ColoredText color='rgba(255,255,255,0.7)'>Create New Agent</ColoredText></Text>
                  <Text alignment={TextAlignment.Center}>Deploy a new strategy</Text>
                </Stack>
              </Box>
            </ClickableBox>
          </EqualGrid>
        )}
      </Stack>
    </Stack>
  );
}
