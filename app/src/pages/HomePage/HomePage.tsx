import React from 'react';

import { Alignment, Direction, Stack, Text, TextAlignment } from '@kibalabs/ui-react';

export function HomePage(): React.ReactElement {
  return (
    <Stack direction={Direction.Vertical} isFullWidth={true} isFullHeight={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Center}>
      <Text variant='header1' alignment={TextAlignment.Center}>Welcome to RangeSeeker</Text>
    </Stack>
  );
}
