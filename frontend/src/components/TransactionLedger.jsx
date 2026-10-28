export default function TransactionLedger({ transactions, t, onViewBill }) {
  const handleRowBill = (txn) => {
    if (!onViewBill) return;
    const isCredit = txn.TransactionType === 'Credit';
    const amount = Math.abs(Number(txn.TotalAmount || 0));
    const qty = txn.Quantity || 1;
    const unitPrice = qty > 0 ? Math.round(amount / qty) : amount;

    onViewBill({
      billItems: [
        {
          item_name: txn.EntityName || txn.CommandText || 'Retail Item',
          quantity: qty,
          unit_price: unitPrice,
          item_total: amount,
        },
      ],
      customerName: isCredit ? (txn.EntityName || 'Customer') : 'Walk-in Customer',
      paymentMode: isCredit ? 'udhaar' : 'cash',
      customerBalance: isCredit ? amount : 0,
    });
  };

  return (
    <section className="mt-8">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-lg font-bold text-gray-100 flex items-center space-x-2">
            <span>📜</span>
            <span>{t.ledgerTitle}</span>
          </h3>
          <p className="text-xs text-gray-400">All registered counter transactions, sales, and credit logs</p>
        </div>
        <span className="text-xs font-mono bg-gray-800 text-gray-300 px-2.5 py-1 rounded-lg border border-gray-700">
          {transactions.length} Records
        </span>
      </div>

      <div className="bg-gray-800/90 rounded-xl overflow-hidden border border-gray-700 max-h-80 shadow-inner">
        <table className="w-full min-w-[760px] text-left text-sm text-gray-300">
          <thead className="bg-gray-900/90 text-gray-400 uppercase text-[11px] tracking-wider sticky top-0 border-b border-gray-700">
            <tr>
              <th className="px-4 py-3">{t.ledgerDate}</th>
              <th className="px-4 py-3">{t.ledgerType}</th>
              <th className="px-4 py-3">{t.ledgerEntity}</th>
              <th className="px-4 py-3 text-right">{t.ledgerQuantity}</th>
              <th className="px-4 py-3 text-right">{t.ledgerAmount}</th>
              <th className="px-4 py-3">{t.ledgerDetails}</th>
              <th className="px-3 py-3 text-center">Receipt</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700/50">
            {transactions.length === 0 ? (
              <tr>
                <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                  {t.ledgerEmpty}
                </td>
              </tr>
            ) : (
              transactions.map((transaction) => {
                const isSale = transaction.TransactionType === 'Sale';
                const isCredit = transaction.TransactionType === 'Credit';
                const isRestock = transaction.TransactionType === 'Restock';
                const isRepay = transaction.TransactionType === 'Repayment';

                return (
                  <tr key={transaction.TxnID} className="hover:bg-gray-700/30 transition-colors">
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-400 font-mono">
                      {transaction.Timestamp
                        ? new Date(`${transaction.Timestamp.replace(' ', 'T')}Z`).toLocaleString('en-IN', {
                            day: '2-digit',
                            month: 'short',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium inline-block ${
                          isSale
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                            : isCredit
                            ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                            : isRestock
                            ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                            : isRepay
                            ? 'bg-purple-500/15 text-purple-400 border border-purple-500/30'
                            : 'bg-gray-700 text-gray-300'
                        }`}
                      >
                        {transaction.TransactionType}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium text-white">{transaction.EntityName || '—'}</td>
                    <td className="px-4 py-3 text-right font-mono">{transaction.Quantity ?? '—'}</td>
                    <td className="px-4 py-3 text-right whitespace-nowrap font-mono font-semibold">
                      <span
                        className={
                          isSale || isRepay
                            ? 'text-emerald-400'
                            : isRestock
                            ? 'text-rose-400'
                            : isCredit
                            ? 'text-amber-400'
                            : 'text-gray-300'
                        }
                      >
                        {isSale || isRepay ? '+' : ''}
                        {isRestock && Number(transaction.TotalAmount) < 0 ? '−' : ''}
                        ₹{Math.abs(Number(transaction.TotalAmount || 0)).toLocaleString('en-IN')}
                      </span>
                    </td>
                    <td className="px-4 py-3 max-w-xs truncate text-xs text-gray-400" title={transaction.CommandText || ''}>
                      {transaction.CommandText || '—'}
                    </td>
                    <td className="px-3 py-3 text-center">
                      {(isSale || isCredit) ? (
                        <button
                          onClick={() => handleRowBill(transaction)}
                          className="px-2 py-1 text-xs bg-gray-700/80 hover:bg-emerald-600/30 hover:border-emerald-500/40 text-gray-300 hover:text-emerald-300 rounded border border-gray-600 transition-all font-medium"
                          title="Generate printable invoice receipt"
                        >
                          🧾 Bill
                        </button>
                      ) : (
                        <span className="text-gray-600 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
