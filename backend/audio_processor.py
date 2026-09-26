import numpy as np
from scipy import signal
from scipy.ndimage import median_filter
from typing import Tuple, Optional, List
import warnings
warnings.filterwarnings('ignore')

try:  # 重型音频依赖可选：缺失时模块仍可导入
    import librosa
    import soundfile as sf
    AUDIO_DEPS_AVAILABLE = True
except ImportError:
    librosa = None
    sf = None
    AUDIO_DEPS_AVAILABLE = False


class AudioDepsMissing(RuntimeError):
    """音频依赖未安装（需要 requirements-ml.txt）。"""


def _require_audio_deps():
    if not AUDIO_DEPS_AVAILABLE:
        raise AudioDepsMissing(
            "音频依赖未安装（librosa / soundfile）：请安装 requirements-ml.txt"
        )


class LaserAudioProcessor:
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.n_fft = 2048
        self.hop_length = 512
        self.window = 'hann'

    def load_vibration_data(self, file_path: str) -> Tuple[np.ndarray, int]:
        _require_audio_deps()
        try:
            y, sr = librosa.load(file_path, sr=self.sample_rate, mono=True)
            return y, sr
        except Exception as e:
            raise RuntimeError(f"Failed to load vibration data: {e}")

    def dc_removal(self, y: np.ndarray) -> np.ndarray:
        return y - np.mean(y)

    def highpass_filter(self, y: np.ndarray, cutoff: float = 80.0) -> np.ndarray:
        b, a = signal.butter(4, cutoff / (self.sample_rate / 2), btype='highpass')
        return signal.filtfilt(b, a, y)

    def lowpass_filter(self, y: np.ndarray, cutoff: float = 8000.0) -> np.ndarray:
        b, a = signal.butter(8, cutoff / (self.sample_rate / 2), btype='lowpass')
        return signal.filtfilt(b, a, y)

    def adaptive_noise_reduction(self, y: np.ndarray, noise_estimation_duration: float = 0.5) -> np.ndarray:
        noise_samples = int(noise_estimation_duration * self.sample_rate)
        noise_est = y[:noise_samples] if len(y) > noise_samples else y
        
        noise_spec = librosa.stft(noise_est, n_fft=self.n_fft, hop_length=self.hop_length, window=self.window)
        noise_power = np.mean(np.abs(noise_spec) ** 2, axis=1, keepdims=True)
        
        spec = librosa.stft(y, n_fft=self.n_fft, hop_length=self.hop_length, window=self.window)
        spec_power = np.abs(spec) ** 2
        
        alpha = 0.95
        noise_power_estimate = noise_power
        for t in range(1, spec.shape[1]):
            noise_power_estimate = alpha * noise_power_estimate + (1 - alpha) * spec_power[:, t:t+1]
        
        snr = spec_power / (noise_power_estimate + 1e-10)
        gain = np.maximum(1 - 1 / snr, 0.1)
        gain = np.sqrt(gain)
        
        enhanced_spec = spec * gain
        enhanced_y = librosa.istft(enhanced_spec, hop_length=self.hop_length, window=self.window)
        
        return enhanced_y

    def spectral_subtraction(self, y: np.ndarray, alpha: float = 2.0, beta: float = 0.01) -> np.ndarray:
        spec = librosa.stft(y, n_fft=self.n_fft, hop_length=self.hop_length, window=self.window)
        magnitude = np.abs(spec)
        phase = np.angle(spec)
        
        noise_mag = np.mean(magnitude[:, :int(0.5 * self.sample_rate / self.hop_length)], axis=1, keepdims=True)
        
        enhanced_mag = np.maximum(magnitude - alpha * noise_mag, beta * noise_mag)
        enhanced_spec = enhanced_mag * np.exp(1j * phase)
        
        enhanced_y = librosa.istft(enhanced_spec, hop_length=self.hop_length, window=self.window)
        return enhanced_y

    def wiener_filter(self, y: np.ndarray, noise_frame_duration: float = 0.02) -> np.ndarray:
        spec = librosa.stft(y, n_fft=self.n_fft, hop_length=self.hop_length, window=self.window)
        magnitude = np.abs(spec)
        phase = np.angle(spec)
        
        noise_frames = int(noise_frame_duration * self.sample_rate / self.hop_length)
        noise_psd = np.mean(np.abs(spec[:, :noise_frames]) ** 2, axis=1, keepdims=True)
        
        signal_psd = np.abs(spec) ** 2
        wiener_gain = signal_psd / (signal_psd + noise_psd + 1e-10)
        
        smoothed_gain = np.zeros_like(wiener_gain)
        for i in range(smoothed_gain.shape[0]):
            smoothed_gain[i, :] = median_filter(wiener_gain[i, :], size=3)
        
        enhanced_spec = spec * smoothed_gain
        enhanced_y = librosa.istft(enhanced_spec, hop_length=self.hop_length, window=self.window)
        return enhanced_y

    def deconvolution(self, y: np.ndarray, window_type: str = 'hann', regularization: float = 1e-5) -> np.ndarray:
        window_length = int(0.025 * self.sample_rate)
        window = signal.get_window(window_type, window_length)
        
        spec = librosa.stft(y, n_fft=self.n_fft, hop_length=self.hop_length, window=self.window)
        
        vibration_response = np.ones(self.n_fft // 2 + 1)
        freqs = np.linspace(0, self.sample_rate / 2, len(vibration_response))
        mid_band = (freqs > 300) & (freqs < 3000)
        vibration_response[mid_band] = 1.5
        vibration_response[~mid_band] = 0.7
        
        inverse_response = 1.0 / (vibration_response + regularization)
        inverse_response = inverse_response[:, np.newaxis]
        
        deconvolved_spec = spec * inverse_response
        deconvolved_y = librosa.istft(deconvolved_spec, hop_length=self.hop_length, window=self.window)
        
        return deconvolved_y

    def harmonic_percussive_separation(self, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        spec = librosa.stft(y, n_fft=self.n_fft, hop_length=self.hop_length, window=self.window)
        harmonic, percussive = librosa.decompose.hpss(spec, margin=(1.0, 5.0))
        
        harmonic_y = librosa.istft(harmonic, hop_length=self.hop_length, window=self.window)
        percussive_y = librosa.istft(percussive, hop_length=self.hop_length, window=self.window)
        
        return harmonic_y, percussive_y

    def voice_activity_detection(self, y: np.ndarray) -> np.ndarray:
        hop_length = 512
        frame_length = 2048
        
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        zcr = librosa.feature.zero_crossing_rate(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        
        rms_threshold = np.percentile(rms, 60)
        zcr_threshold = np.percentile(zcr, 40)
        
        speech_mask = (rms > rms_threshold) & (zcr > zcr_threshold)
        
        speech_mask = signal.medfilt(speech_mask.astype(int), kernel_size=5)
        
        frame_times = librosa.frames_to_time(np.arange(len(rms)), sr=self.sample_rate, hop_length=hop_length)
        full_mask = np.zeros_like(y, dtype=bool)
        for i, is_speech in enumerate(speech_mask):
            start = int(i * hop_length)
            end = int(min((i + 1) * hop_length, len(y)))
            full_mask[start:end] = is_speech
        
        return full_mask

    def extreme_enhancement_pipeline(self, y: np.ndarray) -> np.ndarray:
        y = self.dc_removal(y)
        
        y = self.highpass_filter(y, 80.0)
        y = self.lowpass_filter(y, 8000.0)
        
        y = self.spectral_subtraction(y, alpha=2.5, beta=0.02)
        
        y = self.adaptive_noise_reduction(y)
        
        y = self.deconvolution(y)
        
        y = self.wiener_filter(y)
        
        harmonic_y, _ = self.harmonic_percussive_separation(y)
        
        speech_mask = self.voice_activity_detection(y)
        enhanced_y = np.where(speech_mask, 0.7 * harmonic_y + 0.3 * y, y * 0.1)
        
        enhanced_y = enhanced_y / (np.max(np.abs(enhanced_y)) + 1e-10)
        
        return enhanced_y

    def process_audio_file(self, input_path: str, output_path: Optional[str] = None) -> Tuple[np.ndarray, str]:
        _require_audio_deps()
        y, sr = self.load_vibration_data(input_path)
        
        enhanced_y = self.extreme_enhancement_pipeline(y)
        
        if output_path:
            sf.write(output_path, enhanced_y, self.sample_rate)
            return enhanced_y, output_path
        
        return enhanced_y, ""

    def estimate_snr(self, clean_signal: np.ndarray, noisy_signal: np.ndarray) -> float:
        signal_power = np.mean(clean_signal ** 2)
        noise_power = np.mean((clean_signal - noisy_signal) ** 2)
        snr = 10 * np.log10(signal_power / (noise_power + 1e-10))
        return snr
