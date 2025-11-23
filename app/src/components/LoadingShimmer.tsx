import React from 'react';

import styled, { keyframes } from 'styled-components';

const shimmer = keyframes`
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
`;

const ShimmerBox = styled.div<{ width?: string; height?: string }>`
  width: ${(props) => props.width || '100%'};
  height: ${(props) => props.height || '20px'};
  background: linear-gradient(
    to right,
    rgba(255, 255, 255, 0.05) 0%,
    rgba(255, 255, 255, 0.15) 50%,
    rgba(255, 255, 255, 0.05) 100%
  );
  background-size: 1000px 100%;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 0px;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
  animation: ${shimmer} 2s infinite;
  border-radius: 8px;
`;

interface LoadingShimmerProps {
  width?: string;
  height?: string;
}

export function LoadingShimmer(props: LoadingShimmerProps): React.ReactElement {
  return <ShimmerBox width={props.width} height={props.height} />;
}
