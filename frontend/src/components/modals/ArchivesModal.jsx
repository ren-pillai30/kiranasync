import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  buildTransactionsCsv,
  groupTransactionsByDay,
} from '../../utils/transactionArchive';

const downloadTransactions = (transactions, filename) => {
  const blob = new Blob([buildTransactionsCsv(transactions)], {
    type: 'text/csv;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};

const formatDay = (date, lang) => new Date(`${date}T00:00:00`).toLocaleDateString(
  lang === 'hi' ? 'hi-IN' : 'en-IN',
  { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }
);

export default function ArchivesModal({
  showArchives,
  onClose,
  archives,
  archivesError,
  transactions,
  lang,
}) {
  const [activeTab, setActiveTab] = useState('transactions');
  const [selectedDays, setSelectedDays] = useState([]);
  const transactionDays = useMemo(
    () => groupTransactionsByDay(transactions),
    [transactions]
  );
  const allDates = transactionDays.map(({ date }) => date);
  const selectedTransactions = transactionDays
    .filter(({ date }) => selectedDays.includes(date))
    .flatMap(({ records }) => records);

  const toggleDay = (date) => {
    setSelectedDays((current) => current.includes(date)
      ? current.filter((selected) => selected !== date)
      : [...current, date]);
  };

  const toggleAllDays = () => {
    setSelectedDays((current) => (
      allDates.length > 0 && allDates.every((date) => current.includes(date))
        ? []
        : allDates
    ));
  };

  return (
    <AnimatePresence>
      {showArchives && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98 }}
          className="w-full max-w-6xl bg-[#FAF7F2] border-2 border-[#991B1B] rounded-2xl p-4 sm:p-7 shadow-2xl pointer-events-auto max-h-[85vh] overflow-y-auto text-stone-900"
        >
          <div className="flex items-center justify-between mb-5 pb-3 border-b border-[#E2D9C8]">
            <div>
              <h2 className="text-xl font-black text-stone-900">
                {lang === 'hi' ? 'आर्काइव' : 'Archives'}
              </h2>
              <p className="text-xs text-[#78716C] mt-0.5 font-medium">
                {lang === 'hi'
                  ? 'दिन के अनुसार लेन-देन देखें और CSV डाउनलोड करें'
                  : 'Review transactions by day and download CSV reports'}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 bg-[#FFFDF9] hover:bg-[#F4EFE6] text-stone-800 rounded-lg text-xs font-bold border border-[#D8CEBA] shadow-2xs transition-all"
            >
              {lang === 'hi' ? 'डैशबोर्ड पर वापस' : 'Back to dashboard'}
            </button>
          </div>

          <div className="flex gap-2 mb-4 border-b border-[#E2D9C8]">
            <button
              type="button"
              onClick={() => setActiveTab('transactions')}
              className={`px-3 py-2 text-xs font-bold border-b-2 ${
                activeTab === 'transactions'
                  ? 'border-[#991B1B] text-[#991B1B]'
                  : 'border-transparent text-stone-500'
              }`}
            >
              {lang === 'hi' ? 'लेन-देन' : 'Transactions'}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('removals')}
              className={`px-3 py-2 text-xs font-bold border-b-2 ${
                activeTab === 'removals'
                  ? 'border-[#991B1B] text-[#991B1B]'
                  : 'border-transparent text-stone-500'
              }`}
            >
              {lang === 'hi' ? 'हटाने का ऑडिट' : 'Removal audit'}
            </button>
          </div>

          {activeTab === 'transactions' ? (
            <section>
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <label className="flex items-center gap-2 text-xs font-semibold text-stone-700">
                  <input
                    type="checkbox"
                    checked={allDates.length > 0 && allDates.every((date) => selectedDays.includes(date))}
                    onChange={toggleAllDays}
                    className="h-4 w-4 accent-[#991B1B]"
                  />
                  {lang === 'hi' ? 'सभी दिन चुनें' : 'Select all days'}
                </label>
                <button
                  type="button"
                  disabled={!selectedTransactions.length}
                  onClick={() => downloadTransactions(selectedTransactions, 'transactions-selected-days.csv')}
                  className="px-3.5 py-2 rounded-lg bg-[#991B1B] text-white text-xs font-bold disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {lang === 'hi' ? 'चुने हुए दिन CSV डाउनलोड करें' : 'Download selected days CSV'}
                </button>
              </div>

              {transactionDays.length === 0 ? (
                <p className="rounded-xl border border-[#E2D9C8] bg-[#FFFDF9] p-8 text-center text-sm text-[#78716C]">
                  {lang === 'hi' ? 'अभी कोई लेन-देन रिकॉर्ड नहीं है।' : 'No transactions have been recorded yet.'}
                </p>
              ) : (
                <div className="space-y-4 max-h-[62vh] overflow-y-auto custom-scrollbar">
                  {transactionDays.map(({ date, records }) => {
                    const salesTotal = records.reduce((sum, record) => (
                      ['Sale', 'UdhaarSale'].includes(record.TransactionType)
                        ? sum + Number(record.TotalAmount || 0)
                        : sum
                    ), 0);
                    return (
                      <section
                        key={date}
                        className="rounded-xl border border-[#E2D9C8] bg-[#FFFDF9] overflow-hidden"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-[#F4EFE6] border-b border-[#E2D9C8]">
                          <label className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={selectedDays.includes(date)}
                              onChange={() => toggleDay(date)}
                              className="h-4 w-4 accent-[#991B1B]"
                            />
                            <span className="font-bold text-sm text-stone-900">{formatDay(date, lang)}</span>
                            <span className="text-[11px] text-stone-500">
                              {records.length} {lang === 'hi' ? 'लेन-देन' : 'transactions'}
                              {' · '}₹{salesTotal.toLocaleString('en-IN')}
                            </span>
                          </label>
                          <button
                            type="button"
                            onClick={() => downloadTransactions(records, `transactions-${date}.csv`)}
                            className="px-3 py-1.5 rounded-lg border border-[#D8CEBA] bg-white text-xs font-bold text-stone-700 hover:bg-stone-100"
                          >
                            {lang === 'hi' ? 'इस दिन का CSV' : 'Download day CSV'}
                          </button>
                        </div>
                        <div className="overflow-x-auto">
                          <table className="w-full min-w-[720px] text-left text-xs text-stone-700">
                            <thead className="text-[10px] uppercase text-stone-500 border-b border-[#F0EAE0]">
                              <tr>
                                <th className="px-3 py-2">{lang === 'hi' ? 'समय' : 'Time'}</th>
                                <th className="px-3 py-2">{lang === 'hi' ? 'प्रकार' : 'Type'}</th>
                                <th className="px-3 py-2">{lang === 'hi' ? 'नाम' : 'Product / customer'}</th>
                                <th className="px-3 py-2 text-right">{lang === 'hi' ? 'मात्रा' : 'Quantity'}</th>
                                <th className="px-3 py-2 text-right">{lang === 'hi' ? 'राशि' : 'Amount'}</th>
                                <th className="px-3 py-2">{lang === 'hi' ? 'कमांड' : 'Command'}</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-[#F0EAE0]">
                              {records.map((record) => (
                                <tr key={`${date}-${record.TxnID}`} className="align-top">
                                  <td className="px-3 py-2 whitespace-nowrap font-mono">
                                    {record.Timestamp
                                      ? new Date(`${record.Timestamp.replace(' ', 'T')}Z`).toLocaleTimeString(
                                          lang === 'hi' ? 'hi-IN' : 'en-IN',
                                          { hour: '2-digit', minute: '2-digit' }
                                        )
                                      : '—'}
                                  </td>
                                  <td className="px-3 py-2 font-semibold">{record.TransactionType}</td>
                                  <td className="px-3 py-2">{record.EntityName || '—'}</td>
                                  <td className="px-3 py-2 text-right font-mono">{record.Quantity ?? '—'}</td>
                                  <td className="px-3 py-2 text-right font-mono font-bold">
                                    ₹{Number(record.TotalAmount || 0).toLocaleString('en-IN')}
                                  </td>
                                  <td className="px-3 py-2 max-w-xs break-words text-stone-500">
                                    {record.CommandText || '—'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </section>
                    );
                  })}
                </div>
              )}
            </section>
          ) : (
            <>
              {archivesError && (
                <p
                  role="alert"
                  className="mb-4 rounded-xl border border-red-300 bg-red-50 p-3 text-xs text-red-900 font-semibold"
                >
                  {archivesError}
                </p>
              )}
              <div className="bg-[#FFFDF9] rounded-xl overflow-y-auto max-h-[65vh] border border-[#E2D9C8] shadow-xs custom-scrollbar">
                <table className="w-full min-w-[900px] text-left text-xs text-stone-700">
                  <thead className="bg-[#F4EFE6] text-[#57534E] uppercase sticky top-0 text-[11px] font-bold border-b border-[#E2D9C8] z-10">
                    <tr>
                      <th className="px-4 py-2.5">{lang === 'hi' ? 'हटाने का समय' : 'Removed at'}</th>
                      <th className="px-4 py-2.5">{lang === 'hi' ? 'प्रकार' : 'Type'}</th>
                      <th className="px-4 py-2.5">{lang === 'hi' ? 'नाम' : 'Name'}</th>
                      <th className="px-4 py-2.5">{lang === 'hi' ? 'कार्रवाई' : 'Action'}</th>
                      <th className="px-4 py-2.5">{lang === 'hi' ? 'कारण' : 'Reason'}</th>
                      <th className="px-4 py-2.5 text-right">{lang === 'hi' ? 'मात्रा' : 'Quantity'}</th>
                      <th className="px-4 py-2.5 text-right">{lang === 'hi' ? 'बाकी उधार' : 'Balance at removal'}</th>
                      <th className="px-4 py-2.5">{lang === 'hi' ? 'कमांड' : 'Command'}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#F0EAE0]">
                    {archives.length === 0 ? (
                      <tr>
                        <td colSpan="8" className="px-4 py-8 text-center text-[#78716C] italic text-xs">
                          {lang === 'hi' ? 'अभी तक कोई हटाने का रिकॉर्ड नहीं है।' : 'No removal records yet.'}
                        </td>
                      </tr>
                    ) : archives.map((record) => (
                      <tr key={record.ArchiveID} className="hover:bg-[#FAF6EE] transition-colors align-top">
                        <td className="px-4 py-2.5 whitespace-nowrap font-mono text-[#78716C]">
                          {record.RemovedAt
                            ? new Date(`${record.RemovedAt.replace(' ', 'T')}Z`).toLocaleString()
                            : '—'}
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="px-2 py-0.5 rounded-md bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] font-bold text-[10px]">
                            {record.EntityType}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 font-bold text-stone-900">{record.EntityName}</td>
                        <td className="px-4 py-2.5 font-medium">{record.RemovalType}</td>
                        <td className="px-4 py-2.5 text-[#78716C]">{record.Reason || '—'}</td>
                        <td className="px-4 py-2.5 text-right font-mono font-bold text-stone-900">{record.Quantity ?? '—'}</td>
                        <td className="px-4 py-2.5 text-right font-mono font-bold text-red-700">
                          {record.Balance === null ? '—' : `₹${Number(record.Balance).toLocaleString('en-IN')}`}
                        </td>
                        <td className="px-4 py-2.5 max-w-sm break-words text-[#78716C]">{record.RawCommand || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
