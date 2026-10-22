// api.ts — Typed API client for the TrueLossless Inspector backend

export interface VerdictData {
  score: number;
  status: string;
  label: string;
  confidence: string;
  summary: string;
}

export interface MetadataData {
  codec: string;
  sample_rate_hz: number;
  channels: number;
  duration_sec: number;
  bitrate_kbps: number | null;
  is_dsd: boolean;
  title?: string | null;
  artist?: string | null;
  album?: string | null;
  cover_art_base64?: string | null;
}

export interface BitDepthData {
  declared: number;
  effective: number;
  wasted_bits: number;
  is_padded: boolean;
  suspicious_scaling: boolean;
  detail: string;
}

export interface SpectralCutoffData {
  nyquist_hz: number;
  detected_cutoff_hz: number | null;
  rolloff_slope_db_per_khz: number | null;
  is_brickwall: boolean;
  is_studio_filter?: boolean;
  suspected_source_encoder: string | null;
  detail: string;
}

export interface AntiSpoofData {
  spectral_holes_ratio: number;
  holes_detected: boolean;
  hf_envelope_correlation: number | null;
  fake_noise_injected: boolean;
  detail: string;
}

export interface UltrasonicData {
  applicable: boolean;
  has_true_ultrasonic_transients: boolean | null;
  fake_hires_upsampled: boolean;
  ultrasonic_correlation: number | null;
  detail: string;
}

export interface PillarsData {
  bit_depth: BitDepthData;
  spectral_cutoff: SpectralCutoffData;
  anti_spoof: AntiSpoofData;
  ultrasonic: UltrasonicData;
}

export interface RolloffCurveData {
  frequencies_khz: number[];
  energy_dbfs: number[];
}

export interface VisualsData {
  rolloff_curve: RolloffCurveData;
  spectrogram_base64: string | null;
}

export interface PhaseCoherenceData {
  hf_time_variance_db: number;
  transient_concurrence_ratio: number;
  is_stealth_noise_layer: boolean;
  status: string;
  detail: string;
}

export interface NaturalDecayData {
  knee_frequency_khz: number | null;
  slope_pre_knee_db_per_khz: number | null;
  slope_post_knee_db_per_khz: number | null;
  decay_discontinuity_score: number;
  violates_natural_decay: boolean;
  status: string;
  detail: string;
}

export interface AccurateRipData {
  crc32_v1: string;
  crc32_v2: string;
  track_crc: string;
  db_status: string;
  confidence: number;
  detail: string;
}

export interface AiArtifactsData {
  phase_jitter_entropy: number;
  spectral_repetition_score: number;
  comb_ripple_db: number;
  ai_artifacts_detected: boolean;
  status: string;
  detail: string;
}

export interface AdvancedModulesData {
  phase_coherence: PhaseCoherenceData;
  natural_decay: NaturalDecayData;
  accuraterip: AccurateRipData;
  ai_artifacts: AiArtifactsData;
}

export interface AnalysisResult {
  filename: string;
  verdict: VerdictData;
  metadata: MetadataData;
  pillars: PillarsData;
  advanced?: AdvancedModulesData;
  visuals: VisualsData;
}

export interface DemoSample {
  id: string;
  title: string;
  badge: string;
  filename: string;
  type: 'authentic' | 'padded' | 'fake' | 'spoofed';
  available: boolean;
}

export const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

export async function analyzeFile(file: File): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function getSamples(): Promise<DemoSample[]> {
  const response = await fetch(`${API_BASE}/api/samples`);
  if (!response.ok) return [];
  return response.json();
}

export async function analyzeSample(sampleId: string): Promise<AnalysisResult> {
  const response = await fetch(`${API_BASE}/api/analyze-sample/${encodeURIComponent(sampleId)}`, {
    method: 'POST',
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }

  return response.json();
}
