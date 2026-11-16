"""Word event timestamps from the actual eSpeak synthesis callback, not text-length estimates."""

import ctypes as C
import ctypes.util
import os
import threading
import wave

_lock = threading.Lock()


class EventId(C.Union):
    _fields_ = [("number", C.c_int), ("name", C.c_char_p), ("string", C.c_char * 8)]


class Event(C.Structure):
    _fields_ = [
        ("type", C.c_int),
        ("unique_identifier", C.c_uint),
        ("text_position", C.c_int),
        ("length", C.c_int),
        ("audio_position", C.c_int),
        ("sample", C.c_int),
        ("user_data", C.c_void_p),
        ("id", EventId),
    ]


def synthesize_events(text, language, path):
    library = os.getenv("ESPEAK_LIBRARY") or ctypes.util.find_library("espeak-ng")
    if not library:
        raise RuntimeError("eSpeak shared library not available")
    with _lock:
        lib = C.CDLL(library)
        lib.espeak_Initialize.argtypes = [C.c_int, C.c_int, C.c_char_p, C.c_int]
        data = os.getenv("ESPEAK_DATA_PATH")
        sr = lib.espeak_Initialize(1, 0, data.encode() if data else None, 0)
        if sr <= 0:
            raise RuntimeError("eSpeak initialization failed")
        samples, events = [], []
        callback_type = C.CFUNCTYPE(C.c_int, C.POINTER(C.c_short), C.c_int, C.POINTER(Event))

        def callback(wav, count, event_list):
            if wav and count:
                samples.append(C.string_at(wav, count * 2))
            i = 0
            while event_list and event_list[i].type:
                item = event_list[i]
                if item.type == 1:
                    events.append(
                        {
                            "offset": max(0, item.text_position - 1),
                            "length": item.length,
                            "start": item.audio_position / 1000,
                        }
                    )
                i += 1
            return 0

        callback_ref = callback_type(callback)
        lib.espeak_SetSynthCallback.argtypes = [callback_type]
        lib.espeak_SetSynthCallback(callback_ref)
        lib.espeak_SetVoiceByName.argtypes = [C.c_char_p]
        if lib.espeak_SetVoiceByName(b"cmn" if language == "zh-CN" else b"en-us+m3"):
            lib.espeak_Terminate()
            raise RuntimeError("Voice not installed")
        lib.espeak_SetParameter(1, 250 if language == "zh-CN" else 170, 0)
        encoded = text.encode("utf-8")
        buffer = C.create_string_buffer(encoded)
        lib.espeak_Synth.argtypes = [
            C.c_void_p,
            C.c_size_t,
            C.c_uint,
            C.c_int,
            C.c_uint,
            C.c_uint,
            C.POINTER(C.c_uint),
            C.c_void_p,
        ]
        try:
            code = lib.espeak_Synth(buffer, len(encoded) + 1, 0, 1, 0, 1 | 0x1000, None, None)
            if code:
                raise RuntimeError("Synthesis failed")
            lib.espeak_Synchronize()
        finally:
            lib.espeak_Terminate()
        with wave.open(str(path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(sr)
            out.writeframes(b"".join(samples))
        duration = sum(map(len, samples)) / (2 * sr)
        words = []
        for i, item in enumerate(events):
            start = item["offset"]
            end = min(len(text), events[i + 1]["offset"] if i + 1 < len(events) else len(text))
            end_time = min(duration, events[i + 1]["start"] if i + 1 < len(events) else duration)
            if end > start and end_time > item["start"]:
                words.append({"text": text[start:end], "start": item["start"], "end": end_time})
        if not samples or not words:
            raise RuntimeError("No audio/word events")
        return words
