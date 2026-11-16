import os
import signal
import subprocess
import threading
import time


class ProcessError(RuntimeError):
    pass


class Runner:
    def __init__(self, guard=lambda: None):
        self.guard = guard

    def run(self, args, cwd=None, timeout=120, env=None, on_line=None):
        self.guard()
        proc = subprocess.Popen(
            [str(a) for a in args],
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        chunks, size, overflow = [], [0], threading.Event()
        callback_errors = []

        def consume():
            pending = b""
            while True:
                chunk = proc.stdout.read1(4096)
                if not chunk:
                    break
                size[0] += len(chunk)
                if size[0] > 4 * 1024 * 1024:
                    overflow.set()
                    break
                chunks.append(chunk)
                if on_line:
                    pending += chunk
                    while b"\n" in pending:
                        line, pending = pending.split(b"\n", 1)
                        try:
                            on_line(line.decode("utf-8", errors="replace"))
                        except Exception as exc:
                            callback_errors.append(exc)
                            return
            if on_line and pending:
                try:
                    on_line(pending.decode("utf-8", errors="replace"))
                except Exception as exc:
                    callback_errors.append(exc)

        reader = threading.Thread(target=consume, daemon=True)
        reader.start()
        start = time.monotonic()
        try:
            while proc.poll() is None:
                self.guard()
                if callback_errors:
                    raise ProcessError("Process event handler failed") from callback_errors[0]
                if overflow.is_set():
                    raise ProcessError("Process log limit exceeded")
                if time.monotonic() - start > timeout:
                    raise ProcessError("Process timeout")
                time.sleep(0.15)
            reader.join(timeout=3)
            if callback_errors:
                raise ProcessError("Process event handler failed") from callback_errors[0]
            text = b"".join(chunks).decode("utf-8", errors="replace")
            if overflow.is_set():
                raise ProcessError("Process log limit exceeded")
            if proc.returncode:
                raise ProcessError(f"Process failed ({proc.returncode}): {text[-2500:]}")
            return text
        finally:
            if proc.poll() is None:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=10,
                    )
                else:
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
            if proc.stdout:
                proc.stdout.close()
