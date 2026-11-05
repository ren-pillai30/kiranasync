import { useState } from 'react';
import { api } from '../../services/api';

export default function StoreResetModal({ onClose, onReset }) {
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [isResetting, setIsResetting] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    if (confirmation !== 'RESET') {
      setError('Type RESET exactly to confirm.');
      return;
    }

    setIsResetting(true);
    setError('');
    try {
      const response = await api.resetStore();
      await onReset(response.store);
    } catch (resetError) {
      setError(resetError.message || 'The store could not be reset.');
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/75 p-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-xl font-black text-red-800">Reset store for a demonstration?</h2>
        <p className="mt-3 text-sm text-slate-700">
          This permanently clears all inventory, customer accounts, aliases, pending commands,
          transaction history, and removal audit records for this store. Store details and opening
          register cash will also be cleared. Your sign-in account will remain.
        </p>
        <p className="mt-3 text-sm font-bold text-red-800">
          This cannot be undone. Type RESET to continue.
        </p>
        <input
          autoComplete="off"
          autoCapitalize="characters"
          className="mt-2 w-full rounded-lg border border-red-300 px-3 py-2 text-sm"
          value={confirmation}
          onChange={(event) => setConfirmation(event.target.value)}
          aria-label="Type RESET to confirm"
        />
        {error && (
          <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isResetting}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isResetting || confirmation !== 'RESET'}
            className="rounded-lg bg-red-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
          >
            {isResetting ? 'Resetting...' : 'Reset this store'}
          </button>
        </div>
      </form>
    </div>
  );
}
