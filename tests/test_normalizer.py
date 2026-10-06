"""Tests for the audio normalization core (vat/audio/normalizer.py).

These run the real ffmpeg the app itself would find (bundled, then PATH) on
small synthetic WAVs, so they prove the FFmpeg filter chains do what the
settings promise: peak gain, two-pass LUFS, bit depth, trimming, sample rate,
and the silence guard. They are skipped when no ffmpeg is available.
"""

import math
import os
import struct
import threading
import wave

import pytest

from vat.audio import normalizer as N
from vat.audio.normalizer import (
    DEFAULT_SETTINGS, Normalizer, NormalizeError, NormalizeResult,
    choose_output_codec, describe_settings, ensure_plain_pcm_header,
    get_wav_format_info, normalize_settings, parse_loudnorm_json,
    wav_header_duration,
)


def _ffmpeg_available() -> bool:
    try:
        N.find_ff_tools()
        return True
    except NormalizeError:
        return False


needs_ffmpeg = pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not found")


# --- synthetic audio ---------------------------------------------------------

def write_tone(path, seconds=1.0, rate=48000, sampwidth=3, amp_db=-20.0,
               lead_silence=0.0, trail_silence=0.0, freq=440.0):
    """Mono sine at ``amp_db`` dBFS, optionally padded with digital silence."""
    import numpy as np
    amp = 10 ** (amp_db / 20.0) if amp_db > -300 else 0.0
    full = (1 << (8 * sampwidth - 1)) - 1
    t = np.arange(int(rate * seconds)) / rate
    tone = np.rint(amp * np.sin(2 * np.pi * freq * t) * full).astype(np.int64)
    samples = np.concatenate([
        np.zeros(int(rate * lead_silence), np.int64), tone, np.zeros(int(rate * trail_silence), np.int64),
    ])
    if sampwidth == 2:
        data = samples.astype("<i2").tobytes()
    elif sampwidth == 3:
        # little-endian 24-bit: the low three bytes of each little-endian 32-bit sample
        data = np.frombuffer(samples.astype("<i4").tobytes(), np.uint8).reshape(-1, 4)[:, :3].tobytes()
    else:
        data = samples.astype("<i4").tobytes()
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        wf.writeframes(data)
    return path


def wav_info(path):
    """(peak dBFS, sample width bytes, sample rate, seconds)."""
    with wave.open(path, "rb") as wf:
        sw, rate, n = wf.getsampwidth(), wf.getframerate(), wf.getnframes()
        raw = wf.readframes(n)
    full = (1 << (8 * sw - 1)) - 1
    if sw == 2:
        mx = max((abs(v) for (v,) in struct.iter_unpack("<h", raw)), default=0)
    elif sw == 3:
        mx = max((abs(int.from_bytes(raw[i:i + 3], "little", signed=True)) for i in range(0, len(raw), 3)), default=0)
    else:
        mx = max((abs(v) for (v,) in struct.iter_unpack("<i", raw)), default=0)
    peak = 20 * math.log10(mx / full) if mx else float("-inf")
    return peak, sw, rate, n / rate


# --- settings ------------------------------------------------------------------

def test_defaults_are_complete_and_keep_the_archival_bit_depth():
    s = normalize_settings({})
    assert s == DEFAULT_SETTINGS
    assert s["normMode"] == "peak"
    assert s["targetBitDepth"] == "original"
    assert s["autoTrim"] is False


def test_bad_or_foreign_settings_fall_back_to_defaults():
    s = normalize_settings({
        "normMode": "LOUD", "peakTargetDb": "x", "targetBitDepth": "32",
        "trimPadMs": -5, "autoTrim": "yes", "limiterLimit": 7, "unknown": 1,
    })
    assert s["normMode"] == "peak"
    assert s["peakTargetDb"] == DEFAULT_SETTINGS["peakTargetDb"]
    assert s["targetBitDepth"] == "original"
    assert s["trimPadMs"] == 0
    assert s["autoTrim"] is True
    assert s["limiterLimit"] == 1.0
    assert "unknown" not in s


