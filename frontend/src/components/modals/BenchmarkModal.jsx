import { motion, AnimatePresence } from 'framer-motion';

export default function BenchmarkModal({ showEvalModal, onClose, benchmarkData }) {
  return (
    <AnimatePresence>
      {showEvalModal && benchmarkData && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm pointer-events-auto p-4 cursor-pointer"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, y: 15 }}
            animate={{ scale: 1, y: 0 }}
            className="relative bg-[#FAF7F2] border-2 border-[#991B1B] p-6 rounded-2xl shadow-2xl w-full max-w-xl max-h-[85vh] overflow-y-auto custom-scrollbar text-left text-stone-900 cursor-auto pointer-events-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4 border-b border-[#E2D9C8] pb-3">
              <div className="flex items-center space-x-2">
                <span className="text-xl p-1 rounded-md bg-[#FEF3C7]"></span>
                <h3 className="text-lg font-black text-stone-900">Voice AI Lab — Benchmark Results</h3>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="text-stone-400 hover:text-stone-900 text-2xl font-bold leading-none cursor-pointer p-1 rounded-lg hover:bg-stone-200/60 transition-all"
                title="Close"
              >
                &times;
              </button>
            </div>
            <p className="text-xs text-[#78716C] mb-3">
              Empirical evaluation across {benchmarkData.TotalSamples} versioned Indic utterances
              with isolated SQLite execution safety audits.
            </p>

            {benchmarkData.Metadata?.LanguageDistribution && (
              <div className="flex flex-wrap gap-2 mb-4">
                {Object.entries(benchmarkData.Metadata.LanguageDistribution).map(([lang, pct]) => (
                  <span
                    key={lang}
                    className="px-2 py-0.5 bg-[#FFFDF9] text-stone-800 rounded-md text-[11px] border border-[#D8CEBA] font-semibold"
                  >
                    <strong className="text-[#991B1B]">{lang}:</strong> {pct}
                  </span>
                ))}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 mb-5">
              <div className="bg-[#FFFDF9] p-3.5 rounded-xl border border-[#E2D9C8] shadow-2xs">
                <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-bold">
                  Intent Accuracy
                </span>
                <span className="text-2xl font-black font-mono text-[#991B1B]">
                  {(benchmarkData.IntentAccuracy * 100).toFixed(1)}%
                </span>
              </div>
              <div className="bg-[#FFFDF9] p-3.5 rounded-xl border border-[#E2D9C8] shadow-2xs">
                <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-bold">
                  Intent Macro-F1
                </span>
                <span className="text-2xl font-black font-mono text-stone-900">
                  {(benchmarkData.IntentMacroF1 * 100).toFixed(1)}%
                </span>
              </div>
              <div className="bg-[#FFFDF9] p-3.5 rounded-xl border border-[#E2D9C8] shadow-2xs">
                <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-bold">
                  Slot Exact Match
                </span>
                <span className="text-2xl font-black font-mono text-stone-900">
                  {(benchmarkData.SlotExactMatchRate * 100).toFixed(1)}%
                </span>
              </div>
              <div className="bg-[#FFFDF9] p-3.5 rounded-xl border border-[#E2D9C8] shadow-2xs">
                <span className="text-[10px] text-[#78716C] uppercase tracking-wider block font-bold">
                  Unsafe Write Rate
                </span>
                <span className="text-2xl font-black font-mono text-emerald-700">
                  {(benchmarkData.UnsafeWriteRate * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="bg-[#FFFDF9] p-4 rounded-xl border border-[#E2D9C8] mb-5 shadow-2xs">
              <h4 className="text-xs font-bold uppercase text-stone-700 mb-2.5 tracking-wider">
                Stage-by-Stage Latency Attribution (p50 / p95)
              </h4>
              {benchmarkData.LatencyBreakdown ? (
                <div className="space-y-2 text-xs text-stone-700">
                  <div className="flex justify-between">
                    <span> Gnani STT (Offline Sim):</span>
                    <span className="font-mono text-stone-900 font-bold">
                      {benchmarkData.LatencyBreakdown.MockedSTT?.P50Ms} ms /{' '}
                      {benchmarkData.LatencyBreakdown.MockedSTT?.P95Ms} ms
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span> Structured NLU Interpretation:</span>
                    <span className="font-mono text-stone-900 font-bold">
                      {benchmarkData.LatencyBreakdown.Interpretation?.P50Ms} ms /{' '}
                      {benchmarkData.LatencyBreakdown.Interpretation?.P95Ms} ms
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span> Domain Revalidation &amp; Atomic DB:</span>
                    <span className="font-mono text-stone-900 font-bold">
                      {benchmarkData.LatencyBreakdown.ValidationAndDB?.P50Ms} ms /{' '}
                      {benchmarkData.LatencyBreakdown.ValidationAndDB?.P95Ms} ms
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span> Timbre Spoken Receipt (Offline Sim):</span>
                    <span className="font-mono text-stone-900 font-bold">
                      {benchmarkData.LatencyBreakdown.MockedTTS?.P50Ms} ms /{' '}
                      {benchmarkData.LatencyBreakdown.MockedTTS?.P95Ms} ms
                    </span>
                  </div>
                  <div className="flex justify-between pt-2 border-t border-[#E2D9C8] font-bold text-[#991B1B]">
                    <span>Total End-to-End Pipeline:</span>
                    <span className="font-mono">
                      {benchmarkData.LatencyP50Ms} ms (p50) / {benchmarkData.LatencyP95Ms} ms (p95)
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-stone-700">
                  <div className="flex justify-between">
                    <span>Median Pipeline Latency:</span>
                    <span className="font-mono font-bold text-stone-900">
                      {benchmarkData.LatencyP50Ms} ms
                    </span>
                  </div>
                  <div className="flex justify-between mt-1">
                    <span>p95 Latency:</span>
                    <span className="font-mono font-bold text-stone-900">
                      {benchmarkData.LatencyP95Ms} ms
                    </span>
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2.5 bg-[#991B1B] hover:bg-[#B91C1C] text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer"
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
