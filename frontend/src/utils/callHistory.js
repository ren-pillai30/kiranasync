export function buildRecentCallHistory(transcripts, limit = 6) {
  if (!Array.isArray(transcripts)) return [];

  return transcripts
    .slice(-limit)
    .filter((turn) => turn && typeof turn.text === 'string' && turn.text.trim())
    .map(({ role, text }) => ({
      role: role === 'assistant' ? 'assistant' : 'customer',
      text: text.trim(),
    }));
}
