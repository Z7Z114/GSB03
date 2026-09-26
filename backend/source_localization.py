import numpy as np
from scipy import signal
from typing import List, Tuple, Dict, Optional

try:  # librosa 可选：本模块的核心算法其实不依赖它
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    librosa = None
    LIBROSA_AVAILABLE = False


class SoundSourceLocalization:
    def __init__(self, sample_rate: int = 48000, speed_of_sound: float = 343.0):
        self.sample_rate = sample_rate
        self.speed_of_sound = speed_of_sound
        self.microphone_array = self._setup_standard_array()

    def _setup_standard_array(self) -> np.ndarray:
        return np.array([
            [0.0, 0.0, 0.0],
            [0.1, 0.0, 0.0],
            [0.05, 0.0866, 0.0],
            [0.05, 0.0289, 0.0816],
        ])

    def set_microphone_array(self, positions: List[Tuple[float, float, float]]):
        self.microphone_array = np.array(positions)

    def gcc_phat(self, sig1: np.ndarray, sig2: np.ndarray, max_tau: Optional[float] = None) -> float:
        sig1 = np.asarray(sig1, dtype=float)
        sig2 = np.asarray(sig2, dtype=float)
        if sig1.size == 0 or sig2.size == 0:
            return 0.0

        n = sig1.shape[0] + sig2.shape[0]
        
        SIG1 = np.fft.rfft(sig1, n=n)
        SIG2 = np.fft.rfft(sig2, n=n)
        
        R = SIG1 * np.conj(SIG2)
        R = R / (np.abs(R) + 1e-10)
        
        cc = np.fft.irfft(R, n=n)
        
        max_shift = n // 2
        if max_tau is not None:
            max_shift = min(max_shift, int(max_tau * self.sample_rate))
        
        cc = np.concatenate((cc[-max_shift:], cc[:max_shift + 1]))
        
        shift = np.argmax(np.abs(cc)) - max_shift
        tau = shift / float(self.sample_rate)
        
        return tau

    def estimate_tdoa(self, signals: List[np.ndarray]) -> np.ndarray:
        n_mics = len(signals)
        tdoa_matrix = np.zeros((n_mics, n_mics))
        
        max_distance = np.max(np.linalg.norm(
            self.microphone_array[:, np.newaxis] - self.microphone_array[np.newaxis, :],
            axis=2
        ))
        max_tau = max_distance / self.speed_of_sound
        
        for i in range(n_mics):
            for j in range(i + 1, n_mics):
                tau = self.gcc_phat(signals[i], signals[j], max_tau)
                tdoa_matrix[i, j] = tau
                tdoa_matrix[j, i] = -tau
        
        return tdoa_matrix

    def tdoa_to_position(self, tdoa_matrix: np.ndarray) -> np.ndarray:
        n_mics = len(self.microphone_array)
        positions = []
        
        ref_mic = 0
        for i in range(n_mics):
            if i == ref_mic:
                continue
            
            tau = tdoa_matrix[ref_mic, i]
            distance_diff = tau * self.speed_of_sound
            
            pos = self.microphone_array[i] - self.microphone_array[ref_mic]
            if np.linalg.norm(pos) > 1e-10:
                direction = pos / np.linalg.norm(pos)
                estimated_pos = self.microphone_array[ref_mic] + direction * max(distance_diff, 0)
                positions.append(estimated_pos)
        
        if positions:
            return np.mean(positions, axis=0)
        return np.array([0.0, 0.0, 1.0])

    def scan_for_sources(self, signals: List[np.ndarray], 
                         scan_range: Tuple[float, float] = (-5.0, 5.0),
                         resolution: int = 50) -> Dict:
        if resolution < 2:
            return {
                'power_map': [],
                'x_coords': [],
                'y_coords': [],
                'sources': [],
                'error': f'resolution 必须为 >= 2 的正整数，收到 {resolution}'
            }

        x = np.linspace(scan_range[0], scan_range[1], resolution)
        y = np.linspace(scan_range[0], scan_range[1], resolution)
        X, Y = np.meshgrid(x, y)
        
        power_map = np.zeros_like(X)
        tdoa_matrix = self.estimate_tdoa(signals)
        
        for i in range(resolution):
            for j in range(resolution):
                test_pos = np.array([X[i, j], Y[i, j], 0.0])
                
                expected_delays = np.zeros(len(self.microphone_array))
                for k, mic_pos in enumerate(self.microphone_array):
                    expected_delays[k] = np.linalg.norm(test_pos - mic_pos) / self.speed_of_sound
                
                expected_tdoa = np.zeros_like(tdoa_matrix)
                for m in range(len(self.microphone_array)):
                    for n in range(len(self.microphone_array)):
                        expected_tdoa[m, n] = expected_delays[m] - expected_delays[n]
                
                error = np.sum((tdoa_matrix - expected_tdoa) ** 2)
                power_map[i, j] = 1.0 / (error + 1e-10)
        
        power_map = power_map / np.max(power_map)
        
        peaks = self._find_peaks(power_map, X, Y)
        
        return {
            'power_map': power_map.tolist(),
            'x_coords': X[0].tolist(),
            'y_coords': Y[:, 0].tolist(),
            'sources': peaks
        }

    def _find_peaks(self, power_map: np.ndarray, X: np.ndarray, Y: np.ndarray, 
                    threshold: float = 0.7, min_distance: int = 5) -> List[Dict]:
        peaks = []
        visited = np.zeros_like(power_map, dtype=bool)
        
        for i in range(1, power_map.shape[0] - 1):
            for j in range(1, power_map.shape[1] - 1):
                if visited[i, j]:
                    continue
                
                if power_map[i, j] < threshold * np.max(power_map):
                    continue
                
                local_max = True
                for di in [-1, 0, 1]:
                    for dj in [-1, 0, 1]:
                        if di == 0 and dj == 0:
                            continue
                        if power_map[i + di, j + dj] > power_map[i, j]:
                            local_max = False
                            break
                    if not local_max:
                        break
                
                if local_max:
                    peaks.append({
                        'x': float(X[i, j]),
                        'y': float(Y[i, j]),
                        'confidence': float(power_map[i, j])
                    })
                    
                    for di in range(-min_distance, min_distance + 1):
                        for dj in range(-min_distance, min_distance + 1):
                            ni, nj = i + di, j + dj
                            if 0 <= ni < power_map.shape[0] and 0 <= nj < power_map.shape[1]:
                                visited[ni, nj] = True
        
        peaks.sort(key=lambda x: x['confidence'], reverse=True)
        return peaks[:5]

    def process_localization(self, audio_signals: List[np.ndarray],
                             scan_range: Tuple[float, float] = (-5.0, 5.0),
                             resolution: int = 50) -> Dict:
        if len(audio_signals) < 2:
            return {
                'success': False,
                'error': 'At least 2 microphone signals required for localization'
            }
        
        tdoa_matrix = self.estimate_tdoa(audio_signals)
        estimated_position = self.tdoa_to_position(tdoa_matrix)
        scan_results = self.scan_for_sources(audio_signals, scan_range=scan_range, resolution=resolution)
        
        return {
            'success': True,
            'estimated_position': estimated_position.tolist(),
            'tdoa_matrix': tdoa_matrix.tolist(),
            'source_scan': scan_results,
            'num_sources_detected': len(scan_results['sources']),
            'top_sources': scan_results['sources'][:3]
        }

    def real_time_localization_update(self, audio_chunk: np.ndarray, 
                                      previous_estimate: Optional[np.ndarray] = None,
                                      alpha: float = 0.7) -> Dict:
        if len(audio_chunk.shape) == 1:
            signals = [audio_chunk]
        else:
            signals = [audio_chunk[:, i] for i in range(audio_chunk.shape[1])]
        
        if len(signals) < 2:
            if previous_estimate is not None:
                position = np.asarray(previous_estimate, dtype=float).tolist()
            else:
                position = [0, 0, 0]
            return {'position': position, 'confidence': 0.0}
        
        tdoa_matrix = self.estimate_tdoa(signals)
        new_estimate = self.tdoa_to_position(tdoa_matrix)
        
        if previous_estimate is not None:
            smoothed_estimate = alpha * previous_estimate + (1 - alpha) * new_estimate
        else:
            smoothed_estimate = new_estimate
        
        return {
            'position': smoothed_estimate.tolist(),
            'raw_position': new_estimate.tolist(),
            'confidence': self._calculate_confidence(tdoa_matrix)
        }

    def _calculate_confidence(self, tdoa_matrix: np.ndarray) -> float:
        symmetry_error = np.mean(np.abs(tdoa_matrix + tdoa_matrix.T))
        consistency_score = 1.0 / (1.0 + symmetry_error * 1000)
        return float(min(1.0, consistency_score))