def test_settings_accept_json_round_trip_forms():
    s = normalize_settings({"targetBitDepth": "16", "normMode": "LUFS", "peakOnlyBoost": 0})
    assert s["targetBitDepth"] == 16
    assert s["normMode"] == "lufs"
    assert s["peakOnlyBoost"] is False
    assert normalize_settings({"targetBitDepth": 24.0})["targetBitDepth"] == 24


def test_describe_settings_mentions_the_essentials():
    assert "peak -2 dBFS" in describe_settings({})
    txt = describe_settings({"normMode": "lufs", "autoTrim": True, "targetBitDepth": 16})
    assert "LUFS -16" in txt and "16-bit" in txt and "trim" in txt


# --- pure helpers ---------------------------------------------------------------

def test_wav_header_helpers(tmp_path):
    p = write_tone(str(tmp_path / "t.wav"), seconds=0.5, sampwidth=3)
    fmt = get_wav_format_info(p)
    assert fmt == {"audioFormat": 1, "channels": 1, "sampleRate": 48000, "bitsPerSample": 24}
    assert abs(wav_header_duration(p) - 0.5) < 1e-6
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"RIFF....WAVEjunk")
    assert get_wav_format_info(str(bad)) is None
    assert wav_header_duration(str(bad)) == 0.0


@pytest.mark.parametrize("depth,fmt,codec", [
    ("original", {"audioFormat": 1, "bitsPerSample": 24}, "pcm_s24le"),
    ("original", {"audioFormat": 1, "bitsPerSample": 16}, "pcm_s16le"),
    ("original", {"audioFormat": 3, "bitsPerSample": 32}, "pcm_f32le"),
    ("original", None, "pcm_s16le"),
    (16, {"audioFormat": 1, "bitsPerSample": 24}, "pcm_s16le"),
    (24, {"audioFormat": 1, "bitsPerSample": 24}, "pcm_s24le"),
    (24, {"audioFormat": 1, "bitsPerSample": 16}, "pcm_s16le"),   # no up-convert
    (24, None, "pcm_s24le"),
])
def test_choose_output_codec(depth, fmt, codec):
    assert choose_output_codec(depth, fmt) == codec


def _fmt_chunk(path):
    """(format tag, fmt chunk size, other chunk ids) of a WAV file."""
    with open(path, "rb") as f:
        data = f.read()
    pos, tag, size, others = 12, None, None, []
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        csize = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if cid == b"fmt ":
            tag, size = struct.unpack("<H", data[pos + 8:pos + 10])[0], csize
        elif cid != b"data":
            others.append(cid)
        pos += 8 + csize + (csize % 2)
    return tag, size, others


def _extensible_pcm_wav(path, samples_24bit, with_list_chunk=True):
    """Hand-build what FFmpeg writes for 24-bit PCM: an EXTENSIBLE fmt plus a LIST chunk."""
    pcm = b"".join(v.to_bytes(3, "little", signed=True) for v in samples_24bit)
    fmt = struct.pack("<HHIIHH", 0xFFFE, 1, 48000, 48000 * 3, 3, 24)
    fmt += struct.pack("<HHI", 22, 24, 4) + b"\x01\x00\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71"
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    if with_list_chunk:
        info = b"INFOISFT" + struct.pack("<I", 6) + b"Lavf\x00\x00"
        chunks += b"LIST" + struct.pack("<I", len(info)) + info
    chunks += b"data" + struct.pack("<I", len(pcm)) + pcm + (b"\x00" if len(pcm) % 2 else b"")
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks)
    return pcm


def test_ensure_plain_pcm_header_rewrites_extensible_pcm_and_keeps_samples(tmp_path):
    p = str(tmp_path / "x.wav")
    samples = [0, 1, -1, 8388607, -8388608, 123456, -654321]   # odd count: data gets a pad byte
    pcm = _extensible_pcm_wav(p, samples)
    assert _fmt_chunk(p)[0] == 0xFFFE
    assert ensure_plain_pcm_header(p) is True
    tag, size, others = _fmt_chunk(p)
    assert tag == 1 and size == 16 and others == []
    with wave.open(p, "rb") as wf:   # the app's playback path
        assert (wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getnframes()) == (1, 3, 48000, len(samples))
        assert wf.readframes(len(samples)) == pcm
    with open(p, "rb") as f:
        riff = f.read()
    assert struct.unpack("<I", riff[4:8])[0] == len(riff) - 8
    assert ensure_plain_pcm_header(p) is False, "already plain: nothing to do"
    assert not os.path.exists(p + ".pcm-header.tmp")


