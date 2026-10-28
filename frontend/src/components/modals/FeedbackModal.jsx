import { useState, useEffect } from "react";
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
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={!interactive}
          onClick={() => interactive && onRate(star)}
          onMouseEnter={() => interactive && setHovered(star)}
          onMouseLeave={() => interactive && setHovered(0)}
          className={`${size} transition-colors duration-150 ${
            interactive ? "cursor-pointer hover:scale-110" : "cursor-default"
          }`}
        >
          <span
            className={
              star <= (hovered || rating)
                ? "text-yellow-400"
                : "text-gray-600"
            }
          >
            {star <= (hovered || rating) ? "★" : "☆"}
          </span>
        </button>
      ))}
    </div>
  );
}

function CategoryBadge({ category }) {
  const colorMap = {
    General: "bg-blue-900/50 text-blue-300 border-blue-700/50",
    "Voice Recognition": "bg-purple-900/50 text-purple-300 border-purple-700/50",
    "Stock & Inventory": "bg-amber-900/50 text-amber-300 border-amber-700/50",
    "Customer Udhaar": "bg-rose-900/50 text-rose-300 border-rose-700/50",
    "Billing & Invoices": "bg-cyan-900/50 text-cyan-300 border-cyan-700/50",
    "Feature Request": "bg-emerald-900/50 text-emerald-300 border-emerald-700/50",
    "Bug Report": "bg-red-900/50 text-red-300 border-red-700/50",
  };

  return (
    <span
      className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full border ${
        colorMap[category] || "bg-gray-800 text-gray-300 border-gray-700"
      }`}
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

  // Fetch feedback history when switching to that tab
  useEffect(() => {
    if (activeTab === "history" && isOpen) {
      fetchFeedback();
    }
  }, [activeTab, isOpen]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setActiveTab("submit");
      setSuccess(false);
      setError("");
    }
  }, [isOpen]);

  async function fetchFeedback() {
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
  }

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
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            className="relative w-full max-w-lg bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden"
            initial={{ scale: 0.95, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 20 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
              <h2 className="text-lg font-semibold text-white">
                Store Feedback
              </h2>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-white transition-colors text-xl leading-none p-1 rounded-lg hover:bg-gray-800"
              >
                ×
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-700">
              <button
                onClick={() => setActiveTab("submit")}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === "submit"
                    ? "text-emerald-400 border-b-2 border-emerald-400 bg-gray-800/50"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/30"
                }`}
              >
                Submit Feedback
              </button>
              <button
                onClick={() => setActiveTab("history")}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === "history"
                    ? "text-emerald-400 border-b-2 border-emerald-400 bg-gray-800/50"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/30"
                }`}
              >
                Feedback History
              </button>
            </div>

            {/* Content */}
            <div className="p-6">
              {activeTab === "submit" ? (
                <form onSubmit={handleSubmit} className="space-y-5">
                  {/* Success Message */}
                  <AnimatePresence>
                    {success && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="bg-emerald-900/40 border border-emerald-700/50 text-emerald-300 px-4 py-3 rounded-lg text-sm"
                      >
                        ✓ Feedback submitted successfully. Thank you!
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Error Message */}
                  {error && (
                    <div className="bg-red-900/40 border border-red-700/50 text-red-300 px-4 py-3 rounded-lg text-sm">
                      {error}
                    </div>
                  )}

                  {/* Rating */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Rating
                    </label>
                    <StarRating rating={rating} onRate={setRating} />
                  </div>

                  {/* Category */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Category
                    </label>
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 text-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-colors appearance-none"
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
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Message <span className="text-red-400">*</span>
                    </label>
                    <textarea
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      placeholder="Share your feedback about the store system..."
                      rows={4}
                      required
                      className="w-full bg-gray-800 border border-gray-700 text-gray-200 rounded-lg px-3 py-2.5 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-colors resize-none"
                    />
                  </div>

                  {/* Author */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Your Name / Cashier ID
                    </label>
                    <input
                      type="text"
                      value={author}
                      onChange={(e) => setAuthor(e.target.value)}
                      placeholder="Store Cashier"
                      className="w-full bg-gray-800 border border-gray-700 text-gray-200 rounded-lg px-3 py-2.5 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-colors"
                    />
                  </div>

                  {/* Submit */}
                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 disabled:cursor-not-allowed text-white font-medium py-2.5 px-4 rounded-lg text-sm transition-colors"
                  >
                    {submitting ? "Submitting..." : "Submit Feedback"}
                  </button>
                </form>
              ) : (
                /* History Tab */
                <div>
                  {loading ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="w-6 h-6 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
                      <span className="ml-3 text-gray-400 text-sm">
                        Loading feedback...
                      </span>
                    </div>
                  ) : fetchError ? (
                    <div className="text-center py-12">
                      <p className="text-red-400 text-sm">{fetchError}</p>
                      <button
                        onClick={fetchFeedback}
                        className="mt-3 text-emerald-400 hover:text-emerald-300 text-sm underline"
                      >
                        Try again
                      </button>
                    </div>
                  ) : feedbackList.length === 0 ? (
                    <div className="text-center py-12">
                      <p className="text-gray-500 text-3xl mb-2">📝</p>
                      <p className="text-gray-400 text-sm">
                        No feedback submitted yet.
                      </p>
                      <p className="text-gray-500 text-xs mt-1">
                        Be the first to share your thoughts!
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-96 overflow-y-auto pr-1 custom-scrollbar">
                      {feedbackList.map((item, idx) => (
                        <div
                          key={item.id || idx}
                          className="bg-gray-800 border border-gray-700 rounded-lg p-4"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <StarRating
                              rating={item.rating || 0}
                              onRate={() => {}}
                              interactive={false}
                              size="text-sm"
                            />
                            <CategoryBadge category={item.category} />
                          </div>
                          <p className="text-gray-300 text-sm leading-relaxed mb-3">
                            {item.message}
                          </p>
                          <div className="flex items-center justify-between text-xs text-gray-500">
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
