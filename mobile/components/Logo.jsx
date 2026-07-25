import React from 'react';
import Svg, { Path } from 'react-native-svg';
import { Theme } from '../theme';

export function LogoMark({ size = 40 }) {
  return (
    <Svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
    >
      <Path
        fill={Theme.colors.accentStrong}
        d="M20 5 H44 C52.837 5 60 12.163 60 21 V33 C60 41.837 52.837 49 44 49 H27 L15 59.5 V48.2 C8.6 46.1 4 40.1 4 33 V21 C4 12.163 11.163 5 20 5 Z"
      />
      <Path
        fill={Theme.colors.card}
        d="M22 39 C22 26.5 31 17.5 43.5 17.5 C43.5 30 34.5 39 22 39 Z"
      />
      <Path
        fill="none"
        stroke={Theme.colors.accentSoft}
        strokeWidth="2"
        strokeLinecap="round"
        d="M23.5 37.5 C29.5 31.5 36 25 42 19"
      />
    </Svg>
  );
}
