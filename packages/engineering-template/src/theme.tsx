/** Shared, protected presentation tokens. Intrinsic device/material colors remain factual. */
import React, { createContext, useContext } from 'react';
export const designPacks = {
  neon_horizon: {
    background: '#0d1022',
    ink: '#fff2d6',
    accent: '#75ded7',
    panel: '#202038',
    muted: '#b2b8d0',
    header: '#272241',
    headerText: '#fff2d6',
    soft: '#292540',
    selected: '#613254',
    border: '#594066',
    code: '#14172c',
    codeText: '#d1f4f3',
    success: '#75ded7',
    warning: '#ffd18a',
    danger: '#fc818b',
  },
  editorial_warm: {
    background: '#f4efe5',
    ink: '#273b38',
    accent: '#a63d49',
    panel: '#fffdf7',
    muted: '#7a8580',
    header: '#34423e',
    headerText: '#fffaf1',
    soft: '#efe8dc',
    selected: '#f0d9cd',
    border: '#d4c8b5',
    code: '#263a36',
    codeText: '#e3ece4',
    success: '#39816c',
    warning: '#a36b22',
    danger: '#b14c58',
  },
  workspace_tech: {
    background: '#eef4fa',
    ink: '#17354b',
    accent: '#087f83',
    panel: '#ffffff',
    muted: '#718698',
    header: '#17354b',
    headerText: '#f6fbff',
    soft: '#edf2f7',
    selected: '#d8eee9',
    border: '#c4d3df',
    code: '#153444',
    codeText: '#ddf0f4',
    success: '#078780',
    warning: '#b37b25',
    danger: '#b85759',
  },
};
export type DesignPack = keyof typeof designPacks;
export type ThemeTokens = typeof designPacks.workspace_tech;
const Context = createContext<ThemeTokens>(designPacks.workspace_tech);
export function ThemeProvider({
  pack = 'workspace_tech',
  children,
}: {
  pack?: DesignPack;
  children: React.ReactNode;
}) {
  return <Context.Provider value={designPacks[pack]}>{children}</Context.Provider>;
}
export const useTheme = () => useContext(Context);
