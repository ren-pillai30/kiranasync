import { motion, AnimatePresence } from 'framer-motion';

export default function ArchivesModal({
  showArchives,
  onClose,
  archives,
  archivesError,
  lang,
}) {
  return (
    <AnimatePresence>
      {showArchives && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98 }}
          className="w-full max-w-6xl bg-[#FAF7F2] border-2 border-[#991B1B] rounded-2xl p-7 shadow-2xl pointer-events-auto max-h-[85vh] overflow-y-auto text-stone-900 select-none"
        >
          <div className="flex items-center justify-between mb-5 pb-3 border-b border-[#E2D9C8]">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl p-1 rounded-md bg-[#FEF3C7]"></span>
                <h2 className="text-xl font-black text-stone-900">
                  {lang === 'hi' ? 'हटाए गए आइटम का ऑडिट' : 'Removal Archive & Audit'}
                </h2>
              </div>
              <p className="text-xs text-[#78716C] mt-0.5 font-medium">
                {lang === 'hi'
                  ? 'सभी हटाए गए उत्पादों और ग्राहकों का रिकॉर्ड'
                  : 'Audit history for removed products and customers'}
              </p>
            </div>
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 bg-[#FFFDF9] hover:bg-[#F4EFE6] text-stone-800 rounded-lg text-xs font-bold border border-[#D8CEBA] shadow-2xs transition-all"
            >
              {lang === 'hi' ? 'डैशबोर्ड पर वापस' : 'Back to dashboard'}
            </button>
          </div>
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
                  <th className="px-4 py-2.5 text-right">
                    {lang === 'hi' ? 'बाकी उधार' : 'Balance at removal'}
                  </th>
                  <th className="px-4 py-2.5">{lang === 'hi' ? 'कमांड' : 'Command'}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F0EAE0]">
                {archives.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="px-4 py-8 text-center text-[#78716C] italic text-xs">
                      {lang === 'hi'
                        ? 'अभी तक कोई हटाने का रिकॉर्ड नहीं है।'
                        : 'No removal records yet.'}
                    </td>
                  </tr>
                ) : (
                  archives.map((record) => (
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
                        {record.Balance === null
                          ? '—'
                          : `₹${Number(record.Balance).toLocaleString('en-IN')}`}
                      </td>
                      <td className="px-4 py-2.5 max-w-sm break-words text-[#78716C]">{record.RawCommand || '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
