import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export default function App() {
  const [isActive, setIsActive] = useState(false);
  const [transcript, setTranscript] = useState("Listening for voice command...");
  const [dbAction, setDbAction] = useState(null);

  // Simulates frontend audio recording and calling the Flask API endpoint
  const simulateVoiceCommand = async () => {
    setIsActive(true);
    setTranscript("Processing audio via Gnani AI...");
    
    // Simulating response cycle for interface testing
    setTimeout(() => {
      setTranscript("Ramesh ke khaate mein dhai sau rupaye add kar do");
      setDbAction({
        status: "success",
        action: "udhaar_added",
        message: "Added Rs 250 to Ramesh's account."
      });
      
      // Auto-dismiss the floating widget after 5 seconds
      setTimeout(() => {
        setIsActive(false);
        setDbAction(null);
      }, 5000);
    }, 2000);
  };

  return (
    <div className="flex items-end justify-end w-screen h-screen p-6">
      
      {/* Test Trigger Button */}
      {!isActive && (
        <button 
          onClick={simulateVoiceCommand}
          className="absolute top-4 right-4 bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-2 rounded-lg shadow-lg transition-all"
        >
          Test HUD Trigger
        </button>
      )}

      <AnimatePresence>
        {isActive && (
          <motion.div 
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className="w-96 bg-gray-900/90 backdrop-blur-md border border-gray-700/80 rounded-2xl p-5 shadow-2xl"
          >
            {/* Pulsing Status Indicator */}
            <div className="flex items-center space-x-2 mb-3">
              <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                KiranaSync Voice Copilot
              </span>
            </div>

            {/* Transcript Area */}
            <p className="text-base font-semibold text-white mb-4 leading-snug">
              "{transcript}"
            </p>

            {/* Database Action Receipt Badge */}
            {dbAction && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className={`p-3 rounded-xl flex items-center space-x-3 border ${
                  dbAction.status === 'success' 
                    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300' 
                    : 'bg-rose-500/10 border-rose-500/40 text-rose-300'
                }`}
              >
                <span className="text-xl">
                  {dbAction.action === 'udhaar_added' ? '📝' : dbAction.action === 'inventory_updated' ? '📦' : '⚠️'}
                </span>
                <span className="text-sm font-medium">
                  {dbAction.message}
                </span>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}