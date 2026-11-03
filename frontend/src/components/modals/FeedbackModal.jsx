import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

const CATEGORIES = [
  "General",
  "Voice Recognition",
  "Stock & Inventory",
  "Customer Udhaar",
  "Billing & Invoices",
  "Feature Request",
  "Bug Report",
];

const API_BASE = "http://127.0.0.1:5000/api/feedback";

function StarRating({ rating, onRate, interactive = true, size = "text-2xl" }) {
  const [hovered, setHovered] = useState(0);

  return (
    <div className="flex gap-1.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={!interactive}
          onClick={() => interactive && onRate(star)}
          onMouseEnter={() => interactive && setHovered(star)}
          onMouseLeave={() => interactive && setHovered(0)}
          className={`${size} transition-all duration-150 ${
            interactive ? "cursor-pointer hover:scale-115" : "cursor-default"
          }`}
        >
          <span
            className={
              star <= (hovered || rating)
                ? "text-amber-500"
                : "text-stone-300"
            }
          >
            {star <= (hovered || rating) ? "" : ""}
          </span>
        </button>
      ))}
    </div>
  );
}

function CategoryBadge({ category }) {
  return (
    <span
      className="inline-block px-2.5 py-0.5 text-[11px] font-bold rounded-md border bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]"
    >
      {category}
    </span>
  );
}

