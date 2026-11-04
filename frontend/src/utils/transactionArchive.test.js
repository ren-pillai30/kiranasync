import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildTransactionsCsv,
  getTransactionDate,
  groupTransactionsByDay,
} from './transactionArchive.js';

test('getTransactionDate groups timestamps by local calendar day', () => {
  const timestamp = new Date(2026, 10, 4, 23, 45).toISOString();
  assert.equal(getTransactionDate(timestamp), '2026-11-04');
});

test('groupTransactionsByDay sorts dates and transactions newest first', () => {
  const groups = groupTransactionsByDay([
    { TxnID: 1, Timestamp: '2026-11-03 10:00:00' },
    { TxnID: 2, Timestamp: '2026-11-04 09:00:00' },
    { TxnID: 3, Timestamp: '2026-11-04 12:00:00' },
    { TxnID: 4, Timestamp: null },
  ]);
  assert.deepEqual(groups, [
    {
      date: '2026-11-04',
      records: [
        { TxnID: 3, Timestamp: '2026-11-04 12:00:00' },
        { TxnID: 2, Timestamp: '2026-11-04 09:00:00' },
      ],
    },
    {
      date: '2026-11-03',
      records: [{ TxnID: 1, Timestamp: '2026-11-03 10:00:00' }],
    },
  ]);
});

test('buildTransactionsCsv escapes cells and guards spreadsheet formulas', () => {
  const csv = buildTransactionsCsv([{
    Timestamp: '2026-11-04 09:00:00',
    TransactionType: 'Sale',
    EntityName: 'Tea, "Premium"',
    Quantity: 1,
    TotalAmount: 25,
    CommandText: '=HYPERLINK("https://example.com")',
  }]);

  assert.match(csv, /"Tea, ""Premium"""/);
  assert.match(csv, /"'=HYPERLINK\(""https:\/\/example\.com""\)"/);
});
