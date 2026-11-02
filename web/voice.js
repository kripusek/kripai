'use strict';
window.KripVoice = (() => {
  let hooks, epoch = 0, capture = null, waiting = false, job = null, aborter = null;
  let player = null, playerUrl = null, finishPlayback = null, blocked = false, processing = false;
  const $ = id => document.getElementById(id);
  const errors = {
    audio_length: 'Nagranie musi trwać od 0,25 do 30 sekund.',
    audio_format: 'Nieprawidłowy format nagrania.',
    stt_not_installed: 'Model głosu nie jest zainstalowany. Uruchom ponownie START.cmd.',
    tts_voice_missing: 'Brak lokalnego głosu w tym języku dostępnego przez System.Speech. Zainstaluj głos Windows; nie używam zamiennika w chmurze.',
    tts_windows_required: 'Odczyt wymaga natywnego Windows.',
    voice_busy: 'Trwa inna operacja głosowa. Poczekaj chwilę.',
    voice_rate_limited: 'Za dużo operacji głosowych. Odczekaj kilka minut.',
    voice_timeout: 'Przetwarzanie głosu trwało zbyt długo. Spróbuj krótszego nagrania.',
    voice_cancelled: 'Głos zatrzymany.',
    speech_not_detected: 'Nie rozpoznano mowy. Spróbuj ponownie bliżej mikrofonu.',
    transcript_too_long: 'Rozpoznany tekst jest za długi. Nagraj krótszą wypowiedź.',
    voice_engine_failed: 'Lokalny silnik głosu nie odpowiedział prawidłowo.',
    gaming_mode: 'Głos jest wyłączony w trybie Gaming.',
    login_required: 'Sesja wygasła. Zaloguj się ponownie.',
    NotAllowedError: 'Zezwól tej stronie na użycie mikrofonu w ustawieniach przeglądarki.',
    NotFoundError: 'Nie znaleziono mikrofonu.',
    NotReadableError: 'Mikrofon jest niedostępny albo używa go inna aplikacja.'
  };
  function report(error) { hooks.notice(errors[error.code || error.name || error.message] || error.message || 'Nie udało się użyć głosu.'); }
  function controls() {
    $('record').textContent = waiting ? 'Czekam na mikrofon…' : capture ? '■ Zakończ nagranie' : processing ? 'Rozpoznaję…' : '🎙 Nagraj';
    $('record').setAttribute('aria-pressed', String(!!capture));
    $('record').disabled = blocked || waiting || processing || !!job || !!player;
    $('stopVoice').hidden = !(capture || waiting || processing || job || player);
  }
  function closeCapture(item) {
    if (!item) return;
    clearTimeout(item.timer); item.stream.getTracks().forEach(track => track.stop());
    if (item.node) { item.node.port.onmessage = null; item.node.port.postMessage('stop'); item.node.disconnect(); }
    if (item.source) item.source.disconnect();
    item.context?.close().catch(() => {});
  }
  function stop() {
    ++epoch; waiting = false; processing = false;
    const old = capture; capture = null; closeCapture(old);
    if (job) {
      // Anulowanie ma własne żądanie: samo AbortController nie kończy procesu serwera.
      fetch('/api/v1/voice/jobs/' + job + '/cancel', {method:'POST', keepalive:true,
        headers:{'X-CSRF-Token':hooks.csrf()}}).catch(() => {});
    }
    job = null; aborter?.abort(); aborter = null;
    if (player) { player.pause(); player.removeAttribute('src'); player.load(); player = null; }
    if (playerUrl) { URL.revokeObjectURL(playerUrl); playerUrl = null; }
    if (finishPlayback) { finishPlayback(); finishPlayback = null; }
    controls();
  }
  async function request(kind, body, token, language) {
    if (token !== epoch) return null;
    const id = crypto.randomUUID(); job = id; aborter = new AbortController(); controls();
    const headers = {'X-CSRF-Token':hooks.csrf(), 'Content-Type':kind === 'transcribe' ? 'audio/wav' : 'application/json'};
    const response = await fetch('/api/v1/voice/jobs/' + id + '/' + kind + '?language=' + language,
      {method:'POST', headers, body, signal:aborter.signal});
    if (!response.ok) {
      let code = ''; try { code = (await response.json()).error?.code; } catch {}
      const error = Error('Operacja głosowa nie powiodła się (' + response.status + ').'); error.code = code; throw error;
    }
    const value = kind === 'transcribe' ? await response.json() : await response.blob();
    if (token !== epoch) return null;
    job = null; aborter = null; controls(); return value;
  }
  async function finishRecording() {
    const item = capture; if (!item) return;
    capture = null; closeCapture(item); const token = epoch; processing = true; controls();
    try {
      hooks.notice('Rozpoznaję mowę lokalnie na CPU…');
      // OfflineAudioContext wykonuje konwersję częstotliwości z filtrowaniem.
      const total = item.chunks.reduce((sum, part) => sum + part.length, 0);
      if (total < item.rate / 4) throw Error('audio_length');
      const samples = Math.min(480000, Math.floor(total * 16000 / item.rate));
      const offline = new OfflineAudioContext(1, samples, 16000);
      const buffer = offline.createBuffer(1, total, item.rate);
      let offset = 0; for (const part of item.chunks) { buffer.getChannelData(0).set(part, offset); offset += part.length; }
      const source = offline.createBufferSource(); source.buffer = buffer; source.connect(offline.destination); source.start();
      const rendered = await offline.startRendering();
      if (token !== epoch) return;
      const wav = encodeWav(rendered.getChannelData(0));
      const result = await request('transcribe', wav, token, item.language);
      if (!result || token !== epoch) return;
      const prompt = $('prompt');
      const combined = prompt.value.trim() + (prompt.value.trim() ? '\n' : '') + result.text;
      if (combined.length > 4000) { hooks.notice('Brak miejsca w polu wiadomości. Wyślij lub skróć tekst i nagraj ponownie.'); return; }
      prompt.value = combined; prompt.focus();
      hooks.notice('Rozpoznany tekst jest w polu wiadomości. Sprawdź go i kliknij Wyślij.');
    } catch (error) { if (token === epoch) report(error); }
    finally { if (token === epoch) { job = null; aborter = null; processing = false; controls(); } }
  }
  async function record() {
    if (capture) { await finishRecording(); return; }
    if (blocked || waiting || processing || job) return;
    stop(); const token = epoch; waiting = true; controls();
    let acquired = null;
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.AudioWorkletNode) throw Error('Ta przeglądarka nie udostępnia nagrywania. Otwórz localhost w aktualnym Edge lub Chrome.');
      const stream = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1, echoCancellation:true}, video:false});
      if (token !== epoch) { stream.getTracks().forEach(track => track.stop()); return; }
      acquired = {stream, chunks:[], language:$('voiceLanguage').value};
      const context = new AudioContext(); acquired.context = context; acquired.rate = context.sampleRate;
      capture = acquired;
      await context.audioWorklet.addModule('/recorder-worklet.js');
      if (token !== epoch) return;
      const node = new AudioWorkletNode(context, 'krip-recorder'); acquired.node = node;
      const source = context.createMediaStreamSource(stream); acquired.source = source;
      node.port.onmessage = event => {
        if (token !== epoch || capture !== acquired) return;
        if (event.data === 'limit') { finishRecording(); return; }
        acquired.chunks.push(event.data);
      };
      stream.getAudioTracks().forEach(track => { track.onended = () => { if (capture === acquired) { stop(); hooks.notice('Mikrofon został odłączony. Nagraj ponownie.'); } }; });
      source.connect(node); node.connect(context.destination); await context.resume();
      if (token !== epoch) return;
      acquired.timer = setTimeout(finishRecording, 30000); waiting = false; controls();
      hooks.notice('Nagrywam — kliknij Zakończ nagranie. Limit 30 sekund.');
    } catch (error) {
      closeCapture(acquired);
      if (token === epoch) { capture = null; waiting = false; controls(); report(error); }
    }
  }
  async function speak(text) {
    if (blocked) return;
    stop(); const token = epoch, language = $('voiceLanguage').value;
    if (!text.trim()) return;
    if (text.length > 12000) { hooks.notice('Ta wiadomość jest za długa do odczytu. Limit: 12 000 znaków.'); return; }
    try {
      // Cała odpowiedź w kolejnych porcjach; nigdy odczyt automatyczny ani SSML.
      for (let offset = 0; offset < text.length; offset += 1200) {
        hooks.notice('Przygotowuję lokalny odczyt…');
        const blob = await request('speak', JSON.stringify({text:text.slice(offset, offset+1200), language}), token, language);
        if (!blob || token !== epoch) return;
        playerUrl = URL.createObjectURL(blob); player = new Audio(playerUrl); controls();
        hooks.notice('Czytam odpowiedź. Możesz zatrzymać głos.');
        await new Promise((resolve, reject) => {
          finishPlayback = resolve; player.onended = resolve;
          player.onerror = () => reject(Error('Nie udało się odtworzyć dźwięku.'));
          player.play().catch(reject);
        });
        if (token !== epoch) return;
        player = null; finishPlayback = null; URL.revokeObjectURL(playerUrl); playerUrl = null;
      }
      hooks.notice('Odczyt zakończony.');
    } catch (error) { if (token === epoch) report(error); }
    finally { if (token === epoch) stop(); }
  }
  function configure(callbacks) {
    hooks = callbacks;
    $('record').onclick = record; $('stopVoice').onclick = () => { stop(); hooks.notice('Głos zatrzymany.'); };
    document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
    window.addEventListener('pagehide', stop); controls();
  }
  return {configure, stop, speak, setBlocked(value) { if (value && !blocked) stop(); blocked = value; controls(); }};
})();
