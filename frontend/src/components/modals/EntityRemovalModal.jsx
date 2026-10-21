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
          className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 backdrop-blur-sm pointer-events-auto p-4"
        >
          <motion.div
            initial={{ scale: 0.95, y: 16 }}
            animate={{ scale: 1, y: 0 }}
            className="bg-gray-800 border border-red-500/50 p-6 rounded-2xl shadow-2xl w-full max-w-[440px]"
          >
            <h3 className="text-xl font-bold text-white mb-2">Confirm removal</h3>
            <p className="text-gray-300 text-sm mb-3">
              Remove <strong>{pendingRemoval.EntityName}</strong> from active{' '}
              {pendingRemoval.EntityType === 'Product' ? 'inventory' : 'customers'}?
            </p>
            {pendingRemoval.EntityType === 'Product' ? (
              <p className="text-sm text-amber-300 mb-4">
                Remaining stock ({pendingRemoval.QuantityOrBalance}) will be set to zero and
                recorded as a write-off. Transaction history will remain.
              </p>
            ) : (
              <p className="text-sm text-amber-300 mb-4">
                Outstanding balance (₹
                {Number(pendingRemoval.QuantityOrBalance || 0).toLocaleString('en-IN')}) and
                transaction history will be retained.
              </p>
            )}
            <label className="block text-xs text-gray-400 mb-1">Reason (optional)</label>
            <input
              type="text"
              value={pendingRemoval.Reason || ''}
              onChange={(event) =>
                setPendingRemoval((current) => ({
                  ...current,
                  Reason: event.target.value,
                }))
              }
              className="w-full bg-gray-700 text-white p-2 rounded-lg border border-gray-600 mb-4"
              placeholder="e.g. expired or recalled"
            />
            {confirmationError && (
              <p role="alert" className="text-sm text-red-400 mb-3">
                {confirmationError}
              </p>
            )}
            <div className="flex gap-3">
              <button
                onClick={onCancel}
                className="flex-1 py-3 rounded-xl bg-gray-700 hover:bg-gray-600 text-gray-200 font-medium"
              >
                Cancel
              </button>
              <button
                onClick={confirmEntityRemoval}
                className="flex-1 py-3 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold"
              >
                Confirm removal
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

