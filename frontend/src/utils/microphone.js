export async function acquireMicrophoneStream(mediaDevices = navigator.mediaDevices) {
  if (!mediaDevices?.getUserMedia) {
    throw new Error('Microphone capture is unavailable');
  }

  try {
    return await mediaDevices.getUserMedia({ audio: true });
  } catch (initialError) {
    if (
      !['NotFoundError', 'NotReadableError'].includes(initialError?.name) ||
      !mediaDevices.enumerateDevices
    ) {
      throw initialError;
    }

    let audioInputs = [];
    try {
      audioInputs = (await mediaDevices.enumerateDevices())
        .filter((device) => device.kind === 'audioinput' && device.deviceId)
        .map((device) => device.deviceId);
    } catch (error) {
      console.warn('Could not enumerate audio input devices:', error);
    }

    let lastError = initialError;
    for (const deviceId of audioInputs) {
      try {
        return await mediaDevices.getUserMedia({
          audio: { deviceId: { exact: deviceId } },
        });
      } catch (error) {
        lastError = error;
        if (['NotAllowedError', 'SecurityError'].includes(error?.name)) {
          throw error;
        }
        if (
          !['NotFoundError', 'NotReadableError', 'OverconstrainedError'].includes(
            error?.name
          )
        ) {
          throw error;
        }
      }
    }

    throw lastError;
  }
}
