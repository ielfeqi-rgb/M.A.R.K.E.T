use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use tracing::{error, info};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum InstallState {
    NotInstalled,
    InProgress { step: String, percent: u8 },
    Completed { binary_path: String },
    Failed { error: String },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlamaServerStatus {
    pub is_running: bool,
    pub is_installed: bool,
    pub pid: Option<u32>,
    pub port: u16,
    pub active_model: Option<String>,
    pub install_state: InstallState,
}

pub struct LlamaManager {
    process: Arc<Mutex<Option<Child>>>,
    active_model_name: Arc<Mutex<Option<String>>>,
    install_state: Arc<Mutex<InstallState>>,
}

impl LlamaManager {
    pub fn new() -> Self {
        let binary_opt = Self::locate_binary();
        let installed = binary_opt.is_some();
        let init_state = if installed {
            InstallState::Completed {
                binary_path: binary_opt.unwrap().to_string_lossy().to_string(),
            }
        } else {
            InstallState::NotInstalled
        };

        Self {
            process: Arc::new(Mutex::new(None)),
            active_model_name: Arc::new(Mutex::new(None)),
            install_state: Arc::new(Mutex::new(init_state)),
        }
    }

    pub fn get_workspace_dir() -> PathBuf {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        PathBuf::from(home).join("omnicontext_ai")
    }

    pub fn locate_binary() -> Option<PathBuf> {
        let ws = Self::get_workspace_dir();
        let candidates = vec![
            ws.join("llama-server"),
            ws.join("bin/llama-server"),
            ws.join("llama-b10977/llama-server"),
            ws.join("llama.cpp/build/bin/llama-server"),
            PathBuf::from("llama.cpp/build/bin/llama-server"),
            PathBuf::from("llama-server"),
            PathBuf::from("./llama-server"),
            PathBuf::from("/usr/local/bin/llama-server"),
            PathBuf::from("/usr/bin/llama-server"),
        ];

        for path in candidates {
            if path.exists() {
                return Some(path);
            }
        }

        if let Ok(output) = Command::new("which").arg("llama-server").output() {
            if output.status.success() {
                let bin = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !bin.is_empty() {
                    let pb = PathBuf::from(bin);
                    if pb.exists() {
                        return Some(pb);
                    }
                }
            }
        }

        None
    }

    pub fn status(&self) -> LlamaServerStatus {
        let mut proc_guard = self.process.lock().unwrap();
        let mut is_running = false;
        let mut pid = None;

        if let Some(child) = proc_guard.as_mut() {
            match child.try_wait() {
                Ok(None) => {
                    is_running = true;
                    pid = Some(child.id());
                }
                _ => {
                    *proc_guard = None;
                }
            }
        }

        let is_installed = Self::locate_binary().is_some();
        let install_state = self.install_state.lock().unwrap().clone();
        let active_model = self.active_model_name.lock().unwrap().clone();

        LlamaServerStatus {
            is_running,
            is_installed,
            pid,
            port: 8081,
            active_model,
            install_state,
        }
    }

    pub fn start(
        &self,
        model_filename: &str,
        threads: usize,
        context_size: usize,
        port: u16,
    ) -> Result<u32, String> {
        let mut proc_guard = self.process.lock().unwrap();
        if proc_guard.is_some() {
            return Err("الخادم قيد التشغيل بالفعل".to_string());
        }

        let binary = Self::locate_binary()
            .ok_or_else(|| "ملف تشغيل llama-server غير موجود. يرجى تثبيته أولاً عبر الزر.".to_string())?;

        let ws = Self::get_workspace_dir();
        let candidates = vec![
            ws.join("models").join(model_filename),
            ws.join(model_filename),
            PathBuf::from("models").join(model_filename),
            PathBuf::from(model_filename),
        ];

        let model_path = candidates.into_iter().find(|p| p.exists())
            .unwrap_or_else(|| ws.join("models").join(model_filename));

        if !model_path.exists() {
            return Err(format!(
                "ملف النموذج غير موجود في المسار: {:?}. يرجى الضغط على زر التثبيت والتنزيل أولاً.",
                model_path
            ));
        }

        let actual_threads = if threads == 0 {
            std::thread::available_parallelism().map(|n| n.get()).unwrap_or(2)
        } else {
            threads
        };

        let bin_dir = binary.parent().unwrap_or(&ws);
        let existing_ld = std::env::var("LD_LIBRARY_PATH").unwrap_or_default();
        let new_ld = format!(
            "{}:{}:{}:{}:{}",
            bin_dir.display(),
            ws.display(),
            ws.join("llama-b10977").display(),
            ws.join("llama.cpp/build/bin").display(),
            existing_ld
        );

        match Command::new(&binary)
            .env("LD_LIBRARY_PATH", new_ld)
            .arg("-m")
            .arg(&model_path)
            .arg("-c")
            .arg(context_size.to_string())
            .arg("-t")
            .arg(actual_threads.to_string())
            .arg("--host")
            .arg("0.0.0.0")
            .arg("--port")
            .arg(port.to_string())
            .spawn()
        {
            Ok(child) => {
                let id = child.id();
                *proc_guard = Some(child);
                *self.active_model_name.lock().unwrap() = Some(model_filename.to_string());
                info!("تم تشغيل llama-server بنجاح PID: {}", id);
                Ok(id)
            }
            Err(e) => Err(format!("فشل في تشغيل llama-server: {}", e)),
        }
    }

    pub fn stop(&self) -> Result<(), String> {
        let mut proc_guard = self.process.lock().unwrap();
        if let Some(mut child) = proc_guard.take() {
            let _ = child.kill();
            *self.active_model_name.lock().unwrap() = None;
            info!("تم إيقاف llama-server");
            Ok(())
        } else {
            Ok(())
        }
    }

    pub fn trigger_install(
        &self,
        model_url: String,
        model_filename: String,
        threads: usize,
    ) {
        let state_arc = Arc::clone(&self.install_state);

        tokio::task::spawn_blocking(move || {
            *state_arc.lock().unwrap() = InstallState::InProgress {
                step: "تجهيز المجلدات وبيئة التثبيت على النظام...".to_string(),
                percent: 10,
            };

            let ws = Self::get_workspace_dir();
            let models_dir = ws.join("models");
            let _ = fs::create_dir_all(&models_dir);

            let binary_path = ws.join("llama-server");

            if !binary_path.exists() {
                // Check if cmake build works
                let has_cmake = Command::new("which").arg("cmake").output().map(|o| o.status.success()).unwrap_or(false);

                if has_cmake {
                    let llama_dir = ws.join("llama.cpp");
                    if !llama_dir.exists() {
                        *state_arc.lock().unwrap() = InstallState::InProgress {
                            step: "جاري استنساخ مستودع llama.cpp من GitHub...".to_string(),
                            percent: 25,
                        };
                        let _ = Command::new("git")
                            .arg("clone")
                            .arg("https://github.com/ggerganov/llama.cpp.git")
                            .arg(&llama_dir)
                            .status();
                    }

                    if llama_dir.exists() {
                        *state_arc.lock().unwrap() = InstallState::InProgress {
                            step: "جاري تجميع وبناء llama.cpp محلياً بـ AVX2...".to_string(),
                            percent: 50,
                        };
                        let _ = Command::new("cmake")
                            .current_dir(&llama_dir)
                            .arg("-B")
                            .arg("build")
                            .arg("-DGGML_AVX2=ON")
                            .arg("-DGGML_NATIVE=ON")
                            .status();

                        let _ = Command::new("cmake")
                            .current_dir(&llama_dir)
                            .arg("--build")
                            .arg("build")
                            .arg("--config")
                            .arg("Release")
                            .arg(format!("-j{}", threads.max(1)))
                            .status();

                        let compiled_bin = ws.join("llama.cpp/build/bin/llama-server");
                        if compiled_bin.exists() {
                            let _ = fs::copy(&compiled_bin, &binary_path);
                        }
                    }
                }

                // Fallback: Prebuilt binary download
                if !binary_path.exists() {
                    *state_arc.lock().unwrap() = InstallState::InProgress {
                        step: "جاري تحميل النسخة المجهزة المباشرة (Prebuilt llama-server for Linux)...".to_string(),
                        percent: 60,
                    };

                    let prebuilt_tar = ws.join("llama-prebuilt.tar.gz");
                    let prebuilt_url = "https://github.com/ggml-org/llama.cpp/releases/download/b10977/llama-b10977-bin-ubuntu-x64.tar.gz";

                    let curl_res = Command::new("curl")
                        .arg("-L")
                        .arg("-s")
                        .arg(prebuilt_url)
                        .arg("-o")
                        .arg(&prebuilt_tar)
                        .status();

                    if curl_res.is_ok() && prebuilt_tar.exists() {
                        let _ = Command::new("tar")
                            .arg("-xzf")
                            .arg(&prebuilt_tar)
                            .arg("-C")
                            .arg(&ws)
                            .status();
                        let _ = fs::remove_file(&prebuilt_tar);
                    }

                    // Copy extracted binary to ws/llama-server
                    let extracted_bin = ws.join("llama-b10977/llama-server");
                    if extracted_bin.exists() {
                        let _ = fs::copy(&extracted_bin, &binary_path);
                        // Copy shared libs to ws/
                        if let Ok(entries) = fs::read_dir(ws.join("llama-b10977")) {
                            for entry in entries.flatten() {
                                let path = entry.path();
                                let fname = path.file_name().unwrap_or_default().to_string_lossy().to_string();
                                if fname.contains(".so") || fname.contains(".dylib") {
                                    let target = ws.join(&fname);
                                    let _ = fs::copy(&path, &target);
                                }
                            }
                        }
                    }
                }
            }

            // Step 3: Download Model GGUF
            let target_model = models_dir.join(&model_filename);
            if !target_model.exists() {
                *state_arc.lock().unwrap() = InstallState::InProgress {
                    step: format!("جاري تنزيل ملف النموذج ({}) من HuggingFace...", model_filename),
                    percent: 85,
                };

                let curl_res = Command::new("curl")
                    .arg("-L")
                    .arg(&model_url)
                    .arg("-o")
                    .arg(&target_model)
                    .status();

                if curl_res.is_err() || !curl_res.unwrap().success() {
                    *state_arc.lock().unwrap() = InstallState::Failed {
                        error: format!("فشل تنزيل ملف النموذج {}. تحقق من الاتصال بالموقع.", model_filename),
                    };
                    return;
                }
            }

            let final_bin = Self::locate_binary().unwrap_or(binary_path);
            let _ = Command::new("chmod").arg("+x").arg(&final_bin).status();

            *state_arc.lock().unwrap() = InstallState::Completed {
                binary_path: final_bin.to_string_lossy().to_string(),
            };
        });
    }
}
