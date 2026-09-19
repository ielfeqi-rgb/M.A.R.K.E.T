import os
import sys
import shutil
import subprocess
import threading
import time
import logging
import traceback
import zipfile
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def _run_cmd_live(cmd: List[str], cwd: Optional[Path] = None, step_name: str = "LlamaBuild"):
    """Run a subprocess command and stream output line-by-line directly to logger."""
    logger.info(f"[{step_name}] Executing: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    output_lines = []
    if proc.stdout:
        for line in iter(proc.stdout.readline, ''):
            l = line.strip()
            if l:
                output_lines.append(l)
                logger.info(f"[{step_name}] {l}")
        proc.stdout.close()

    rc = proc.wait()
    if rc != 0:
        tail = "\n".join(output_lines[-10:]) if output_lines else "No output"
        err_msg = f"Command '{' '.join(cmd)}' failed (Exit code {rc}).\nLast terminal output:\n{tail}"
        logger.error(f"[{step_name} ERROR] {err_msg}")
        raise RuntimeError(err_msg)


class LlamaCppManager:
    """
    Supervises the llama.cpp / llama-server local execution engine process:
    - Prebuilt binary auto-download for Tiny Core Linux & minimal distros
    - CMake compilation fallback when build environment is present
    - Process startup (-m, -c, -t, --port)
    - Process status tracking & graceful shutdown
    """

    def __init__(self):
        self.base_dir = Path.home() / "omnicontext_ai"
        self.models_dir = self.base_dir / "models"
        self.llama_dir = self.base_dir / "llama.cpp"
        
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self._process: Optional[subprocess.Popen] = None
        self._running_model: Optional[str] = None
        self._running_port: int = 8081
        self._lock = threading.RLock()
        
        # Install progress tracking
        self.install_state: Dict[str, Any] = {
            "status": "idle",  # idle, installing, completed, failed
            "step": "لم يبدأ التثبيت بعد",
            "percent": 0,
            "error": None
        }

    def find_cmake(self) -> Optional[str]:
        """Search for cmake binary in PATH or Python local bin."""
        res = shutil.which("cmake")
        if res:
            return res
        
        user_local = Path.home() / ".local" / "bin" / "cmake"
        if user_local.exists():
            return str(user_local)

        py_bin = Path(sys.prefix) / "bin" / "cmake"
        if py_bin.exists():
            return str(py_bin)

        return None

    def find_binary(self) -> Optional[str]:
        """Search for llama-server binary across priority paths (Bundled LTS binary first)."""
        project_root = Path(__file__).parent.resolve()
        candidates = [
            project_root / "bin" / "llama-server",
            project_root / "llama-server",
            self.base_dir / "llama-server",
            self.base_dir / "bin" / "llama-server",
            self.llama_dir / "build" / "bin" / "llama-server",
            Path("./bin/llama-server"),
            Path("./llama-server"),
            Path("/usr/local/bin/llama-server"),
            Path("/usr/bin/llama-server")
        ]

        for path in candidates:
            if path.exists() and os.access(path, os.X_OK):
                return str(path.resolve())

        # System PATH lookup
        sys_path = shutil.which("llama-server")
        if sys_path:
            return sys_path

        return None

    def get_status(self) -> Dict[str, Any]:
        """Return engine execution status."""
        with self._lock:
            is_running = False
            pid = None

            if self._process is not None:
                poll = self._process.poll()
                if poll is None:
                    is_running = True
                    pid = self._process.pid
                else:
                    self._process = None
                    self._running_model = None

            binary_path = self.find_binary()
            installed = binary_path is not None

            # Downloaded GGUF models
            models = []
            if self.models_dir.exists():
                for f in self.models_dir.glob("*.gguf"):
                    models.append({
                        "filename": f.name,
                        "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
                        "path": str(f.resolve())
                    })

            return {
                "installed": installed,
                "binary_path": binary_path,
                "running": is_running,
                "pid": pid,
                "port": self._running_port,
                "running_model": self._running_model,
                "install_state": self.install_state,
                "available_gguf_models": models
            }

    def download_prebuilt_binary(self) -> str:
        """Download pre-compiled static binary for Linux x86_64 (Tiny Core / Minimal OS Fallback)."""
        logger.info("[LlamaInstall Fallback] Minimal OS detected (Tiny Core / No build tools). Switching to prebuilt binary download...")
        self.install_state["step"] = "تنزيل ثنائي llama-server الجاهز للنظم المصغرة (Tiny Core)..."
        self.install_state["percent"] = 30

        # Stable prebuilt release binary zip
        release_url = "https://github.com/ggerganov/llama.cpp/releases/download/b4800/llama-b4800-bin-ubuntu-x64.zip"
        zip_path = self.base_dir / "llama-server-prebuilt.zip"

        logger.info(f"[LlamaInstall Fallback] Downloading prebuilt binary from: {release_url}")

        req = urllib.request.Request(release_url, headers={"User-Agent": "M.A.R.K.E.T-AI-Engine"})
        with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as f:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 1024 * 1024
            while True:
                buffer = resp.read(block_size)
                if not buffer:
                    break
                downloaded += len(buffer)
                f.write(buffer)
                if total_size > 0:
                    pct = int(30 + (downloaded / total_size) * 45)
                    self.install_state["percent"] = pct
                    self.install_state["step"] = f"تنزيل llama-server الثنائي الجاهز ({round(downloaded/1048576, 1)}MB / {round(total_size/1048576, 1)}MB)..."

        # Extract executable binary
        self.install_state["step"] = "فك ضغط الملفات الثنائية الجاهزة..."
        self.install_state["percent"] = 80
        logger.info("[LlamaInstall Fallback] Extracting prebuilt binaries...")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                if "llama-server" in member or "llama-cli" in member:
                    filename = os.path.basename(member)
                    if filename:
                        dest = self.base_dir / filename
                        with zip_ref.open(member) as source, open(dest, "wb") as target:
                            shutil.copyfileobj(source, target)
                        os.chmod(dest, 0o755)
                        logger.info(f"[LlamaInstall Fallback] Extracted executable: {dest}")

        if zip_path.exists():
            zip_path.unlink()

        final_binary = self.find_binary()
        if not final_binary:
            raise RuntimeError("تم تنزيل الثنائي الجاهز ولكن لم يتم إيجاد llama-server")

        logger.info(f"[LlamaInstall Fallback SUCCESS] Prebuilt binary ready at: {final_binary}")
        return final_binary

    def start(self, model_filename: str, threads: int = 4, context_size: int = 4096, port: int = 8081) -> Dict[str, Any]:
        """Spawn llama-server process with the specified GGUF model."""
        with self._lock:
            binary = self.find_binary()
            if not binary:
                err = "محرك llama-server غير مثبت على الجهاز. يرجى الضغط على زر 'تثبيت/بناء محرك llama.cpp' أولاً."
                logger.error(f"[LlamaEngine] {err}")
                return {"success": False, "error": err}

            # If already running, stop existing instance
            if self._process and self._process.poll() is None:
                self.stop()

            model_path = self.models_dir / model_filename
            if not model_path.exists():
                alt_path = Path(model_filename)
                if alt_path.exists():
                    model_path = alt_path
                else:
                    err = f"ملف الموديل '{model_filename}' غير موجود في {self.models_dir}"
                    logger.error(f"[LlamaEngine] {err}")
                    return {"success": False, "error": err}

            cmd = [
                binary,
                "-m", str(model_path.resolve()),
                "-c", str(context_size),
                "-t", str(threads),
                "--host", "0.0.0.0",
                "--port", str(port)
            ]

            env = os.environ.copy()
            bin_dir = str(Path(binary).parent.resolve())
            current_ld = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = f"{bin_dir}:{current_ld}".strip(":")

            try:
                logger.info(f"[LlamaEngine] Spawning llama-server process: {' '.join(cmd)}")
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env
                )
                self._running_model = model_filename
                self._running_port = port

                time.sleep(1.5)
                poll = self._process.poll()
                if poll is not None:
                    out, _ = self._process.communicate()
                    err = f"فشل تشغيل llama-server (Exit code {poll}):\n{out[:500]}"
                    logger.error(f"[LlamaEngine Error] {err}")
                    self._process = None
                    self._running_model = None
                    return {"success": False, "error": err}

                msg = f"تم تشغيل المحرك المحلي llama-server بنجاح على المنفذ {port} (PID: {self._process.pid})"
                logger.info(f"[LlamaEngine] {msg}")
                return {
                    "success": True,
                    "pid": self._process.pid,
                    "port": port,
                    "model": model_filename,
                    "message": msg
                }
            except Exception as e:
                logger.error(f"[LlamaEngine Error] Failed to start llama-server: {e}\n{traceback.format_exc()}")
                return {"success": False, "error": str(e)}

    def stop(self) -> Dict[str, Any]:
        """Gracefully terminate the running llama-server process."""
        with self._lock:
            if not self._process:
                return {"success": True, "message": "المحرك متوقف بالفعل"}

            try:
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()

                pid = self._process.pid
                self._process = None
                self._running_model = None
                logger.info(f"[LlamaEngine] llama-server process (PID: {pid}) stopped successfully")
                return {"success": True, "message": "تم إيقاف محرك llama-server بنجاح"}
            except Exception as e:
                logger.error(f"[LlamaEngine Error] Error stopping llama-server: {e}")
                return {"success": False, "error": str(e)}

    def trigger_install(self) -> Dict[str, Any]:
        """Trigger background installation of llama.cpp."""
        with self._lock:
            if self.install_state["status"] == "installing":
                return {"success": False, "message": "عملية التثبيت قيد التشغيل بالفعل"}

            self.install_state = {
                "status": "installing",
                "step": "جاري تحضير بيئة التثبيت...",
                "percent": 5,
                "error": None
            }

            thread = threading.Thread(target=self._async_install_worker, daemon=True)
            thread.start()
            logger.info("[LlamaEngine] Background installation thread launched")
            return {"success": True, "message": "بدأت عملية تثبيت وبناء محرك llama.cpp في الخلفية"}

    def _async_install_worker(self):
        """Worker thread to clone and build llama.cpp, or fallback to prebuilt binary on minimal OS."""
        try:
            logger.info("[LlamaInstall] === Starting llama.cpp setup process ===")
            
            # Step 1: Check git & cmake & build tools
            self.install_state["step"] = "فحص توفر أداة البناء (Git & CMake)..."
            self.install_state["percent"] = 10

            cmake_bin = self.find_cmake()
            has_git = shutil.which("git") is not None
            has_cmake = cmake_bin is not None
            has_gcc = shutil.which("gcc") is not None or shutil.which("clang") is not None or shutil.which("g++") is not None

            # If OS is minimal (like Tiny Core Linux) without build tools: Use prebuilt binary download fallback!
            if not has_git or not has_cmake or not has_gcc:
                logger.warning("[LlamaInstall] Build tools (Git/CMake/GCC) missing or minimal OS (Tiny Core Linux) detected. Switching to Prebuilt Binary Download...")
                self.download_prebuilt_binary()
            else:
                try:
                    # Attempt compilation from source
                    self.install_state["step"] = "استنساخ مستودع llama.cpp..."
                    self.install_state["percent"] = 25

                    if self.llama_dir.exists():
                        _run_cmd_live(["git", "pull"], cwd=self.llama_dir, step_name="GitPull")
                    else:
                        _run_cmd_live(
                            ["git", "clone", "--depth", "1", "https://github.com/ggerganov/llama.cpp.git", str(self.llama_dir)],
                            step_name="GitClone"
                        )

                    self.install_state["step"] = "تجميع بناء CMake (AVX2 Enabled)..."
                    self.install_state["percent"] = 55
                    build_dir = self.llama_dir / "build"

                    _run_cmd_live(
                        [cmake_bin, "-B", str(build_dir), "-DGGML_AVX2=ON", "-DGGML_NATIVE=ON"],
                        cwd=self.llama_dir,
                        step_name="CMakeConfig"
                    )

                    cores = os.cpu_count() or 4
                    self.install_state["step"] = f"بناء ثنائيات llama-server ({cores} أنوية)..."
                    self.install_state["percent"] = 80

                    _run_cmd_live(
                        [cmake_bin, "--build", str(build_dir), "--config", "Release", "-j", str(cores)],
                        cwd=self.llama_dir,
                        step_name="CMakeBuild"
                    )
                except Exception as build_err:
                    logger.warning(f"[LlamaInstall] Source compilation failed ({build_err}). Falling back to prebuilt static binary download...")
                    self.download_prebuilt_binary()

            binary = self.find_binary()
            if not binary:
                raise RuntimeError("لم يتم العثور على ثنائي llama-server بعد التثبيت")

            self.install_state["status"] = "completed"
            self.install_state["step"] = "تم تثبيت وإعداد محرك llama.cpp بنجاح! "
            self.install_state["percent"] = 100
            logger.info(f"[LlamaInstall SUCCESS] Binary ready at: {binary}")

        except Exception as e:
            err_str = str(e)
            logger.error(f"[LlamaInstall FAILED] {err_str}")
            self.install_state["status"] = "failed"
            self.install_state["step"] = f"فشل التثبيت: {err_str[:150]}"
            self.install_state["percent"] = 0
            self.install_state["error"] = err_str


llama_manager = LlamaCppManager()
