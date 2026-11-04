import { useState } from 'react';

export default function TransactionLedger({ transactions, t, onViewBill }) {
  const [selectedReceipts, setSelectedReceipts] = useState([]);

  const supportsReceipt = (transaction) =>
    ['Sale', 'Restock', 'Credit'].includes(transaction.TransactionType);

  const toggleReceipt = (transactionId) => {
    setSelectedReceipts((current) =>
      current.includes(transactionId)
        ? current.filter((id) => id !== transactionId)
        : [...current, transactionId]
    );
  };

  const buildReceipt = (txn) => {
    const isCredit = txn.TransactionType === 'Credit';
    const amount = Math.abs(Number(txn.TotalAmount || 0));
    const qty = txn.Quantity || 1;
    const unitPrice = qty > 0 ? Math.round(amount / qty) : amount;

    return {
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
    };
  };

  const handleRowBill = (txn) => {
    if (!onViewBill) return;
    onViewBill(buildReceipt(txn));
  };

  const handleCombinedBill = () => {
    if (!onViewBill || selectedReceipts.length === 0) return;
    const selectedTransactions = transactions.filter((transaction) =>
      selectedReceipts.includes(transaction.TxnID)
    );
    const receipts = selectedTransactions.map(buildReceipt);
    const hasUdhaar = receipts.some((receipt) => receipt.paymentMode === 'udhaar');
    onViewBill({
      billItems: receipts.flatMap((receipt) => receipt.billItems),
      customerName: hasUdhaar
        ? receipts.find((receipt) => receipt.paymentMode === 'udhaar')?.customerName
        : 'Walk-in Customer',
      paymentMode: hasUdhaar ? 'udhaar' : 'cash',
      customerBalance: hasUdhaar
        ? receipts.filter((receipt) => receipt.paymentMode === 'udhaar')
            .reduce((sum, receipt) => sum + Number(receipt.customerBalance || 0), 0)
        : 0,
    });
  };

  return (
    <section className="mt-7">
      <div className="flex justify-between items-center mb-3">
        <div>
          <h3 className="text-base font-bold text-stone-900 flex items-center space-x-2">
            <span></span>
            <span>{t.ledgerTitle}</span>
          </h3>
          <p className="text-xs text-[#78716C]">All registered counter transactions, sales, and credit logs</p>
        </div>
        <span className="text-xs font-mono font-bold bg-[#FEF3C7] text-[#92400E] px-2.5 py-1 rounded-lg border border-[#FDE68A] shadow-2xs">
          {transactions.length} Records
        </span>
      </div>
      {selectedReceipts.length > 0 && (
        <div className="mb-3 flex items-center justify-end gap-2">
          <span className="text-xs font-semibold text-[#78716C]">
            {selectedReceipts.length} receipt{selectedReceipts.length === 1 ? '' : 's'} selected
          </span>
          <button
            type="button"
            onClick={handleCombinedBill}
            className="px-3 py-1.5 text-xs bg-[#991B1B] hover:bg-[#7F1D1D] text-white rounded-lg font-bold transition-all"
          >
            Combine receipts
          </button>
        </div>
      )}

      <div className="bg-[#FFFDF9] rounded-xl overflow-y-auto max-h-80 border border-[#E2D9C8] shadow-xs custom-scrollbar">
        <table className="w-full min-w-[760px] text-left text-sm text-stone-700">
          <thead className="bg-[#F4EFE6] text-[#57534E] uppercase text-[11px] tracking-wider sticky top-0 border-b border-[#E2D9C8] font-bold z-10">
            <tr>
              <th className="px-3 py-2.5 text-center">Select</th>
              <th className="px-4 py-2.5">{t.ledgerDate}</th>
              <th className="px-4 py-2.5">{t.ledgerType}</th>
              <th className="px-4 py-2.5">{t.ledgerEntity}</th>
              <th className="px-4 py-2.5 text-right">{t.ledgerQuantity}</th>
              <th className="px-4 py-2.5 text-right">{t.ledgerAmount}</th>
              <th className="px-4 py-2.5">{t.ledgerDetails}</th>
              <th className="px-3 py-2.5 text-center">Receipt</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#F0EAE0]">
            {transactions.length === 0 ? (
              <tr>
                <td colSpan="8" className="px-4 py-8 text-center text-[#78716C] italic text-xs">
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
                  <tr key={transaction.TxnID} className="hover:bg-[#FAF6EE] transition-colors">
                    <td className="px-3 py-2.5 text-center">
                      {supportsReceipt(transaction) ? (
                        <input
                          type="checkbox"
                          checked={selectedReceipts.includes(transaction.TxnID)}
                          onChange={() => toggleReceipt(transaction.TxnID)}
                          aria-label={`Select receipt for transaction ${transaction.TxnID}`}
                          className="h-4 w-4 accent-[#991B1B] cursor-pointer"
                        />
                      ) : (
                        <span className="text-stone-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 whitespace-nowrap text-xs text-[#78716C] font-mono">
                      {transaction.Timestamp
                        ? new Date(`${transaction.Timestamp.replace(' ', 'T')}Z`).toLocaleString('en-IN', {
                            day: '2-digit',
                            month: 'short',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : '—'}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-bold inline-block ${
                          isSale
                            ? 'bg-emerald-50 text-emerald-800 border border-emerald-300'
                            : isCredit
                            ? 'bg-red-50 text-red-800 border border-red-300'
                            : isRestock
                            ? 'bg-stone-100 text-stone-800 border border-stone-300'
                            : isRepay
                            ? 'bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]'
                            : 'bg-stone-100 text-stone-700'
                        }`}
                      >
                        {transaction.TransactionType}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 font-semibold text-stone-900">{transaction.EntityName || '—'}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-stone-700">{transaction.Quantity ?? '—'}</td>
                    <td className="px-4 py-2.5 text-right whitespace-nowrap font-mono font-bold">
                      <span
                        className={
                          isSale || isRepay
                            ? 'text-emerald-700'
                            : isRestock
                            ? 'text-stone-800'
                            : isCredit
                            ? 'text-red-700'
                            : 'text-stone-700'
                        }
                      >
                        {isSale || isRepay ? '+' : ''}
                        {isRestock && Number(transaction.TotalAmount) < 0 ? '−' : ''}
                        ₹{Math.abs(Number(transaction.TotalAmount || 0)).toLocaleString('en-IN')}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 max-w-xs truncate text-xs text-[#78716C]" title={transaction.CommandText || ''}>
                      {transaction.CommandText || '—'}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {(isSale || isRestock || isCredit) ? (
                        <button
                          onClick={() => handleRowBill(transaction)}
                          className="px-2.5 py-1 text-xs bg-[#FFFDF7] hover:bg-[#991B1B] text-stone-800 hover:text-white rounded-md border border-[#D8CEBA] hover:border-[#991B1B] font-bold transition-all shadow-2xs"
                          title="Generate printable invoice receipt"
                        >
                           Bill
                        </button>
                      ) : (
                        <span className="text-stone-400 text-xs">—</span>
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
