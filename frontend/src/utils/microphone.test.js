import assert from 'node:assert/strict';
import test from 'node:test';
import { acquireMicrophoneStream } from './microphone.js';

const namedError = (name) => Object.assign(new Error(name), { name });

test('acquireMicrophoneStream uses the default audio input when available', async () => {
  const stream = { id: 'default' };
  const getUserMedia = async () => stream;

  assert.equal(await acquireMicrophoneStream({ getUserMedia }), stream);
});

test('acquireMicrophoneStream retries available inputs when the default is missing', async () => {
  const stream = { id: 'built-in' };
  const constraints = [];
  const mediaDevices = {
    getUserMedia: async (constraint) => {
      constraints.push(constraint);
      if (constraints.length === 1) throw namedError('NotFoundError');
      return stream;
    },
    enumerateDevices: async () => [
      { kind: 'videoinput', deviceId: 'camera' },
      { kind: 'audioinput', deviceId: 'built-in' },
    ],
  };

  assert.equal(await acquireMicrophoneStream(mediaDevices), stream);
  assert.deepEqual(constraints, [
    { audio: true },
    { audio: { deviceId: { exact: 'built-in' } } },
  ]);
});

test('acquireMicrophoneStream does not retry when access is denied', async () => {
  let enumerateCalled = false;
  const mediaDevices = {
    getUserMedia: async () => {
      throw namedError('NotAllowedError');
    },
    enumerateDevices: async () => {
      enumerateCalled = true;
      return [];
    },
  };

  await assert.rejects(
    acquireMicrophoneStream(mediaDevices),
    (error) => error.name === 'NotAllowedError'
  );
  assert.equal(enumerateCalled, false);
});