def test_ensure_plain_pcm_header_leaves_other_files_alone(tmp_path):
    p16 = write_tone(str(tmp_path / "p16.wav"), seconds=0.01, sampwidth=2)
    assert ensure_plain_pcm_header(p16) is False
    junk = tmp_path / "junk.wav"
    junk.write_bytes(b"RIFF....WAVEjunk")
    assert ensure_plain_pcm_header(str(junk)) is False
    assert ensure_plain_pcm_header(str(tmp_path / "missing.wav")) is False


def test_parse_loudnorm_json_skips_braces_in_file_names():
    text = ("Input #0, wav, from 'take {1}.wav':\n ... \n"
            '{\n\t"input_i" : "-23.75",\n\t"input_tp" : "-20.00",\n\t"target_offset" : "0.00"\n}\n')
    assert parse_loudnorm_json(text)["input_i"] == "-23.75"
    assert parse_loudnorm_json("no json here {") is None


# --- real ffmpeg ----------------------------------------------------------------

@needs_ffmpeg
def test_peak_mode_boosts_quiet_files_and_keeps_24_bit(tmp_path):
    src = write_tone(str(tmp_path / "quiet.wav"), amp_db=-20, sampwidth=3)
    dst = str(tmp_path / "out" / "quiet.wav")
    r = Normalizer({}).normalize_file(src, dst)
    assert r.ok and not r.canceled and r.error is None, r
    peak, sw, rate, secs = wav_info(dst)
    assert abs(peak - (-2.0)) < 0.2
    assert sw == 3 and rate == 48000 and abs(secs - 1.0) < 0.01
    assert abs(r.gain_db - 18.0) < 0.2
    assert not r.trimmed
    # Same header style as the app's own 24-bit recordings (classic PCM tag),
    # so an exported file imported back still plays through the wave module.
    assert _fmt_chunk(dst) == (1, 16, [])


@needs_ffmpeg
def test_peak_mode_only_boosts_by_default_but_can_attenuate(tmp_path):
    src = write_tone(str(tmp_path / "loud.wav"), amp_db=-1, sampwidth=2)
    r = Normalizer({}).normalize_file(src, str(tmp_path / "a.wav"))
    assert r.ok and r.gain_db == 0.0
    assert abs(wav_info(str(tmp_path / "a.wav"))[0] - (-1.0)) < 0.2
    r2 = Normalizer({"peakOnlyBoost": False, "peakTargetDb": -6}).normalize_file(src, str(tmp_path / "b.wav"))
    assert r2.ok and abs(r2.gain_db - (-5.0)) < 0.2
    assert abs(wav_info(str(tmp_path / "b.wav"))[0] - (-6.0)) < 0.2


@needs_ffmpeg
def test_bit_depth_setting_controls_the_output(tmp_path):
    src24 = write_tone(str(tmp_path / "s24.wav"), amp_db=-20, sampwidth=3)
    src16 = write_tone(str(tmp_path / "s16.wav"), amp_db=-20, sampwidth=2)
    assert Normalizer({"targetBitDepth": 16}).normalize_file(src24, str(tmp_path / "o16.wav")).ok
    assert wav_info(str(tmp_path / "o16.wav"))[1] == 2
    assert Normalizer({"targetBitDepth": 24}).normalize_file(src24, str(tmp_path / "o24.wav")).ok
    assert wav_info(str(tmp_path / "o24.wav"))[1] == 3
    # 24-bit target never up-converts a 16-bit source
    assert Normalizer({"targetBitDepth": 24}).normalize_file(src16, str(tmp_path / "o16b.wav")).ok
    assert wav_info(str(tmp_path / "o16b.wav"))[1] == 2


