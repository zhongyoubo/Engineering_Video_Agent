"""Run a local Python pipeline with all IP socket creation blocked by kernel seccomp."""

import ctypes, ctypes.util, errno, runpy, sys, os

# Prevent dependency analytics before any model library import.
os.environ.update(
    {
        "HF_HUB_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "DO_NOT_TRACK": "1",
        "GRADIO_ANALYTICS_ENABLED": "False",
        "TOKENIZERS_PARALLELISM": "false",
    }
)
lib = ctypes.CDLL(ctypes.util.find_library("seccomp"), use_errno=True)
lib.seccomp_init.argtypes = [ctypes.c_uint32]
lib.seccomp_init.restype = ctypes.c_void_p
lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
lib.seccomp_rule_add_array.argtypes = [
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.c_int,
    ctypes.c_uint,
    ctypes.c_void_p,
]
lib.seccomp_load.argtypes = [ctypes.c_void_p]
lib.seccomp_release.argtypes = [ctypes.c_void_p]


class Arg(ctypes.Structure):
    _fields_ = [
        ("arg", ctypes.c_uint),
        ("op", ctypes.c_uint),
        ("datum_a", ctypes.c_uint64),
        ("datum_b", ctypes.c_uint64),
    ]


ctx = lib.seccomp_init(0x7FFF0000)
if not ctx:
    raise RuntimeError("No seccomp context; refusing to run without network isolation")
try:
    for domain in [2, 10]:
        rule = Arg(0, 4, domain, 0)  # SCMP_CMP_EQ; AF_INET / AF_INET6.
        if (
            lib.seccomp_rule_add_array(
                ctx,
                0x00050000 | errno.EPERM,
                lib.seccomp_syscall_resolve_name(b"socket"),
                1,
                ctypes.byref(rule),
            )
            != 0
        ):
            raise RuntimeError("Cannot install socket denial rule")
    if lib.seccomp_load(ctx) != 0:
        raise RuntimeError("Cannot enforce network isolation")
finally:
    lib.seccomp_release(ctx)
# Verify kernel enforcement before importing model dependencies.
import socket

for family in (socket.AF_INET, socket.AF_INET6):
    try:
        s = socket.socket(family, socket.SOCK_STREAM)
    except PermissionError:
        pass
    else:
        s.close()
        raise RuntimeError("Network isolation failed")
print("OFFLINE VERIFIED: IPv4 and IPv6 socket creation denied by kernel.", flush=True)
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
