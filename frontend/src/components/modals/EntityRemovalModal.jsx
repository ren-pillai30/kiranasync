import { motion, AnimatePresence } from 'framer-motion';

export default function EntityRemovalModal({
  pendingRemoval,
  setPendingRemoval,
  confirmationError,
  confirmEntityRemoval,
  onCancel,
}) {
  return (
    <AnimatePresence>
      {pendingRemoval && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm pointer-events-auto p-4 cursor-pointer"
          onClick={onCancel}
        >
          <motion.div
            initial={{ scale: 0.95, y: 16 }}
            animate={{ scale: 1, y: 0 }}
            className="relative bg-[#FAF7F2] border-2 border-[#991B1B] p-6 rounded-2xl shadow-2xl w-full max-w-[440px] text-stone-900 cursor-auto pointer-events-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Top Close Button */}
            <button
              type="button"
              onClick={onCancel}
              className="absolute top-3 right-3 text-stone-400 hover:text-stone-900 text-2xl font-bold w-8 h-8 flex items-center justify-center rounded-lg hover:bg-stone-200/60 transition-all cursor-pointer"
              title="Close"
            >
              &times;
            </button>

            <div className="flex items-center space-x-2 mb-2">
              <span className="text-xl p-1 bg-red-100 rounded-lg">🗑️</span>
              <h3 className="text-xl font-black text-stone-900">Confirm Removal</h3>
            </div>
            <p className="text-stone-700 text-xs mb-3 font-medium leading-relaxed">
              Remove <strong className="text-stone-950 font-bold">{pendingRemoval.EntityName}</strong> from active{' '}
              {pendingRemoval.EntityType === 'Product' ? 'inventory' : 'customers'}?
            </p>
            {pendingRemoval.EntityType === 'Product' ? (
              <div className="text-xs text-red-900 bg-red-50 p-3 rounded-xl border border-red-200 mb-4 font-medium">
                Remaining stock (<strong className="font-mono font-bold">{pendingRemoval.QuantityOrBalance}</strong>) will be set to zero and
                recorded as a write-off. Transaction history will remain.
              </div>
            ) : (
              <div className="text-xs text-red-900 bg-red-50 p-3 rounded-xl border border-red-200 mb-4 font-medium">
                Outstanding balance (₹
                <strong className="font-mono font-bold">
                  {Number(pendingRemoval.QuantityOrBalance || 0).toLocaleString('en-IN')}
                </strong>) and transaction history will be retained.
              </div>
            )}
            <label className="block text-[11px] font-bold uppercase text-[#78716C] mb-1 tracking-wider">Reason (optional)</label>
            <input
              type="text"
              value={pendingRemoval.Reason || ''}
              onChange={(event) =>
                setPendingRemoval((current) => ({
                  ...current,
                  Reason: event.target.value,
                }))
              }
              className="w-full bg-[#FFFDF9] text-stone-900 p-2.5 rounded-xl border border-[#D8CEBA] mb-4 text-sm font-medium focus:outline-none focus:border-[#991B1B] focus:ring-2 focus:ring-[#991B1B]/20"
              placeholder="e.g. expired or recalled"
            />
            {confirmationError && (
              <p role="alert" className="text-xs text-red-600 font-semibold bg-red-50 p-2 rounded border border-red-200 mb-3">
                {confirmationError}
              </p>
            )}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onCancel}
                className="flex-1 py-3 px-4 rounded-xl bg-[#FFFDF9] hover:bg-[#F4EFE6] text-stone-800 font-bold border border-[#D8CEBA] transition-all text-xs shadow-2xs cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmEntityRemoval}
                className="flex-1 py-3 px-4 rounded-xl bg-red-700 hover:bg-red-800 text-white font-bold transition-all text-xs shadow-xs cursor-pointer"
              >
                Confirm Removal
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
