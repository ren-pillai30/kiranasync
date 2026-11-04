import { AnimatePresence, motion } from 'framer-motion';
import { getEntityName } from '../../utils/entityNames';

export default function TransactionConfirmModal({
  pendingTransaction,
  onConfirm,
  onCancel,
  confirmationError,
  inventory = [],
  credit = [],
  nameDisplayMode = 'en',
}) {
  if (!pendingTransaction) return null;

  const isCredit = pendingTransaction.Intent === 'credit';
  const customer = credit.find((entry) => entry.CustomerName === pendingTransaction.CustomerName);
  const item = inventory.find((entry) => entry.ItemName === pendingTransaction.ItemName);
  const customerName = customer ? getEntityName(customer, nameDisplayMode, 'CustomerName', 'CustomerNameHindi') : pendingTransaction.CustomerName;
  const itemName = item ? getEntityName(item, nameDisplayMode) : pendingTransaction.ItemName;
  const summary = isCredit
    ? `Add Rs ${pendingTransaction.Amount} to ${customerName}?`
    : pendingTransaction.Intent === 'sell'
      ? `Sell ${pendingTransaction.Quantity} ${itemName}?`
      : `Restock ${pendingTransaction.Quantity} ${itemName}?`;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <motion.div
          role="dialog"
          aria-modal="true"
          className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl"
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
        >
          <h2 className="text-lg font-bold text-stone-900">Confirm transaction</h2>
          <p className="mt-3 text-sm text-stone-700">{summary}</p>
          {confirmationError && (
            <p className="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700">{confirmationError}</p>
          )}
          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onConfirm}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white"
            >
              Confirm
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
