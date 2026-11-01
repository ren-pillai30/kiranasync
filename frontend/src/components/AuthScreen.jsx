import { useState } from 'react';
import { api } from '../services/api';

export default function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({
    store_name: '',
    display_name: '',
    email: '',
    password: '',
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
      if (mode === 'login') {
        await api.login(form.email, form.password);
      } else {
        await api.registerOwner(form);
      }
      onAuthenticated();
    } catch (submissionError) {
      setError(submissionError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl bg-white p-7 shadow-2xl">
        <h1 className="text-2xl font-bold text-slate-900">KiranaSync</h1>
        <p className="mt-1 text-sm text-slate-500">
          {mode === 'login' ? 'Sign in to your store' : 'Create the first store account'}
        </p>

        {mode === 'register' && (
          <>
            <label className="mt-5 block text-sm font-medium text-slate-700">Store name</label>
            <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" name="store_name" value={form.store_name} onChange={update} required />
            <label className="mt-4 block text-sm font-medium text-slate-700">Your name</label>
            <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" name="display_name" value={form.display_name} onChange={update} required />
          </>
        )}

        <label className="mt-5 block text-sm font-medium text-slate-700">Email</label>
        <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" type="email" name="email" value={form.email} onChange={update} required />
        <label className="mt-4 block text-sm font-medium text-slate-700">Password</label>
        <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" type="password" name="password" minLength={mode === 'register' ? 10 : 1} value={form.password} onChange={update} required />

        {error && <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <button disabled={submitting} className="mt-5 w-full rounded-lg bg-emerald-600 px-4 py-2.5 font-semibold text-white disabled:opacity-60">
          {submitting ? 'Please wait...' : mode === 'login' ? 'Sign in' : 'Create store'}
        </button>
        <button type="button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }} className="mt-4 w-full text-sm font-medium text-emerald-700">
          {mode === 'login' ? 'Create the first store account' : 'Already have an account? Sign in'}
        </button>
      </form>
    </div>
  );
}
