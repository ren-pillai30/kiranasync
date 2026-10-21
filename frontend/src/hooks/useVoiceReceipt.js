import { useRef, useState, useCallback } from 'react';
import { api } from '../services/api';

/**
 * Custom hook to handle voice audio synthesis and playback.
 */
export function useVoiceReceipt({ playbackAudioContextRef, isMuted, lang }) {
  const [voiceError, setVoiceError] = useState('');
  const activeAudioRef = useRef(null);
  const activeAudioSourceRef = useRef(null);

  const stopActiveAudio = useCallback(() => {
    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
    }
    if (activeAudioSourceRef.current) {
      try {
        activeAudioSourceRef.current.stop();
      } catch {
        // Source might already be stopped
      }
      activeAudioSourceRef.current = null;
    }
  }, []);

  const playVoiceReceipt = useCallback(
    async (textToSpeak) => {
      if (isMuted || !textToSpeak) return;
      try {
        setVoiceError('');
        stopActiveAudio();

        const response = await api.synthesizeVoice(textToSpeak, lang === 'hi' ? 'hi-IN' : 'en-IN');
        if (!response.ok) {
          const errorBody = response.headers.get('content-type')?.includes('application/json')
            ? await response.json()
            : await response.text();
          throw new Error(
            typeof errorBody === 'string'
              ? `TTS request failed (${response.status}): ${errorBody.slice(0, 200)}`
              : errorBody.error || `TTS request failed (${response.status})`
          );
        }
        const audioBlob = await response.blob();
        if (!audioBlob.type.startsWith('audio/')) {
          throw new Error(`TTS returned an unexpected response type: ${audioBlob.type || 'unknown'}`);
        }

        const playbackContext = playbackAudioContextRef?.current;
        if (playbackContext) {
          if (playbackContext.state === 'suspended') {
            await playbackContext.resume();
          }
          const audioBuffer = await playbackContext.decodeAudioData(await audioBlob.arrayBuffer());
          const source = playbackContext.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(playbackContext.destination);
          source.onended = () => {
            if (activeAudioSourceRef.current === source) {
              activeAudioSourceRef.current = null;
            }
          };
          activeAudioSourceRef.current = source;
          source.start();
          return;
        }

        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        activeAudioRef.current = audio;
        audio.onended = () => {
          URL.revokeObjectURL(audioUrl);
          if (activeAudioRef.current === audio) {
            activeAudioRef.current = null;
          }
        };
        await audio.play();
      } catch (err) {
        console.error('TTS playback failed:', err);
        setVoiceError(`Could not play the spoken answer: ${err.message}`);
      }
    },
    [isMuted, lang, playbackAudioContextRef, stopActiveAudio]
  );

  return {
    voiceError,
    setVoiceError,
    playVoiceReceipt,
    stopActiveAudio,
  };
}