export default function FeedbackModal({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState("submit");
  const [rating, setRating] = useState(0);
  const [category, setCategory] = useState("General");
  const [message, setMessage] = useState("");
  const [author, setAuthor] = useState("Store Cashier");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const [feedbackList, setFeedbackList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState("");

  const handleModalClose = useCallback(() => {
    setActiveTab("submit");
    setSuccess(false);
    setError("");
    onClose();
  }, [onClose]);

  const fetchFeedback = useCallback(async () => {
    setLoading(true);
    setFetchError("");
    try {
      const res = await fetch(API_BASE);
      if (!res.ok) throw new Error("Failed to fetch feedback");
      const data = await res.json();
      setFeedbackList(Array.isArray(data) ? data : data.feedback || []);
    } catch (err) {
      setFetchError(err.message || "Could not load feedback history.");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleTabSwitch = (tab) => {
    setActiveTab(tab);
    if (tab === "history") {
      fetchFeedback();
    }
  };

  function resetForm() {
    setRating(0);
    setCategory("General");
    setMessage("");
    setAuthor("Store Cashier");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!message.trim()) {
      setError("Please enter your feedback message.");
      return;
    }
    if (rating === 0) {
      setError("Please select a rating.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const res = await fetch(API_BASE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rating,
          category,
          message: message.trim(),
          author: author.trim() || "Store Cashier",
        }),
      });
      if (!res.ok) throw new Error("Failed to submit feedback");
      setSuccess(true);
      resetForm();
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function formatTimestamp(ts) {
    if (!ts) return "—";
    const date = new Date(ts);
    return date.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 pointer-events-auto"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm cursor-pointer pointer-events-auto"
            onClick={handleModalClose}
          />

          {/* Modal */}
          <motion.div
            className="relative w-full max-w-lg bg-[#FAF7F2] border-2 border-[#991B1B] rounded-2xl shadow-2xl overflow-hidden text-stone-900 pointer-events-auto z-10"
            initial={{ scale: 0.95, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 20 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 bg-[#991B1B] border-b border-[#7F1D1D]">
              <div className="flex items-center space-x-2">
                <span className="text-xl p-1 rounded-md bg-[#FEF3C7]"></span>
                <h2 className="text-lg font-black text-[#FFFDF7]">
                  Store Feedback &amp; Reviews
                </h2>
              </div>
              <button
                type="button"
                onClick={handleModalClose}
                className="text-white hover:text-red-200 transition-colors text-2xl font-bold p-1 rounded-lg hover:bg-red-900/40 cursor-pointer"
              >
                ×
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-[#E2D9C8] bg-[#F4EFE6]">
              <button
                onClick={() => handleTabSwitch("submit")}
                className={`flex-1 px-4 py-3 text-xs font-bold uppercase tracking-wider transition-all ${
                  activeTab === "submit"
                    ? "text-[#991B1B] border-b-2 border-[#991B1B] bg-[#FFFDF9]"
                    : "text-stone-600 hover:text-stone-900 hover:bg-[#FAF7F2]"
                }`}
              >
                Submit Feedback
              </button>
              <button
                onClick={() => handleTabSwitch("history")}
                className={`flex-1 px-4 py-3 text-xs font-bold uppercase tracking-wider transition-all ${
                  activeTab === "history"
                    ? "text-[#991B1B] border-b-2 border-[#991B1B] bg-[#FFFDF9]"
                    : "text-stone-600 hover:text-stone-900 hover:bg-[#FAF7F2]"
                }`}
              >
                Feedback History
              </button>
            </div>

            {/* Content */}
            <div className="p-6 bg-[#FAF7F2]">
              {activeTab === "submit" ? (
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* Success Message */}
                  <AnimatePresence>
                    {success && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="bg-emerald-50 border border-emerald-300 text-emerald-900 px-4 py-3 rounded-xl text-xs font-bold shadow-xs"
                      >
                         Feedback submitted successfully. Thank you!
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Error Message */}
                  {error && (
                    <div className="bg-red-50 border border-red-300 text-red-900 px-4 py-3 rounded-xl text-xs font-bold">
                      {error}
                    </div>
                  )}

                  {/* Rating */}
                  <div>
                    <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1.5">
                      Experience Rating
                    </label>
                    <StarRating rating={rating} onRate={setRating} />
                  </div>

                  {/* Category */}
                  <div>
                    <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1.5">
                      Category
                    </label>
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="w-full bg-[#FFFDF9] border border-[#D8CEBA] text-stone-900 rounded-xl px-3 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 focus:border-[#991B1B] transition-all cursor-pointer"
                    >
                      {CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Message */}
                  <div>
                    <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1.5">
                      Message <span className="text-red-600">*</span>
                    </label>
                    <textarea
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      placeholder="Share your feedback about the store system..."
                      rows={3}
                      required
                      className="w-full bg-[#FFFDF9] border border-[#D8CEBA] text-stone-900 rounded-xl px-3 py-2.5 text-sm placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 focus:border-[#991B1B] transition-all resize-none font-medium"
                    />
                  </div>

                  {/* Author */}
                  <div>
                    <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1.5">
                      Your Name / Cashier ID
                    </label>
                    <input
                      type="text"
                      value={author}
                      onChange={(e) => setAuthor(e.target.value)}
                      placeholder="Store Cashier"
                      className="w-full bg-[#FFFDF9] border border-[#D8CEBA] text-stone-900 rounded-xl px-3 py-2.5 text-sm placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 focus:border-[#991B1B] transition-all font-medium"
                    />
                  </div>

                  {/* Submit */}
                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full bg-[#991B1B] hover:bg-[#B91C1C] disabled:bg-stone-300 disabled:cursor-not-allowed text-white font-bold py-2.5 px-4 rounded-xl text-sm transition-all shadow-xs"
                  >
                    {submitting ? "Submitting..." : "Submit Feedback"}
                  </button>
                </form>
              ) : (
                /* History Tab */
                <div>
                  {loading ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="w-6 h-6 border-2 border-[#991B1B] border-t-transparent rounded-full animate-spin" />
                      <span className="ml-3 text-stone-600 text-sm font-semibold">
                        Loading feedback...
                      </span>
                    </div>
                  ) : fetchError ? (
                    <div className="text-center py-12">
                      <p className="text-red-700 text-sm font-bold">{fetchError}</p>
                      <button
                        onClick={fetchFeedback}
                        className="mt-3 text-[#991B1B] hover:text-[#B91C1C] text-sm underline font-bold"
                      >
                        Try again
                      </button>
                    </div>
                  ) : feedbackList.length === 0 ? (
                    <div className="text-center py-12">
                      <p className="text-stone-400 text-3xl mb-2"></p>
                      <p className="text-stone-700 text-sm font-bold">
                        No feedback submitted yet.
                      </p>
                      <p className="text-stone-500 text-xs mt-1">
                        Be the first to share your thoughts!
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                      {feedbackList.map((item, idx) => (
                        <div
                          key={item.id || idx}
                          className="bg-[#FFFDF9] border border-[#E2D9C8] rounded-xl p-3.5 shadow-2xs"
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <StarRating
                              rating={item.rating || 0}
                              onRate={() => {}}
                              interactive={false}
                              size="text-sm"
                            />
                            <CategoryBadge category={item.category} />
                          </div>
                          <p className="text-stone-800 text-sm leading-relaxed mb-2 font-medium">
                            {item.message}
                          </p>
                          <div className="flex items-center justify-between text-xs text-[#78716C] font-semibold">
                            <span>— {item.author || "Anonymous"}</span>
                            <span>
                              {formatTimestamp(
                                item.timestamp || item.created_at
                              )}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
