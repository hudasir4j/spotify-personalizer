/** Shared audio element unlocked by user gesture (envelope tap). */
let unlocked = false;
let unlockPromise = null;
let sharedAudio = null;

const SILENT_WAV =
  "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";

function ensureAudioElement() {
  if (typeof window === "undefined") return null;
  if (sharedAudio) return sharedAudio;

  sharedAudio = document.createElement("audio");
  sharedAudio.preload = "auto";
  sharedAudio.crossOrigin = "anonymous";
  sharedAudio.setAttribute("playsinline", "");
  sharedAudio.style.cssText = "position:fixed;width:0;height:0;opacity:0;pointer-events:none";
  document.body.appendChild(sharedAudio);
  return sharedAudio;
}

export function getSharedAudio() {
  return ensureAudioElement();
}

export function isAudioUnlocked() {
  return unlocked;
}

/** Call synchronously inside a click/tap handler. */
export function unlockAudioPlayback() {
  if (unlocked) return Promise.resolve(true);
  if (unlockPromise) return unlockPromise;

  const audio = ensureAudioElement();
  if (!audio) return Promise.resolve(false);

  audio.src = SILENT_WAV;
  audio.volume = 0.01;

  unlockPromise = audio
    .play()
    .then(() => {
      audio.pause();
      audio.currentTime = 0;
      audio.volume = 0.9;
      unlocked = true;
      window.dispatchEvent(new CustomEvent("audio-unlocked"));
      return true;
    })
    .catch(() => {
      unlockPromise = null;
      return false;
    });

  return unlockPromise;
}

export async function playPreview(url, key, onKeyChange) {
  if (!url) return false;

  if (!unlocked && unlockPromise) {
    await unlockPromise;
  }
  if (!unlocked) return false;

  const audio = ensureAudioElement();
  if (!audio) return false;

  if (audio.dataset.playingKey === key && !audio.paused) {
    return true;
  }

  try {
    audio.pause();
    if (audio.src !== url) {
      audio.src = url;
      audio.load();
    }
    audio.dataset.playingKey = key;
    await audio.play();
    if (onKeyChange) onKeyChange(key);
    return true;
  } catch {
    audio.dataset.playingKey = "";
    return false;
  }
}

export function preloadPreview(url) {
  if (!url || !unlocked) return;
  const link = document.createElement("link");
  link.rel = "preload";
  link.as = "audio";
  link.href = url;
  document.head.appendChild(link);
}

export function pausePreview() {
  const audio = sharedAudio;
  if (audio) {
    audio.pause();
    audio.dataset.playingKey = "";
  }
}
