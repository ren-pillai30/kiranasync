import { motion, AnimatePresence } from 'framer-motion';

export default function BenchmarkModal({ showEvalModal, onClose, benchmarkData }) {
  return (
    <AnimatePresence>
      {showEvalModal && benchmarkData && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md pointer-events-auto p-4"
        >
          <motion.div
            initial={{ scale: 0.95, y: 15 }}
            animate={{ scale: 1, y: 0 }}
            className="bg-gray-900 border border-violet-500/50 p-6 rounded-2xl shadow-2xl w-full max-w-xl max-h-[85vh] overflow-y-auto text-left"
          >
            <div className="flex justify-between items-center mb-4 border-b border-gray-800 pb-3">
              <div className="flex items-center space-x-2">
                <span className="text-xl">🔬</span>
                <h3 className="text-lg font-bold text-white">Voice AI Lab — Benchmark Results</h3>
              </div>
              <button onClick={onClose} className="text-gray-400 hover:text-white text-lg font-bold">
                &times;
              </button>
            </div>
            <p className="text-xs text-gray-400 mb-3">
              Empirical evaluation across {benchmarkData.TotalSamples} versioned Indic utterances
              with isolated SQLite execution safety audits.
            </p>

            {benchmarkData.Metadata?.LanguageDistribution && (
              <div className="flex flex-wrap gap-2 mb-4">
                {Object.entries(benchmarkData.Metadata.LanguageDistribution).map(([lang, pct]) => (
                  <span
                    key={lang}
                    className="px-2 py-0.5 bg-gray-800 text-gray-300 rounded text-[11px] border border-gray-700"
                  >
                    <strong className="text-violet-400">{lang}:</strong> {pct}
                  </span>
                ))}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 mb-6">
              <div className="bg-gray-800/80 p-3 rounded-xl border border-gray-700/60">
                <span className="text-xs text-gray-400 uppercase tracking-wider block font-semibold">
                  Intent Accuracy
                </span>
                <span className="text-2xl font-bold text-emerald-400">
                  {(benchmarkData.IntentAccuracy * 100).toFixed(1)}%
                </span>
              </div>
              <div className="bg-gray-800/80 p-3 rounded-xl border border-gray-700/60">
                <span className="text-xs text-gray-400 uppercase tracking-wider block font-semibold">
                  Intent Macro-F1
                </span>
                <span className="text-2xl font-bold text-blue-400">
                  {(benchmarkData.IntentMacroF1 * 100).toFixed(1)}%
                </span>
              </div>
              <div className="bg-gray-800/80 p-3 rounded-xl border border-gray-700/60">
                <span className="text-xs text-gray-400 uppercase tracking-wider block font-semibold">
                  Slot Exact Match
                </span>
                <span className="text-2xl font-bold text-violet-400">
                  {(benchmarkData.SlotExactMatchRate * 100).toFixed(1)}%
                </span>
              </div>
              <div className="bg-gray-800/80 p-3 rounded-xl border border-gray-700/60">
                <span className="text-xs text-gray-400 uppercase tracking-wider block font-semibold">
                  Unsafe Write Rate
                </span>
                <span className="text-2xl font-bold text-emerald-400">
                  {(benchmarkData.UnsafeWriteRate * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="bg-gray-800/50 p-4 rounded-xl border border-gray-700/50 mb-4">
              <h4 className="text-xs font-semibold uppercase text-gray-400 mb-2">
                Stage-by-Stage Latency Attribution (p50 / p95)
              </h4>
              {benchmarkData.LatencyBreakdown ? (
                <div className="space-y-1.5 text-xs text-gray-300">
                  <div className="flex justify-between">
                    <span>🎙️ Gnani STT (Offline Sim):</span>
                    <span className="font-mono text-white">
                      {benchmarkData.LatencyBreakdown.MockedSTT?.P50Ms} ms /{' '}
                      {benchmarkData.LatencyBreakdown.MockedSTT?.P95Ms} ms
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>🧠 Structured NLU Interpretation:</span>
                    <span className="font-mono text-white">
                      {benchmarkData.LatencyBreakdown.Interpretation?.P50Ms} ms /{' '}
                      {benchmarkData.LatencyBreakdown.Interpretation?.P95Ms} ms
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>🔒 Domain Revalidation & Atomic DB:</span>
                    <span className="font-mono text-white">
                      {benchmarkData.LatencyBreakdown.ValidationAndDB?.P50Ms} ms /{' '}
                      {benchmarkData.LatencyBreakdown.ValidationAndDB?.P95Ms} ms
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>🔊 Timbre Spoken Receipt (Offline Sim):</span>
                    <span className="font-mono text-white">
                      {benchmarkData.LatencyBreakdown.MockedTTS?.P50Ms} ms /{' '}
                      {benchmarkData.LatencyBreakdown.MockedTTS?.P95Ms} ms
                    </span>
                  </div>
                  <div className="flex justify-between pt-2 border-t border-gray-700/80 font-semibold text-emerald-400">
                    <span>⏱️ Total End-to-End Pipeline:</span>
                    <span className="font-mono">
                      {benchmarkData.LatencyP50Ms} ms (p50) / {benchmarkData.LatencyP95Ms} ms (p95)
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-gray-300">
                  <div className="flex justify-between">
                    <span>Median Pipeline Latency:</span>
                    <span className="font-mono font-bold text-white">
                      {benchmarkData.LatencyP50Ms} ms
                    </span>
                  </div>
                  <div className="flex justify-between mt-1">
                    <span>p95 Latency:</span>
                    <span className="font-mono font-bold text-white">
                      {benchmarkData.LatencyP95Ms} ms
                    </span>
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end">
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-xs font-semibold"
              >
                Close Lab
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

