import os
import signal
import select
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
        stopping = threading.Event()

        def consume():
            pending = b""
            while not stopping.is_set():
                if os.name == "nt":
                    chunk = proc.stdout.read1(4096)
                else:
                    # Poll the FD so an escaped process holding a pipe cannot block close().
                    if not select.select([proc.stdout], [], [], 0.1)[0]:
                        continue
                    chunk = os.read(proc.stdout.fileno(), 4096)
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
            # A leader may exit while descendants still own its output pipes. The deadline
            # and cancellation guard apply until BOTH the process and its reader finish.
            while proc.poll() is None or reader.is_alive():
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
            if os.name == "nt":
                if proc.poll() is None:
                    subprocess.run(
                        ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=10,
                    )
            else:
                try:
                    # Remotion closes its detached Chrome group in a SIGTERM handler.
                    # Allow that cleanup before escalating, rather than immediately orphaning it.
                    os.killpg(proc.pid, signal.SIGTERM)
                    if proc.poll() is None:
                        try:
                            proc.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            pass
                    else:
                        reader.join(timeout=1)
                except ProcessLookupError:
                    pass
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if proc.poll() is None:
                proc.wait(timeout=10)
            stopping.set()
            reader.join(timeout=3)
            if proc.stdout:
                proc.stdout.close()
