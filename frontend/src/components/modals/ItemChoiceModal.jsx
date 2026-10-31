import { motion, AnimatePresence } from 'framer-motion';

export default function ItemChoiceModal({
  pendingItemChoice,
  selectedItemId,
  setSelectedItemId,
  confirmationError,
  submitItemChoice,
  onAddNewProduct,
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
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm pointer-events-auto p-4 cursor-pointer"
          onClick={onCancel}
        >
          <motion.div
            initial={{ scale: 0.95, y: 16 }}
            animate={{ scale: 1, y: 0 }}
            className="relative bg-[#FAF7F2] border-2 border-[#991B1B] p-6 rounded-2xl shadow-2xl w-full max-w-[440px] max-h-[85vh] overflow-y-auto custom-scrollbar text-stone-900 cursor-auto pointer-events-auto"
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

            <h3 className="text-xl font-black text-stone-900 mb-2">{t.selectProductTitle}</h3>
            {pendingItemChoice.MeasurementMismatch && (
              <div className="mb-4 p-3 bg-red-50 border border-red-300 rounded-xl text-red-900 text-xs space-y-1">
                <div className="font-bold flex items-center space-x-1.5 text-red-800">
                  <span>⚠️</span>
                  <span>Exact measurement ({pendingItemChoice.RequestedMeasurement}) is not in stock</span>
                </div>
                <p className="text-red-900/90 font-medium">
                  Other available sizes: <strong className="text-red-950 font-mono">{pendingItemChoice.AvailableMeasurements?.join(', ')}</strong>. Please select an available size.
                </p>
              </div>
            )}
            <p className="text-[#78716C] text-xs mb-4 font-medium">{t.selectProductDesc}</p>
            <p className="text-xs font-bold text-stone-800 mb-2.5 px-2.5 py-1 rounded-md bg-[#FEF3C7] border border-[#FDE68A] inline-block">
              {pendingItemChoice.Intent === 'sell' ? 'Sale' : 'Restock'} · Qty: {pendingItemChoice.Quantity}
            </p>
            <div className="space-y-2">
              {pendingItemChoice.Candidates.map((item) => (
                <label
                  key={item.ItemID}
                  className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                    selectedItemId === item.ItemID
                      ? 'border-2 border-[#991B1B] bg-[#FFFDF9] shadow-xs'
                      : 'border border-[#D8CEBA] bg-[#F4EFE6] hover:bg-[#EAE2D2]'
                  }`}
                >
                  <input
                    type="radio"
                    name="inventory-variant"
                    value={item.ItemID}
                    checked={selectedItemId === item.ItemID}
                    onChange={() => setSelectedItemId(item.ItemID)}
                    className="mt-1 accent-[#991B1B]"
                  />
                  <span className="flex-1">
                    <span className="block font-bold text-stone-900 text-sm">{item.ItemName}</span>
                    <span className="block text-xs font-medium text-[#78716C] mt-0.5">
                      ₹{Number(item.Price).toLocaleString('en-IN')} · {t.availableStock}:{' '}
                      <span className="font-mono font-bold text-stone-800">{item.StockQuantity}</span>
                    </span>
                  </span>
                </label>
              ))}
            </div>
            {pendingItemChoice.AllowNewProduct && onAddNewProduct && (
              <button
                onClick={() => onAddNewProduct(
                  pendingItemChoice.EntityName || pendingItemChoice.RawCommand || '',
                  pendingItemChoice.Quantity || 1
                )}
                className="mt-4 w-full py-2.5 rounded-xl border-2 border-dashed border-[#991B1B]/40 bg-[#FEF3C7] hover:bg-[#FDE68A] text-[#92400E] hover:text-[#78350F] font-bold text-xs transition-all flex items-center justify-center space-x-1.5 shadow-2xs"
              >
                <span>+</span>
                <span>Add as New Product Instead</span>
              </button>
            )}
            {confirmationError && (
              <p role="alert" className="text-xs text-red-600 font-semibold bg-red-50 p-2.5 rounded-lg border border-red-200 mt-3">
                {confirmationError}
              </p>
            )}
            <div className="flex gap-3 mt-6">
              <button
                type="button"
                onClick={onCancel}
                className="w-1/3 py-3 px-4 rounded-xl bg-[#FFFDF9] hover:bg-[#F4EFE6] text-stone-800 font-bold border border-[#D8CEBA] transition-all text-xs shadow-2xs cursor-pointer"
              >
                {t.cancelBtn}
              </button>
              <button
                type="button"
                onClick={submitItemChoice}
                disabled={selectedItemId === null}
                className="flex-1 py-3 px-4 rounded-xl bg-[#991B1B] hover:bg-[#B91C1C] disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-xs shadow-xs transition-all cursor-pointer"
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
