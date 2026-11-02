/**
 * Accent colours for a matchup. When both teams share the same accent, the pair override
 * (key: the two tricodes sorted and joined by "-") replaces the colour of the tricode(s) it lists.
 * Colour values come from the caller (tokens.json); none live here.
 */
export function matchupAccents(
  home: string,
  away: string,
  accents: Record<string, string>,
  overrides: Record<string, Record<string, string>>,
  fallback: string,
): { home: string; away: string } {
  const pick = (t: string) => accents[t] ?? fallback;
  const clash = pick(home) === pick(away) && accents[home] !== undefined;
  const o = clash ? (overrides[[home, away].sort().join("-")] ?? {}) : {};
  return { home: o[home] ?? pick(home), away: o[away] ?? pick(away) };
}
