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
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="w-full max-w-6xl bg-gray-900/95 backdrop-blur-xl border border-gray-700 rounded-2xl p-8 shadow-2xl pointer-events-auto max-h-[85vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-white">
                {lang === 'hi' ? 'हटाए गए आइटम का ऑडिट' : 'Removal Archive & Audit'}
              </h2>
              <p className="text-sm text-gray-400 mt-1">
                {lang === 'hi'
                  ? 'सभी हटाए गए उत्पादों और ग्राहकों का रिकॉर्ड'
                  : 'Audit history for removed products and customers'}
              </p>
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium"
            >
              {lang === 'hi' ? 'डैशबोर्ड पर वापस' : 'Back to dashboard'}
            </button>
          </div>
          {archivesError && (
            <p
              role="alert"
              className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300"
            >
              {archivesError}
            </p>
          )}
          <div className="bg-gray-800 rounded-xl overflow-auto border border-gray-700 max-h-[65vh]">
            <table className="w-full min-w-[900px] text-left text-sm text-gray-300">
              <thead className="bg-gray-700/70 text-gray-400 uppercase sticky top-0">
                <tr>
                  <th className="px-4 py-3">{lang === 'hi' ? 'हटाने का समय' : 'Removed at'}</th>
                  <th className="px-4 py-3">{lang === 'hi' ? 'प्रकार' : 'Type'}</th>
                  <th className="px-4 py-3">{lang === 'hi' ? 'नाम' : 'Name'}</th>
                  <th className="px-4 py-3">{lang === 'hi' ? 'कार्रवाई' : 'Action'}</th>
                  <th className="px-4 py-3">{lang === 'hi' ? 'कारण' : 'Reason'}</th>
                  <th className="px-4 py-3 text-right">{lang === 'hi' ? 'मात्रा' : 'Quantity'}</th>
                  <th className="px-4 py-3 text-right">
                    {lang === 'hi' ? 'बाकी उधार' : 'Balance at removal'}
                  </th>
                  <th className="px-4 py-3">{lang === 'hi' ? 'कमांड' : 'Command'}</th>
                </tr>
              </thead>
              <tbody>
                {archives.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="px-4 py-10 text-center text-gray-500">
                      {lang === 'hi'
                        ? 'अभी तक कोई हटाने का रिकॉर्ड नहीं है।'
                        : 'No removal records yet.'}
                    </td>
                  </tr>
                ) : (
                  archives.map((record) => (
                    <tr key={record.ArchiveID} className="border-t border-gray-700/50 align-top">
                      <td className="px-4 py-3 whitespace-nowrap">
                        {record.RemovedAt
                          ? new Date(`${record.RemovedAt.replace(' ', 'T')}Z`).toLocaleString()
                          : '—'}
                      </td>
                      <td className="px-4 py-3">{record.EntityType}</td>
                      <td className="px-4 py-3 font-medium text-white">{record.EntityName}</td>
                      <td className="px-4 py-3">{record.RemovalType}</td>
                      <td className="px-4 py-3">{record.Reason || '—'}</td>
                      <td className="px-4 py-3 text-right">{record.Quantity ?? '—'}</td>
                      <td className="px-4 py-3 text-right">
                        {record.Balance === null
                          ? '—'
                          : `₹${Number(record.Balance).toLocaleString('en-IN')}`}
                      </td>
                      <td className="px-4 py-3 max-w-sm break-words">{record.RawCommand || '—'}</td>
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
