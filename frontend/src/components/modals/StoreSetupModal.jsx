import { useState } from 'react';
import { api } from '../../services/api';

export default function StoreSetupModal({ initialStore, onComplete }) {
  const [form, setForm] = useState({
    store_name: initialStore?.store_name || '',
    phone: initialStore?.store_phone || '',
    address: initialStore?.store_address || '',
    city: initialStore?.store_city || '',
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
      await api.completeStoreSetup(form);
      onComplete();
    } catch (submissionError) {
      setError(submissionError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/70 p-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <h2 className="text-xl font-bold text-slate-900">Complete your store setup</h2>
        <p className="mt-1 text-sm text-slate-500">This information is required before the system can be used.</p>
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
        {error && <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <button disabled={submitting} className="mt-5 w-full rounded-lg bg-emerald-600 px-4 py-3 font-semibold text-white disabled:opacity-60">
          {submitting ? 'Saving...' : 'Save and continue'}
        </button>
      </form>
    </div>
  );
}
