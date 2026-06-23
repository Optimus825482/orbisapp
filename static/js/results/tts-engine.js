/**
 * ═══════════════════════════════════════════════════════════════════════════
 * ORBIS TTS ENGINE
 * Text-to-Speech functionality for AI interpretations
 * ═══════════════════════════════════════════════════════════════════════════
 */

const TTS = {
  status: "idle",
  chunks: [],
  currentChunkIndex: 0,
  totalChunks: 0,
  rate: parseFloat(localStorage.getItem("tts-speed") || "1.5"),
  voicesLoaded: false,
  selectedVoice: null,

  init() {
    this.loadVoices();
    this.updateSpeedDisplay();
    this.bindEvents();
    console.log("[TTS] Engine initialized");
  },

  bindEvents() {
    $("#modal-read-aloud").on("click", () => this.startFromModal());
  },

  loadVoices() {
    const loadVoiceList = () => {
      const voices = speechSynthesis.getVoices();
      const turkishVoices = voices.filter((v) => v.lang.startsWith("tr"));
      this.selectedVoice =
        turkishVoices[0] ||
        voices.find((v) => v.lang.startsWith("en")) ||
        voices[0];
      this.voicesLoaded = true;
    };

    if (speechSynthesis.onvoiceschanged !== undefined) {
      speechSynthesis.onvoiceschanged = loadVoiceList;
    }
    loadVoiceList();
  },

  updateSpeedDisplay() {
    const display = document.getElementById("speed-display");
    if (display) display.textContent = this.rate.toFixed(1) + "x";
  },

  changeSpeed(delta) {
    this.rate = Math.max(0.5, Math.min(2.5, this.rate + delta));
    localStorage.setItem("tts-speed", this.rate.toString());
    this.updateSpeedDisplay();

    if (this.status === "playing") {
      speechSynthesis.cancel();
      this.speakCurrentChunk();
    }
  },

  /**
   * Markdown ve özel karakterleri temizle
   * TTS'in "yıldız yıldız" veya "iki nokta üst üste" demesini engeller
   */
  cleanTextForSpeech(text) {
    return (
      text
        // Başlıkları temizle (## Başlık -> Başlık)
        .replace(/^#{1,6}\s*/gm, "")
        // Bold/italic yıldızları temizle (**text** veya *text* -> text)
        .replace(/\*{1,3}([^*]+)\*{1,3}/g, "$1")
        // Underscore bold/italic (_text_ veya __text__ -> text)
        .replace(/_{1,2}([^_]+)_{1,2}/g, "$1")
        // Inline code backtick'leri temizle (`code` -> code)
        .replace(/`([^`]+)`/g, "$1")
        // Code block'ları temizle
        .replace(/```[\s\S]*?```/g, "")
        // Link'leri sadece metin olarak bırak [text](url) -> text
        .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
        // Görsel linklerini kaldır ![alt](url)
        .replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1")
        // Liste işaretlerini temizle (- veya * ile başlayan)
        .replace(/^[\s]*[-*+]\s+/gm, "")
        // Numaralı liste işaretlerini temizle (1. 2. vs)
        .replace(/^[\s]*\d+\.\s+/gm, "")
        // Blockquote'ları temizle (> ile başlayan)
        .replace(/^>\s*/gm, "")
        // Horizontal rule'ları kaldır (---, ***, ___)
        .replace(/^[-*_]{3,}$/gm, "")
        // Emoji'leri kaldır (opsiyonel - bazı TTS'ler emoji okuyabiliyor)
        .replace(
          /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu,
          ""
        )
        // HTML tag'lerini temizle
        .replace(/<[^>]*>/g, "")
        // Özel karakterleri temizle
        .replace(/[═║╔╗╚╝╠╣╦╩╬─│┌┐└┘├┤┬┴┼]/g, "")
        // Çoklu boşlukları tek boşluğa indir
        .replace(/\s+/g, " ")
        // Çoklu satır sonlarını tek satır sonuna indir
        .replace(/\n{2,}/g, "\n")
        // Baş ve sondaki boşlukları temizle
        .trim()
    );
  },

  splitIntoChunks(text, maxLength = 180) {
    // Önce metni temizle
    const cleanedText = this.cleanTextForSpeech(text);
    const sentences = cleanedText.replace(/([.!?])\s+/g, "$1|").split("|");
    const chunks = [];
    let current = "";

    sentences.forEach((sentence) => {
      if ((current + " " + sentence).length > maxLength && current) {
        chunks.push(current.trim());
        current = sentence;
      } else {
        current = current ? current + " " + sentence : sentence;
      }
    });

    if (current.trim()) chunks.push(current.trim());
    return chunks;
  },

  startFromModal() {
    const text = window.currentInterpretationText || "";
    if (!text) {
      console.warn("[TTS] No text to read");
      return;
    }

    if (this.status === "playing") {
      this.pause();
    } else if (this.status === "paused") {
      this.resume();
    } else {
      this.start(text);
    }
  },

  start(text) {
    speechSynthesis.cancel();
    this.chunks = this.splitIntoChunks(text);
    this.totalChunks = this.chunks.length;
    this.currentChunkIndex = 0;
    this.status = "playing";
    this.updateUI();
    this.speakCurrentChunk();
  },

  speakCurrentChunk() {
    if (this.currentChunkIndex >= this.totalChunks) {
      this.finish();
      return;
    }

    const utterance = new SpeechSynthesisUtterance(
      this.chunks[this.currentChunkIndex]
    );
    utterance.voice = this.selectedVoice;
    utterance.rate = this.rate;
    utterance.pitch = 1;

    utterance.onend = () => {
      if (this.status === "playing") {
        this.currentChunkIndex++;
        this.speakCurrentChunk();
      }
    };

    utterance.onerror = (e) => {
      console.error("[TTS] Error:", e);
      this.stop();
    };

    speechSynthesis.speak(utterance);
  },

  pause() {
    speechSynthesis.pause();
    this.status = "paused";
    this.updateUI();
  },

  resume() {
    speechSynthesis.resume();
    this.status = "playing";
    this.updateUI();
  },

  stop() {
    speechSynthesis.cancel();
    this.status = "idle";
    this.currentChunkIndex = 0;
    this.updateUI();
  },

  finish() {
    this.status = "finished";
    this.updateUI();
    setTimeout(() => {
      this.status = "idle";
      this.updateUI();
    }, 2000);
  },

  updateUI() {
    const icon = document.getElementById("listen-icon");
    const text = document.getElementById("listen-text");
    if (!icon || !text) return;

    switch (this.status) {
      case "playing":
        icon.textContent = "pause";
        text.textContent = "Duraklat";
        break;
      case "paused":
        icon.textContent = "play_arrow";
        text.textContent = "Devam Et";
        break;
      case "finished":
        icon.textContent = "check_circle";
        text.textContent = "Tamamlandı";
        break;
      default:
        icon.textContent = "volume_up";
        text.textContent = "Dinle";
    }
  },
};

// Export
if (typeof module !== "undefined" && module.exports) {
  module.exports = { TTS };
}
