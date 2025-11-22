import React from 'react';

import { Button, useColors } from '@kibalabs/ui-react';
import { rgba } from 'polished';
import styled from 'styled-components';

interface GlowingButtonProps {
  glowColor1: string;
  glowColor2: string;
  glowColor3: string;
}

const GlowingButton = styled(Button)<GlowingButtonProps>`
  position: relative;
  overflow: visible;

  &::before {
    content: '';
    position: absolute;
    top: -6px;
    left: -6px;
    right: -6px;
    bottom: -6px;
    background: linear-gradient(135deg, ${(props) => props.glowColor1}, ${(props) => props.glowColor2}, ${(props) => props.glowColor3});
    border-radius: inherit;
    opacity: 1;
    z-index: 0;
    filter: blur(25px);
    animation: glow 3s ease-in-out infinite;
  }

  &:hover::before {
    filter: blur(35px);
    animation: glowHover 2s ease-in-out infinite;
  }

  @keyframes glow {
    0%, 100% {
      opacity: 0.5;
      transform: scale(1);
    }
    50% {
      opacity: 0.9;
      transform: scale(1.05);
    }
  }

  @keyframes glowHover {
    0%, 100% {
      opacity: 0.7;
      transform: scale(1.05);
    }
    50% {
      opacity: 1;
      transform: scale(1.1);
    }
  }
`;

interface GlowButtonProps {
  text: string;
  onClicked: () => void | Promise<void>;
  variant?: string;
  isLoading?: boolean;
  isEnabled?: boolean;
}

export function GlowButton(props: GlowButtonProps): React.ReactElement {
  const colors = useColors();

  const glowColor1 = rgba(colors.brandPrimary, 0.4);
  const glowColor2 = rgba(colors.brandPrimary, 0.2);
  const glowColor3 = rgba(colors.brandPrimary, 0.4);

  return (
    <GlowingButton
      variant={props.variant}
      text={props.text}
      onClicked={props.onClicked}
      isLoading={props.isLoading}
      isEnabled={props.isEnabled}
      glowColor1={glowColor1}
      glowColor2={glowColor2}
      glowColor3={glowColor3}
    />
  );
}
