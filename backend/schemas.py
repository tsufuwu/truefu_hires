"""
schemas.py — Pydantic response models for the TrueLossless Inspector API.
"""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


class VerdictSchema(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Authenticity score 0-100")
    status: str = Field(..., description="AUTHENTIC_LOSSLESS | SUSPICIOUS | FAKE_UPSCALED | FAKE_SPOOFED | FAKE_BIT_DEPTH | UPSAMPLED_HIRES")
    label: str
    confidence: str = Field(..., description="HIGH | MEDIUM | LOW")
    summary: str


class MetadataSchema(BaseModel):
    codec: str
    sample_rate_hz: int
    channels: int
    duration_sec: float
    bitrate_kbps: Optional[float]
    is_dsd: bool = False
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    cover_art_base64: Optional[str] = None


class BitDepthSchema(BaseModel):
    declared: int
    effective: int
    wasted_bits: int
    is_padded: bool
    suspicious_scaling: bool = False
    detail: str


class SpectralCutoffSchema(BaseModel):
    nyquist_hz: float
    detected_cutoff_hz: Optional[float]
    rolloff_slope_db_per_khz: Optional[float]
    is_brickwall: bool
    is_studio_filter: bool = False
    suspected_source_encoder: Optional[str] = None
    detail: str


class AntiSpoofSchema(BaseModel):
    spectral_holes_ratio: float
    holes_detected: bool
    hf_envelope_correlation: Optional[float]
    fake_noise_injected: bool
    detail: str


class UltrasonicSchema(BaseModel):
    applicable: bool
    has_true_ultrasonic_transients: Optional[bool]
    fake_hires_upsampled: bool = False
    ultrasonic_correlation: Optional[float]
    detail: str


class PillarsSchema(BaseModel):
    bit_depth: BitDepthSchema
    spectral_cutoff: SpectralCutoffSchema
    anti_spoof: AntiSpoofSchema
    ultrasonic: UltrasonicSchema


class RolloffCurveSchema(BaseModel):
    frequencies_khz: List[float]
    energy_dbfs: List[float]


class PhaseCoherenceSchema(BaseModel):
    hf_time_variance_db: float
    transient_concurrence_ratio: float
    is_stealth_noise_layer: bool
    status: str
    detail: str


class NaturalDecaySchema(BaseModel):
    knee_frequency_khz: Optional[float] = None
    slope_pre_knee_db_per_khz: Optional[float] = None
    slope_post_knee_db_per_khz: Optional[float] = None
    decay_discontinuity_score: float
    violates_natural_decay: bool
    status: str
    detail: str


class AccurateRipSchema(BaseModel):
    crc32_v1: str
    crc32_v2: str
    track_crc: str
    db_status: str
    confidence: int = 0
    detail: str


class AiArtifactsSchema(BaseModel):
    phase_jitter_entropy: float
    spectral_repetition_score: float
    comb_ripple_db: float
    ai_artifacts_detected: bool
    status: str
    detail: str


class AdvancedModulesSchema(BaseModel):
    phase_coherence: PhaseCoherenceSchema
    natural_decay: NaturalDecaySchema
    accuraterip: AccurateRipSchema
    ai_artifacts: AiArtifactsSchema


class VisualsSchema(BaseModel):
    rolloff_curve: RolloffCurveSchema
    spectrogram_base64: Optional[str]


class AnalysisResponse(BaseModel):
    filename: str
    verdict: VerdictSchema
    metadata: MetadataSchema
    pillars: PillarsSchema
    advanced: Optional[AdvancedModulesSchema] = None
    visuals: VisualsSchema


class ErrorResponse(BaseModel):
    detail: str

