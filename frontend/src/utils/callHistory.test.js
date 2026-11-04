import test from 'node:test';
import assert from 'node:assert/strict';
import { buildRecentCallHistory } from './callHistory.js';

test('buildRecentCallHistory keeps only recent role and text fields', () => {
  const transcripts = Array.from({ length: 8 }, (_, index) => ({
    id: `turn-${index}`,
    role: index % 2 ? 'assistant' : 'customer',
    text: ` message ${index} `,
    audioBase64: 'large-base64-audio',
    audioContentType: 'audio/wav',
  }));

  assert.deepEqual(buildRecentCallHistory(transcripts), [
    { role: 'customer', text: 'message 2' },
    { role: 'assistant', text: 'message 3' },
    { role: 'customer', text: 'message 4' },
    { role: 'assistant', text: 'message 5' },
    { role: 'customer', text: 'message 6' },
    { role: 'assistant', text: 'message 7' },
  ]);
});

test('buildRecentCallHistory rejects invalid and empty histories', () => {
  assert.deepEqual(buildRecentCallHistory(null), []);
  assert.deepEqual(buildRecentCallHistory([null, {}, { text: '  ' }]), []);
});
