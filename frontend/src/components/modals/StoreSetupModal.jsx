import { useState } from 'react';
import { api } from '../../services/api';

export default function StoreSetupModal({
  initialStore,
  onComplete,
  onClose,
  isRequired = false,
}) {
  const [form, setForm] = useState({
    store_name: initialStore?.store_name || '',
    phone: initialStore?.store_phone || '',
    address: initialStore?.store_address || '',
    city: initialStore?.store_city || '',
    register_opening_balance: String(initialStore?.register_opening_balance ?? 0),
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const update = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const response = await api.completeStoreSetup(form);
      onComplete(response.store);
    } catch (submissionError) {
      setError(submissionError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/70 p-4">
      <form onSubmit={submit} className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-xl font-bold text-slate-900">
          {isRequired ? 'Complete your store setup' : 'Store details and register'}
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          {isRequired
            ? 'This information is required before the system can be used.'
            : 'Update your store details and the cash available at the start of today.'}
        </p>
        {!isRequired && (
          <button
            type="button"
            onClick={onClose}
            className="absolute right-5 top-5 rounded-lg px-2 py-1 text-xl font-bold text-slate-500 hover:bg-slate-100"
            aria-label="Close store settings"
          >
            ×
          </button>
        )}
        {[
          ['store_name', 'Store name', 'text'],
          ['phone', 'Store phone number', 'tel'],
          ['address', 'Store address', 'text'],
          ['city', 'City', 'text'],
        ].map(([name, label, type]) => (
          <label key={name} className="mt-4 block text-sm font-medium text-slate-700">
            {label}
            <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" name={name} type={type} value={form[name]} onChange={update} required />
          </label>
        ))}
        <label className="mt-4 block text-sm font-medium text-slate-700">
          Opening cash in register (₹)
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            name="register_opening_balance"
            type="number"
            min="0"
            step="0.01"
            inputMode="decimal"
            value={form.register_opening_balance}
            onChange={update}
            required
          />
          <span className="mt-1 block text-xs font-normal text-slate-500">
            Added to today’s cash sales and repayments. Update this at the start of each trading day.
          </span>
        </label>
        {error && <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <button disabled={submitting} className="mt-5 w-full rounded-lg bg-emerald-600 px-4 py-3 font-semibold text-white disabled:opacity-60">
          {submitting ? 'Saving...' : isRequired ? 'Save and continue' : 'Save changes'}
        </button>
      </form>
    </div>
  );
}
