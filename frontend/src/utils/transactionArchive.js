const transactionHeaders = [
  'Timestamp',
  'Transaction type',
  'Entity',
  'Quantity',
  'Amount',
  'Command',
];

export function getTransactionDate(timestamp) {
  if (!timestamp) return null;
  const value = String(timestamp);
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value)
    ? value
    : `${value.replace(' ', 'T')}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return null;
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function groupTransactionsByDay(transactions = []) {
  const days = new Map();
  transactions.forEach((transaction) => {
    const date = getTransactionDate(transaction.Timestamp);
    if (!date) return;
    if (!days.has(date)) days.set(date, []);
    days.get(date).push(transaction);
  });
  return [...days.entries()]
    .sort(([first], [second]) => second.localeCompare(first))
    .map(([date, records]) => ({
      date,
      records: records.sort((first, second) =>
        String(second.Timestamp).localeCompare(String(first.Timestamp))
      ),
    }));
}

const csvCell = (value) => {
  const text = value === null || value === undefined ? '' : String(value);
  const safeText = /^[\s]*[=+\-@]/.test(text) ? `'${text}` : text;
  return `"${safeText.replaceAll('"', '""')}"`;
};

export function buildTransactionsCsv(transactions) {
  const rows = [
    transactionHeaders,
    ...transactions.map((transaction) => [
      transaction.Timestamp,
      transaction.TransactionType,
      transaction.EntityName,
      transaction.Quantity,
      transaction.TotalAmount,
      transaction.CommandText,
    ]),
  ];
  return `\uFEFF${rows.map((row) => row.map(csvCell).join(',')).join('\r\n')}`;
}
