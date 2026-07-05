export interface DiffToken {
  type: 'same' | 'added' | 'removed';
  value: string;
}

/** Word-level LCS diff — small inputs only (prompt template text), O(n*m). */
export function diffWords(before: string, after: string): DiffToken[] {
  const a = before.split(/(\s+)/).filter(Boolean);
  const b = after.split(/(\s+)/).filter(Boolean);

  const lengths: number[][] = Array.from({ length: a.length + 1 }, () =>
    new Array(b.length + 1).fill(0),
  );
  for (let i = a.length - 1; i >= 0; i -= 1) {
    for (let j = b.length - 1; j >= 0; j -= 1) {
      lengths[i][j] =
        a[i] === b[j] ? lengths[i + 1][j + 1] + 1 : Math.max(lengths[i + 1][j], lengths[i][j + 1]);
    }
  }

  const tokens: DiffToken[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      tokens.push({ type: 'same', value: a[i] });
      i += 1;
      j += 1;
    } else if (lengths[i + 1][j] >= lengths[i][j + 1]) {
      tokens.push({ type: 'removed', value: a[i] });
      i += 1;
    } else {
      tokens.push({ type: 'added', value: b[j] });
      j += 1;
    }
  }
  while (i < a.length) {
    tokens.push({ type: 'removed', value: a[i] });
    i += 1;
  }
  while (j < b.length) {
    tokens.push({ type: 'added', value: b[j] });
    j += 1;
  }
  return tokens;
}
