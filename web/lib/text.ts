const ENTITY_MAP: Record<string, string> = {
  '&amp;': '&',
  '&lt;': '<',
  '&gt;': '>',
  '&quot;': '"',
  '&apos;': "'",
  '&#39;': "'",
  '&#x27;': "'",
  '&nbsp;': ' ',
};

export function decodeHtmlEntities(value: string | null | undefined): string {
  if (!value) return '';
  return value
    .replace(/&#x([0-9a-fA-F]+);/g, (_match, hex) => {
      const codePoint = Number.parseInt(hex, 16);
      return Number.isNaN(codePoint) ? _match : String.fromCodePoint(codePoint);
    })
    .replace(/&#(\d+);/g, (_match, num) => {
      const codePoint = Number.parseInt(num, 10);
      return Number.isNaN(codePoint) ? _match : String.fromCodePoint(codePoint);
    })
    .replace(/&[a-zA-Z0-9#]+;/g, (match) => ENTITY_MAP[match] ?? match);
}