@needs_ffmpeg
def test_lufs_two_pass_uses_the_measurement_and_keeps_the_sample_rate(tmp_path):
    src = write_tone(str(tmp_path / "q.wav"), amp_db=-20, sampwidth=3)
    dst = str(tmp_path / "lufs.wav")
    r = Normalizer({"normMode": "lufs"}).normalize_file(src, dst)
    assert r.ok, r
    assert "measured_I" in r.measured, "two-pass measurement was not parsed"
    assert any("two-pass" in n for n in r.notes)
    peak, sw, rate, secs = wav_info(dst)
    assert rate == 48000, "loudnorm must not leave the output at 192 kHz"
    assert sw == 3 and abs(secs - 1.0) < 0.01
    assert -20 < peak < 0 and peak > -20 + 3, "LUFS mode should have raised the level"


@needs_ffmpeg
def test_lufs_single_pass_mode(tmp_path):
    src = write_tone(str(tmp_path / "q.wav"), amp_db=-20, sampwidth=2)
    dst = str(tmp_path / "fast.wav")
    r = Normalizer({"normMode": "lufs", "fastNormalize": True}).normalize_file(src, dst)
    assert r.ok and "measured_I" not in r.measured
    peak, sw, rate, _ = wav_info(dst)
    assert rate == 48000 and sw == 2 and peak > -17


@needs_ffmpeg
@pytest.mark.parametrize("settings", [{}, {"normMode": "lufs"}, {"normMode": "lufs", "fastNormalize": True}])
def test_digital_silence_is_left_unchanged(tmp_path, settings):
    """Dynamic loudnorm on all-zero input renders full-scale noise; never do that."""
    src = write_tone(str(tmp_path / "silence.wav"), amp_db=-999, sampwidth=3)
    dst = str(tmp_path / "out.wav")
    r = Normalizer(settings).normalize_file(src, dst)
    assert r.ok and r.gain_db == 0.0
    peak, _, rate, secs = wav_info(dst)
    assert peak == float("-inf") and rate == 48000 and abs(secs - 1.0) < 0.01


@needs_ffmpeg
def test_auto_trim_removes_padding_and_keeps_the_pad(tmp_path):
    src = write_tone(str(tmp_path / "padded.wav"), seconds=1.0, amp_db=-12, sampwidth=3,
                     lead_silence=1.5, trail_silence=1.5)
    plain = Normalizer({}).normalize_file(src, str(tmp_path / "plain.wav"))
    assert plain.ok and not plain.trimmed and abs(wav_info(str(tmp_path / "plain.wav"))[3] - 4.0) < 0.01
    trimmed = Normalizer({"autoTrim": True}).normalize_file(src, str(tmp_path / "trim.wav"))
    assert trimmed.ok and trimmed.trimmed
    secs = wav_info(str(tmp_path / "trim.wav"))[3]
    # 1.0 s of tone plus 0.8 s padding each side (conservative detection adds a little)
    assert 2.4 < secs < 3.2, secs
    # short files are never trimmed
    short = write_tone(str(tmp_path / "short.wav"), seconds=0.3, amp_db=-12, lead_silence=0.2)
    r = Normalizer({"autoTrim": True}).normalize_file(short, str(tmp_path / "short_out.wav"))
    assert r.ok and not r.trimmed and any("shorter than" in n for n in r.notes)


@needs_ffmpeg
def test_unreadable_file_reports_an_error_and_writes_nothing(tmp_path):
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"RIFF....WAVEjunk")
    dst = str(tmp_path / "out.wav")
    r = Normalizer({}).normalize_file(str(bad), dst)
    assert not r.ok and r.error and "Invalid data" in r.error
    assert not os.path.exists(dst)
    r2 = Normalizer({}).normalize_file(str(tmp_path / "missing.wav"), dst)
    assert not r2.ok and "missing" in r2.error


