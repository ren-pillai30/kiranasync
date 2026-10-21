export default function TransactionLedger({ transactions, t }) {
  return (
    <section className="mt-8">
      <h3 className="text-lg font-semibold text-violet-400 mb-4">{t.ledgerTitle}</h3>
      <div className="bg-gray-800 rounded-xl overflow-auto border border-gray-700 max-h-80">
        <table className="w-full min-w-[760px] text-left text-sm text-gray-300">
          <thead className="bg-gray-700/70 text-gray-400 uppercase sticky top-0">
            <tr>
              <th className="px-4 py-3">{t.ledgerDate}</th>
              <th className="px-4 py-3">{t.ledgerType}</th>
              <th className="px-4 py-3">{t.ledgerEntity}</th>
              <th className="px-4 py-3 text-right">{t.ledgerQuantity}</th>
              <th className="px-4 py-3 text-right">{t.ledgerAmount}</th>
              <th className="px-4 py-3">{t.ledgerDetails}</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-4 py-8 text-center text-gray-500">
                  {t.ledgerEmpty}
                </td>
              </tr>
            ) : (
              transactions.map((transaction) => (
                <tr key={transaction.TxnID} className="border-t border-gray-700/50">
                  <td className="px-4 py-3 whitespace-nowrap">
                    {transaction.Timestamp
                      ? new Date(`${transaction.Timestamp.replace(' ', 'T')}Z`).toLocaleString()
                      : '—'}
                  </td>
                  <td className="px-4 py-3 font-medium text-white">{transaction.TransactionType}</td>
                  <td className="px-4 py-3">{transaction.EntityName || '—'}</td>
                  <td className="px-4 py-3 text-right">{transaction.Quantity ?? '—'}</td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <span
                      className={
                        transaction.TransactionType === 'Sale'
                          ? 'text-emerald-400'
                          : transaction.TransactionType === 'Restock'
                          ? 'text-rose-400'
                          : ''
                      }
                    >
                      {transaction.TransactionType === 'Sale' ? '+' : ''}
                      {['Restock', 'WriteOff'].includes(transaction.TransactionType) &&
                      Number(transaction.TotalAmount) < 0
                        ? '−'
                        : ''}
                      ₹{Math.abs(Number(transaction.TotalAmount || 0)).toLocaleString('en-IN')}
                    </span>
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate" title={transaction.CommandText || ''}>
                    {transaction.CommandText || '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
