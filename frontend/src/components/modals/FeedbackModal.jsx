import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { api } from '../../services/api';

const CATEGORIES = [
  'General',
  'Voice Recognition',
  'Stock & Inventory',
  'Customer Udhaar',
  'Billing & Invoices',
  'Feature Request',
  'Bug Report',
];

export default function FeedbackModal({ isOpen, onClose }) {
  const [rating, setRating] = useState(0);
  const [category, setCategory] = useState('General');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  const handleClose = () => {
    setRating(0);
    setCategory('General');
    setMessage('');
    setSuccess('');
    setError('');
    onClose();
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!message.trim()) {
      setError('Please enter your feedback message.');
      return;
    }
    if (!rating) {
      setError('Please select a rating.');
      return;
    }

    setSubmitting(true);
    setError('');
    setSuccess('');
    try {
      const response = await api.submitFeedback({
        rating,
        category,
        message: message.trim(),
      });
      setSuccess(response.message);
      setRating(0);
      setCategory('General');
      setMessage('');
    } catch (submitError) {
      setError(submitError.message || 'Feedback could not be sent. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 pointer-events-auto"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <button
            type="button"
            aria-label="Close feedback"
            className="absolute inset-0 bg-black/70 backdrop-blur-sm cursor-pointer"
            onClick={handleClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby="feedback-title"
            className="relative z-10 w-full max-w-lg overflow-hidden rounded-2xl border-2 border-[#991B1B] bg-[#FAF7F2] text-stone-900 shadow-2xl"
            initial={{ scale: 0.95, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 20 }}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-[#7F1D1D] bg-[#991B1B] px-6 py-4">
              <h2 id="feedback-title" className="text-lg font-black text-[#FFFDF7]">
                Private feedback for developers
              </h2>
              <button
                type="button"
                onClick={handleClose}
                aria-label="Close"
                className="rounded-lg p-1 text-2xl font-bold text-white hover:bg-red-900/40"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 p-6">
              <p className="rounded-xl border border-[#E2D9C8] bg-[#FFFDF9] px-3 py-2.5 text-xs leading-relaxed text-stone-600">
                Your feedback is emailed privately to the developers with your
                account and store details. It is not shown to other accounts.
              </p>

              {success && (
                <p role="status" className="rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-xs font-bold text-emerald-900">
                  {success}
                </p>
              )}
              {error && (
                <p role="alert" className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-xs font-bold text-red-900">
                  {error}
                </p>
              )}

              <fieldset>
                <legend className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-stone-700">
                  Experience rating
                </legend>
                <div className="flex gap-1.5">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      aria-label={`${star} star${star === 1 ? '' : 's'}`}
                      aria-pressed={rating === star}
                      onClick={() => setRating(star)}
                      className={`text-2xl transition-colors ${
                        star <= rating ? 'text-amber-500' : 'text-stone-300'
                      }`}
                    >
                      ★
                    </button>
                  ))}
                </div>
              </fieldset>

              <div>
                <label htmlFor="feedback-category" className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-stone-700">
                  Category
                </label>
                <select
                  id="feedback-category"
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                  className="w-full rounded-xl border border-[#D8CEBA] bg-[#FFFDF9] px-3 py-2.5 text-sm font-semibold text-stone-900 focus:border-[#991B1B] focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20"
                >
                  {CATEGORIES.map((entry) => (
                    <option key={entry} value={entry}>{entry}</option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="feedback-message" className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-stone-700">
                  Message <span className="text-red-600">*</span>
                </label>
                <textarea
                  id="feedback-message"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="Share an idea or describe an issue..."
                  rows={4}
                  maxLength={5000}
                  required
                  className="w-full resize-none rounded-xl border border-[#D8CEBA] bg-[#FFFDF9] px-3 py-2.5 text-sm font-medium text-stone-900 placeholder:text-stone-400 focus:border-[#991B1B] focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-xl bg-[#991B1B] px-4 py-2.5 text-sm font-bold text-white shadow-xs transition-all hover:bg-[#B91C1C] disabled:cursor-not-allowed disabled:bg-stone-300"
              >
                {submitting ? 'Sending privately...' : 'Send private feedback'}
              </button>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
