import { useState } from 'react';
import { api } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

export default function AuthScreen({ onAuthenticated }) {
  const resetTokenFromUrl = new URLSearchParams(window.location.hash.slice(1))
    .get('reset_token') || '';
  const [mode, setMode] = useState(resetTokenFromUrl ? 'reset' : 'login');
  const [resetToken, setResetToken] = useState(resetTokenFromUrl);
  const [form, setForm] = useState({
    store_name: '',
    display_name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const update = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    setMessage('');
    try {
      let session = null;
      if (mode === 'login') {
        await api.login(form.email, form.password);
      } else if (mode === 'register') {
        await api.registerOwner(form);
      } else if (mode === 'request_reset') {
        const response = await api.requestPasswordReset(form.email);
        setMessage(response.message);
        return;
      } else {
        if (form.password !== form.confirmPassword) {
          setError('The passwords do not match.');
          return;
        }
        const response = await api.confirmPasswordReset(resetToken, form.password);
        setMessage(response.message);
        setResetToken('');
        window.history.replaceState(
          null,
          '',
          `${window.location.pathname}${window.location.search}`
        );
        setForm((current) => ({ ...current, password: '', confirmPassword: '' }));
        setMode('login');
        return;
      }
      session = await api.getAuthSession();
      onAuthenticated(session);
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
          {mode === 'login'
            ? 'Sign in to your store'
            : mode === 'register'
              ? 'Create your store account'
              : mode === 'request_reset'
                ? 'Reset your password'
                : 'Choose a new password'}
        </p>

        {mode === 'register' && (
          <>
            <label className="mt-5 block text-sm font-medium text-slate-700">Store name</label>
            <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" name="store_name" value={form.store_name} onChange={update} required />
            <label className="mt-4 block text-sm font-medium text-slate-700">Your name</label>
            <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" name="display_name" value={form.display_name} onChange={update} required />
          </>
        )}

        {(mode === 'login' || mode === 'register' || mode === 'request_reset') && (
          <>
            <label className="mt-5 block text-sm font-medium text-slate-700">Email</label>
            <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" type="email" name="email" value={form.email} onChange={update} required />
          </>
        )}
        {mode !== 'request_reset' && (
          <>
            <label className="mt-4 block text-sm font-medium text-slate-700">
              {mode === 'reset' ? 'New password' : 'Password'}
            </label>
            <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" type="password" name="password" minLength={mode === 'login' ? 1 : 10} maxLength={72} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={form.password} onChange={update} required />
            {mode === 'reset' && (
              <>
                <label className="mt-4 block text-sm font-medium text-slate-700">Confirm new password</label>
                <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" type="password" name="confirmPassword" minLength={10} maxLength={72} autoComplete="new-password" value={form.confirmPassword} onChange={update} required />
              </>
            )}
          </>
        )}

        {error && <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {message && <p role="status" className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{message}</p>}
        <button disabled={submitting} className="mt-5 w-full rounded-lg bg-emerald-600 px-4 py-2.5 font-semibold text-white disabled:opacity-60">
          {submitting ? <LoadingSpinner label="Please wait..." /> : mode === 'login' ? 'Sign in' : mode === 'register' ? 'Create store' : mode === 'request_reset' ? 'Send reset link' : 'Save new password'}
        </button>
        {mode === 'login' && (
          <>
            <button type="button" onClick={() => { setMode('request_reset'); setError(''); setMessage(''); }} className="mt-4 w-full text-sm font-medium text-emerald-700">
              Forgot password?
            </button>
            <button type="button" onClick={() => { setMode('register'); setError(''); setMessage(''); }} className="mt-2 w-full text-sm font-medium text-emerald-700">
              Create a store account
            </button>
          </>
        )}
        {(mode === 'register' || mode === 'request_reset' || mode === 'reset') && (
          <button type="button" onClick={() => {
            setMode('login');
            setError('');
            setMessage('');
            if (mode === 'reset') {
              setResetToken('');
              window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
            }
          }} className="mt-4 w-full text-sm font-medium text-emerald-700">
            Back to sign in
          </button>
        )}
      </form>
    </div>
  );
}
