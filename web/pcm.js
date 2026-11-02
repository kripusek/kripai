'use strict';
// Jedyny akceptowany format wysyłany do API: PCM16, mono, 16 kHz.
function encodeWav(samples) {
  if (samples.length < 4000 || samples.length > 480000) throw Error('audio_length');
  const data = new ArrayBuffer(44 + samples.length * 2), view = new DataView(data);
  const tag = (offset, text) => [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  tag(0, 'RIFF'); view.setUint32(4, data.byteLength - 8, true); tag(8, 'WAVE');
  tag(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, 16000, true); view.setUint32(28, 32000, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); tag(36, 'data');
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((sample, i) => {
    const value = Number.isFinite(sample) ? Math.max(-1, Math.min(1, sample)) : 0;
    view.setInt16(44 + i * 2, Math.round(value * (value < 0 ? 32768 : 32767)), true);
  });
  return data;
}
if (typeof module !== 'undefined') module.exports = {encodeWav};
