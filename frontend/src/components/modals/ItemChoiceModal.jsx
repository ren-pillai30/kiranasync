import { motion, AnimatePresence } from 'framer-motion';

export default function ItemChoiceModal({
  pendingItemChoice,
  selectedItemId,
  setSelectedItemId,
  confirmationError,
  submitItemChoice,
  onCancel,
  t,
}) {
  return (
    <AnimatePresence>
      {pendingItemChoice && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm pointer-events-auto p-4"
        >
          <motion.div
            initial={{ scale: 0.95, y: 16 }}
            animate={{ scale: 1, y: 0 }}
            className="bg-gray-800 border border-amber-500/50 p-6 rounded-2xl shadow-2xl w-full max-w-[440px] max-h-[85vh] overflow-y-auto"
          >
            <h3 className="text-xl font-bold text-white mb-2">{t.selectProductTitle}</h3>
            <p className="text-gray-400 text-sm mb-5">{t.selectProductDesc}</p>
            <p className="text-sm text-gray-300 mb-3">
              {pendingItemChoice.Intent === 'sell' ? 'Sale' : 'Restock'} · {pendingItemChoice.Quantity}
            </p>
            <div className="space-y-2">
              {pendingItemChoice.Candidates.map((item) => (
                <label
                  key={item.ItemID}
                  className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer ${
                    selectedItemId === item.ItemID
                      ? 'border-amber-400 bg-amber-400/10'
                      : 'border-gray-700 bg-gray-700/40'
                  }`}
                >
                  <input
                    type="radio"
                    name="inventory-variant"
                    value={item.ItemID}
                    checked={selectedItemId === item.ItemID}
                    onChange={() => setSelectedItemId(item.ItemID)}
                    className="mt-1 accent-amber-400"
                  />
                  <span className="flex-1">
                    <span className="block font-semibold text-white">{item.ItemName}</span>
                    <span className="block text-sm text-gray-400">
                      ₹{Number(item.Price).toLocaleString('en-IN')} · {t.availableStock}:{' '}
                      {item.StockQuantity}
                    </span>
                  </span>
                </label>
              ))}
            </div>
            {confirmationError && (
              <p role="alert" className="text-sm text-red-400 mt-4">
                {confirmationError}
              </p>
            )}
            <div className="flex gap-3 mt-6">
              <button
                onClick={onCancel}
                className="w-1/3 py-3 rounded-xl bg-gray-700 hover:bg-gray-600 text-gray-300 font-medium"
              >
                {t.cancelBtn}
              </button>
              <button
                onClick={submitItemChoice}
                disabled={selectedItemId === null}
                className="flex-1 py-3 rounded-xl bg-amber-600 hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold"
              >
                {t.confirmProduct}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
