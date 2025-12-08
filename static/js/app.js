// static/js/app.js

document.addEventListener("DOMContentLoaded", () => {
  const path = window.location.pathname;

  if (path === "/production") {
    import("./js/production.js");
    return;
  }

  document.querySelectorAll('.row-toggle').forEach(toggle => {
    toggle.addEventListener('click', () => {
      toggle.parentElement.classList.toggle('collapsed');
    });
  });

  if (path === "/" || path === "/index.html" || path === "") {
    Promise.all([
      import("./modules/ui-helpers.js"),
      import("./modules/upload.js"),
      import("./modules/settings.js"),
      import("./modules/model-xtts.js"),
      import("./modules/generate-xtts.js"),
      import("./modules/model-fish.js"),
      import("./modules/generate-fish.js"),
      import("./modules/model-kokoro.js"),
      import("./modules/generate-kokoro.js"),
      import("./modules/model-stable-audio.js"),
      import("./modules/generate-stable-audio.js"),
      import("./modules/model-ace-step.js"),
      import("./modules/generate-ace-step.js"),
      import("./modules/model-whisper.js"),
      import("./modules/chatbot.js"),
    ]).then(modules => {
      const [
        ui, upload, settings,
        xttsModel, xttsGen,
        fishModel, fishGen,
        kokoroModel, kokoroGen,
        saModel, saGen,
        aceModel, aceGen,
        whisper, chatbot
      ] = modules;

      settings.initSettings();
      ui.initUIHelpers();
      upload.initUpload();

      xttsModel.initXTTSModel();
      xttsModel.setMode("cloned");
      xttsGen.initXTTSGenerate();

      fishModel.initFishModel();
      fishGen.initFishGenerate();

      kokoroModel.initKokoroModel();
      kokoroGen.initKokoroGenerate();

      saModel.initStableAudioModel();
      saGen.initStableAudioGenerate();

      aceModel.initAceStepModel();
      aceGen.initAceStepGenerate();

      whisper.initWhisperModel();
      chatbot.initChatbot();

      if (document.querySelector('#mediaDropZone')) {
        import("./production.js");
      }

      document.addEventListener('click', e => {
        const gearBtn = e.target.closest('.show-settings');
        const backBtn = e.target.closest('.show-main');
        const leftSlider = e.target.closest('.card')?.querySelector('.settings-slider');
        if (gearBtn && leftSlider) leftSlider.classList.add('show-settings');
        if (backBtn && leftSlider) leftSlider.classList.remove('show-settings');

        const xtts   = document.querySelector('.xtts-center-slider');
        const fish   = document.querySelector('.fish-center-slider');
        const kokoro = document.querySelector('.kokoro-center-slider');
        const stable = document.querySelector('.stable-center-slider');
        const ace    = document.querySelector('.ace-center-slider');
        const upload = document.querySelector('.upload-center-slider');

        if (e.target.closest('.show-xtts-api'))        xtts?.classList.add('show-api');
        if (e.target.closest('.hide-xtts-api'))        xtts?.classList.remove('show-api');
        if (e.target.closest('.show-fish-api'))        fish?.classList.add('show-api');
        if (e.target.closest('.hide-fish-api'))        fish?.classList.remove('show-api');
        if (e.target.closest('.show-kokoro-api'))      kokoro?.classList.add('show-api');
        if (e.target.closest('.hide-kokoro-api'))      kokoro?.classList.remove('show-api');
        if (e.target.closest('.show-stable-api'))      stable?.classList.add('show-api');
        if (e.target.closest('.hide-stable-api'))      stable?.classList.remove('show-api');
        if (e.target.closest('.show-ace-api'))         ace?.classList.add('show-api');
        if (e.target.closest('.hide-ace-api'))         ace?.classList.remove('show-api');
        if (e.target.closest('.show-upload-audio-files')) upload?.classList.add('show-api');
        if (e.target.closest('.hide-upload-audio-files')) upload?.classList.remove('show-api');
      });

      document.getElementById('copyTranscriptionBtn')?.addEventListener('click', async () => {
        const text = document.getElementById('transcriptionOutput')?.value.trim();
        if (!text) return;
        try {
          await navigator.clipboard.writeText(text);
          const btn = document.getElementById('copyTranscriptionBtn');
          const old = btn.innerHTML;
          btn.innerHTML = 'Copied!';
          btn.classList.replace('btn-outline-light', 'btn-success');
          setTimeout(() => {
            btn.innerHTML = old;
            btn.classList.replace('btn-success', 'btn-outline-light');
          }, 1500);
        } catch (err) {
          alert('Copy failed');
        }
      });

    });
  }
});