@needs_ffmpeg
def test_normalize_many_reports_each_file_in_order(tmp_path):
    a = write_tone(str(tmp_path / "a.wav"), amp_db=-20)
    b = tmp_path / "b.wav"
    b.write_bytes(b"RIFF....WAVEjunk")
    c = write_tone(str(tmp_path / "c.wav"), amp_db=-10)
    seen = []
    results = Normalizer({}).normalize_many(
        [(a, str(tmp_path / "o" / "a.wav")), (str(b), str(tmp_path / "o" / "b.wav")), (c, str(tmp_path / "o" / "c.wav"))],
        progress=lambda i, n, name: seen.append((i, n, name)),
    )
    assert [r.ok for r in results] == [True, False, True]
    assert seen == [(0, 3, "a.wav"), (1, 3, "b.wav"), (2, 3, "c.wav")]
    assert os.path.exists(str(tmp_path / "o" / "c.wav")) and not os.path.exists(str(tmp_path / "o" / "b.wav"))


@needs_ffmpeg
def test_cancel_stops_the_batch_and_removes_partial_output(tmp_path):
    srcs = [write_tone(str(tmp_path / f"{i}.wav"), seconds=60.0, amp_db=-20, sampwidth=2) for i in range(3)]
    pairs = [(s, str(tmp_path / "o" / os.path.basename(s))) for s in srcs]
    norm = Normalizer({"normMode": "lufs"})  # two passes at 192 kHz: slow enough to cancel

    def cancel_on_first(i, n, name):
        if i == 0:
            threading.Timer(0.2, norm.cancel).start()

    results = norm.normalize_many(pairs, progress=cancel_on_first)
    assert norm.canceled
    assert results and results[-1].canceled
    assert len(results) < 3 or all(r.canceled for r in results[1:])
    assert not os.path.exists(pairs[0][1]), "a canceled render must not leave a partial WAV"


def test_result_name():
    assert NormalizeResult(source="/x/y/take.wav", output="/o").name == "take.wav"


def test_missing_ffmpeg_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(N, "resolve_ff_tools", lambda: {"ffmpeg": None, "ffprobe": None})
    monkeypatch.setattr(N.shutil, "which", lambda name: None)
    with pytest.raises(NormalizeError, match="ffmpeg not found"):
        Normalizer({})


def _fake_tool(tmp_path, name, body):
    """An executable stand-in for ffmpeg/ffprobe (POSIX shell script)."""
    p = tmp_path / name
    p.write_text("#!/bin/sh\n" + body)
    p.chmod(0o755)
    return str(p)


@pytest.mark.skipif(os.name == "nt", reason="shell-script stand-ins")
def test_probe_tool_tells_a_working_ffmpeg_from_a_silent_launcher(tmp_path):
    good = _fake_tool(tmp_path, "ffmpeg", 'echo "ffmpeg version 9.9-test Copyright"\n')
    ok, detail = N.probe_tool(good, "ffmpeg")
    assert ok and detail.startswith("ffmpeg version 9.9-test")
    # What the Chocolatey shim shipped in the 2.3.x-2.4.1 Windows builds does
    # away from its install: exits non-zero and says nothing.
    shim = _fake_tool(tmp_path, "ffmpeg-shim", "exit 1\n")
    ok, detail = N.probe_tool(shim, "ffmpeg")
    assert not ok and "exit code 1" in detail and "no output" in detail
    ok, detail = N.probe_tool(str(tmp_path / "nope"), "ffmpeg")
    assert not ok and "cannot be started" in detail


@pytest.mark.skipif(os.name == "nt", reason="shell-script stand-ins")
def test_find_ff_tools_skips_a_broken_bundled_ffmpeg_and_names_it(tmp_path, monkeypatch):
    shim = _fake_tool(tmp_path, "ffmpeg", "exit 1\n")
    monkeypatch.setattr(N, "resolve_ff_tools", lambda: {"ffmpeg": shim, "ffprobe": None})
    # No system ffmpeg either: the error names the broken file and its exit code.
    monkeypatch.setattr(N.shutil, "which", lambda name: None)
    with pytest.raises(NormalizeError) as e:
        N.find_ff_tools()
    assert shim in str(e.value) and "exit code 1" in str(e.value)
    # A working system ffmpeg on PATH is used instead of the broken bundled one.
    good = _fake_tool(tmp_path, "ffmpeg-system", 'echo "ffmpeg version 9.9-test"\n')
    monkeypatch.setattr(N.shutil, "which", lambda name: good if name == "ffmpeg" else None)
    assert N.find_ff_tools() == (good, "")
