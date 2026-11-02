'use strict';
class KripRecorder extends AudioWorkletProcessor {
  constructor() {
    super(); this.frames = 0; this.finished = false;
    this.port.onmessage = event => { if (event.data === 'stop') this.finished = true; };
  }
  process(inputs) {
    if (this.finished) return false;
    const channel = inputs[0]?.[0];
    if (channel) {
      const remaining = Math.max(0, Math.floor(sampleRate * 30) - this.frames);
      const copy = channel.slice(0, remaining);
      this.frames += copy.length;
      this.port.postMessage(copy, [copy.buffer]);
      if (this.frames >= sampleRate * 30) { this.port.postMessage('limit'); this.finished = true; }
    }
    // Wyjście jest ciszą: mikrofon nie wraca do głośników.
    return !this.finished;
  }
}
registerProcessor('krip-recorder', KripRecorder);
