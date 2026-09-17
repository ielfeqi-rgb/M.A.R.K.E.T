use serde::{Deserialize, Serialize};
use std::fs;
use std::process::Command;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WorkloadMode {
    CasualTrial,     // Safe, low-footprint mode for desktop multitasking
    DedicatedServer, // 100% hardware dedication for maximum inference speed & capacity
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelSpec {
    pub id: String,
    pub name: String,
    pub category: String,
    pub category_label: String,
    pub size: String,
    pub file_size: String,
    pub quant: String,
    pub ram_required_gb: f32,
    pub recommended_threads: usize,
    pub download_url: String,
    pub filename: String,
    pub context_size: usize,
    pub reasoning: String,
    pub strengths: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemProfile {
    pub cpu_model: String,
    pub cpu_cores: usize,
    pub total_ram_gb: f32,
    pub free_ram_gb: f32,
    pub has_avx2: bool,
    pub has_avx512: bool,
    pub has_cuda: bool,
    pub gpu_name: Option<String>,
    pub gpu_vram_gb: Option<f32>,
    pub active_mode: WorkloadMode,
    pub recommended_model: ModelSpec,
    pub available_models: Vec<ModelSpec>,
}

impl SystemProfile {
    pub fn probe() -> Self {
        Self::probe_with_mode(WorkloadMode::CasualTrial)
    }

    pub fn probe_with_mode(mode: WorkloadMode) -> Self {
        let (cpu_model, cpu_cores, has_avx2, has_avx512) = Self::probe_cpu();
        let (total_ram_gb, free_ram_gb) = Self::probe_memory();
        let (has_cuda, gpu_name, gpu_vram_gb) = Self::probe_gpu();

        let (recommended_model, available_models) = Self::build_model_catalog(
            mode,
            cpu_cores,
            total_ram_gb,
            free_ram_gb,
            has_cuda,
            gpu_vram_gb.unwrap_or(0.0),
        );

        Self {
            cpu_model,
            cpu_cores,
            total_ram_gb,
            free_ram_gb,
            has_avx2,
            has_avx512,
            has_cuda,
            gpu_name,
            gpu_vram_gb,
            active_mode: mode,
            recommended_model,
            available_models,
        }
    }

    fn probe_cpu() -> (String, usize, bool, bool) {
        let mut cores = std::thread::available_parallelism()
            .map(|n| n.get())
            .unwrap_or(2);

        let mut model = "Generic Linux Processor".to_string();
        let mut avx2 = false;
        let mut avx512 = false;

        if let Ok(cpuinfo) = fs::read_to_string("/proc/cpuinfo") {
            let mut detected_cores = 0;
            for line in cpuinfo.lines() {
                let trimmed = line.trim();
                if trimmed.starts_with("model name") || trimmed.starts_with("Hardware") || trimmed.starts_with("Processor") {
                    if let Some(val) = trimmed.split(':').nth(1) {
                        let m = val.trim();
                        if !m.is_empty() && model == "Generic Linux Processor" {
                            model = m.to_string();
                        }
                    }
                } else if trimmed.starts_with("processor") {
                    detected_cores += 1;
                } else if trimmed.starts_with("flags") || trimmed.starts_with("Features") {
                    let lower = trimmed.to_lowercase();
                    if lower.contains(" avx2") || lower.contains(" avx2 ") {
                        avx2 = true;
                    }
                    if lower.contains(" avx512") {
                        avx512 = true;
                    }
                }
            }
            if detected_cores > 0 {
                cores = detected_cores;
            }
        }

        if model == "Generic Linux Processor" {
            if let Ok(output) = Command::new("lscpu").output() {
                if output.status.success() {
                    let text = String::from_utf8_lossy(&output.stdout);
                    for line in text.lines() {
                        if line.starts_with("Model name:") {
                            if let Some(val) = line.split(':').nth(1) {
                                model = val.trim().to_string();
                                break;
                            }
                        }
                    }
                }
            }
        }

        (model, cores, avx2, avx512)
    }

    fn probe_memory() -> (f32, f32) {
        let mut total_kb: f32 = 0.0;
        let mut free_kb: f32 = 0.0;

        if let Ok(meminfo) = fs::read_to_string("/proc/meminfo") {
            for line in meminfo.lines() {
                if line.starts_with("MemTotal:") {
                    if let Some(val) = line.split_whitespace().nth(1) {
                        if let Ok(num) = val.parse::<f32>() {
                            total_kb = num;
                        }
                    }
                } else if line.starts_with("MemAvailable:") {
                    if let Some(val) = line.split_whitespace().nth(1) {
                        if let Ok(num) = val.parse::<f32>() {
                            free_kb = num;
                        }
                    }
                }
            }
        }

        if free_kb == 0.0 && total_kb > 0.0 {
            if let Ok(meminfo) = fs::read_to_string("/proc/meminfo") {
                let mut free_acc = 0.0;
                for line in meminfo.lines() {
                    if line.starts_with("MemFree:") || line.starts_with("Buffers:") || line.starts_with("Cached:") {
                        if let Some(val) = line.split_whitespace().nth(1) {
                            if let Ok(num) = val.parse::<f32>() {
                                free_acc += num;
                            }
                        }
                    }
                }
                if free_acc > 0.0 {
                    free_kb = free_acc;
                }
            }
        }

        if total_kb == 0.0 {
            if let Ok(output) = Command::new("free").arg("-m").output() {
                if output.status.success() {
                    let text = String::from_utf8_lossy(&output.stdout);
                    for line in text.lines() {
                        if line.starts_with("Mem:") {
                            let parts: Vec<&str> = line.split_whitespace().collect();
                            if parts.len() >= 7 {
                                let tot = parts[1].parse::<f32>().unwrap_or(4096.0);
                                let avail = parts[6].parse::<f32>().unwrap_or(tot / 2.0);
                                total_kb = tot * 1024.0;
                                free_kb = avail * 1024.0;
                            }
                        }
                    }
                }
            }
        }

        let total_gb = (total_kb / (1024.0 * 1024.0) * 10.0).round() / 10.0;
        let free_gb = (free_kb / (1024.0 * 1024.0) * 10.0).round() / 10.0;

        (total_gb.max(1.0), free_gb.max(0.5))
    }

    fn probe_gpu() -> (bool, Option<String>, Option<f32>) {
        if let Ok(output) = Command::new("nvidia-smi")
            .arg("--query-gpu=name,memory.total")
            .arg("--format=csv,noheader,nounits")
            .output()
        {
            if output.status.success() {
                let text = String::from_utf8_lossy(&output.stdout);
                let parts: Vec<&str> = text.trim().split(',').collect();
                if parts.len() >= 2 {
                    let name = parts[0].trim().to_string();
                    let vram_mb = parts[1].trim().parse::<f32>().unwrap_or(0.0);
                    return (true, Some(name), Some(((vram_mb / 1024.0) * 10.0).round() / 10.0));
                }
            }
        }
        (false, None, None)
    }

    pub fn build_model_catalog(
        mode: WorkloadMode,
        cores: usize,
        total_ram: f32,
        _free_ram: f32,
        has_cuda: bool,
        gpu_vram: f32,
    ) -> (ModelSpec, Vec<ModelSpec>) {
        let is_server = mode == WorkloadMode::DedicatedServer;
        let trial_threads = if cores > 2 { cores / 2 } else { 1 };
        let server_threads = cores;
        let default_threads = if is_server { server_threads } else { trial_threads };

        let catalog = vec![
            ModelSpec {
                id: "qwen-2.5-1.5b-q4".to_string(),
                name: "Qwen 2.5 1.5B Instruct".to_string(),
                category: "ultra_light".to_string(),
                category_label: "فائق الخفة والسرعة ⚡".to_string(),
                size: "1.5B".to_string(),
                file_size: "986 MB".to_string(),
                quant: "Q4_K_M".to_string(),
                ram_required_gb: 1.5,
                recommended_threads: default_threads.min(2).max(1),
                download_url: "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf".to_string(),
                filename: "qwen2.5-1.5b-instruct-q4_k_m.gguf".to_string(),
                context_size: 2048,
                reasoning: format!("خفيف جداً يستهلك 1.5GB فقط و {} خيوط، مثالي للتجربة اليومية بدون أي عبء على الرامات.", default_threads.min(2).max(1)),
                strengths: vec!["عربي بطلاقة".to_string(), "استهلاك خفيف جداً".to_string(), "استجابة فورية".to_string()],
            },
            ModelSpec {
                id: "llama-3.2-1b-q4".to_string(),
                name: "Llama 3.2 1B Instruct".to_string(),
                category: "ultra_light".to_string(),
                category_label: "فائق الخفة والسرعة ⚡".to_string(),
                size: "1.2B".to_string(),
                file_size: "780 MB".to_string(),
                quant: "Q4_K_M".to_string(),
                ram_required_gb: 1.3,
                recommended_threads: default_threads.min(2).max(1),
                download_url: "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf".to_string(),
                filename: "Llama-3.2-1B-Instruct-Q4_K_M.gguf".to_string(),
                context_size: 2048,
                reasoning: "أخف موديل من Meta، استهلاك ذاكرة فائق الصغر وتنزيل سريع جداً.".to_string(),
                strengths: vec!["أحدث معمارية Meta".to_string(), "حجم 780MB فقط".to_string(), "سريع للغاية".to_string()],
            },
            ModelSpec {
                id: "llama-3.2-3b-q4".to_string(),
                name: "Llama 3.2 3B Instruct".to_string(),
                category: "balanced".to_string(),
                category_label: "ذكاء متوازن وعالي 🧠".to_string(),
                size: "3.2B".to_string(),
                file_size: "2.02 GB".to_string(),
                quant: "Q4_K_M".to_string(),
                ram_required_gb: 3.2,
                recommended_threads: if is_server { server_threads } else { trial_threads.max(2) },
                download_url: "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf".to_string(),
                filename: "Llama-3.2-3B-Instruct-Q4_K_M.gguf".to_string(),
                context_size: 4096,
                reasoning: format!("القمة في توازن الذكاء والحجم، يشغل 3.2GB و {} أنوية مع فهم لغوي رائع.", if is_server { server_threads } else { trial_threads.max(2) }),
                strengths: vec!["فهم وصياغة ممتازة".to_string(), "سياق 4096 توكن".to_string(), "توازن مثالي".to_string()],
            },
            ModelSpec {
                id: "qwen-2.5-3b-q4".to_string(),
                name: "Qwen 2.5 3B Instruct".to_string(),
                category: "balanced".to_string(),
                category_label: "ذكاء متوازن وعالي 🧠".to_string(),
                size: "3.1B".to_string(),
                file_size: "1.98 GB".to_string(),
                quant: "Q4_K_M".to_string(),
                ram_required_gb: 3.3,
                recommended_threads: if is_server { server_threads } else { trial_threads.max(2) },
                download_url: "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf".to_string(),
                filename: "qwen2.5-3b-instruct-q4_k_m.gguf".to_string(),
                context_size: 4096,
                reasoning: "نموذج فائق الدقة في إتباع الأوامر وتلخيص الوثائق مع دعم عربي قوي.".to_string(),
                strengths: vec!["إتباع دقيق للأوامر".to_string(), "دعم عربي ممتاز".to_string(), "دقة معرفية".to_string()],
            },
            ModelSpec {
                id: "qwen-2.5-coder-1.5b-q4".to_string(),
                name: "Qwen 2.5 Coder 1.5B Instruct".to_string(),
                category: "specialized".to_string(),
                category_label: "برمجة ونظم لينكس 💻".to_string(),
                size: "1.5B".to_string(),
                file_size: "986 MB".to_string(),
                quant: "Q4_K_M".to_string(),
                ram_required_gb: 1.6,
                recommended_threads: default_threads,
                download_url: "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf".to_string(),
                filename: "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf".to_string(),
                context_size: 4096,
                reasoning: "نموذج مخصص لكتابة ومراجعة أكواد البرمجة، سكربتات Bash، Rust، وبايثون.".to_string(),
                strengths: vec!["مبرمج لينكس وباش".to_string(), "خفيف 1.6GB".to_string(), "توليد أوامر طرفية".to_string()],
            },
            ModelSpec {
                id: "deepseek-r1-distill-qwen-1.5b-q4".to_string(),
                name: "DeepSeek R1 Distill Qwen 1.5B".to_string(),
                category: "specialized".to_string(),
                category_label: "تفكير واستدلال منطقي 🧩".to_string(),
                size: "1.5B".to_string(),
                file_size: "1.12 GB".to_string(),
                quant: "Q4_K_M".to_string(),
                ram_required_gb: 1.6,
                recommended_threads: default_threads,
                download_url: "https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf".to_string(),
                filename: "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf".to_string(),
                context_size: 4096,
                reasoning: "يستخدم التفكير المتسلسل (Chain-of-Thought) لتحليل وحل المشاكل المعقدة خطوة بخطوة.".to_string(),
                strengths: vec!["تفكير منطقي عميق".to_string(), "تحليل متسلسل".to_string(), "حجم صغير وسريع".to_string()],
            },
            ModelSpec {
                id: "phi-3.5-mini-3.8b-q4".to_string(),
                name: "Phi-3.5 Mini 3.8B Instruct".to_string(),
                category: "balanced".to_string(),
                category_label: "ذكاء متوازن وعالي 🧠".to_string(),
                size: "3.8B".to_string(),
                file_size: "2.39 GB".to_string(),
                quant: "Q4_K_M".to_string(),
                ram_required_gb: 3.6,
                recommended_threads: if is_server { server_threads } else { trial_threads.max(2) },
                download_url: "https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf".to_string(),
                filename: "Phi-3.5-mini-instruct-Q4_K_M.gguf".to_string(),
                context_size: 4096,
                reasoning: "نموذج مايكروسوفت القوي في الحسابات والمنطق العلمي والمعرفي.".to_string(),
                strengths: vec!["قوة مايكروسوفت الرياضية".to_string(), "جودة عالية لحجمه".to_string(), "سياق مرن".to_string()],
            },
            ModelSpec {
                id: "llama-3.1-8b-q4".to_string(),
                name: "Llama 3.1 8B Instruct".to_string(),
                category: "power".to_string(),
                category_label: "سيرفر قوي (High Power) 🔥".to_string(),
                size: "8.0B".to_string(),
                file_size: "4.92 GB".to_string(),
                quant: "Q4_K_M".to_string(),
                ram_required_gb: 6.5,
                recommended_threads: server_threads,
                download_url: "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf".to_string(),
                filename: "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf".to_string(),
                context_size: 8192,
                reasoning: "نموذج سيرفر متقدم للمهام المعقدة، يتطلب وضع السيرفر 100% أو رامات 16GB+.".to_string(),
                strengths: vec!["أقصى قدرة استيعابية".to_string(), "سياق ضخم 8192".to_string(), "استغلال كامل للعتاد".to_string()],
            },
        ];

        let recommended = if is_server {
            if total_ram >= 15.5 || (has_cuda && gpu_vram >= 7.5) {
                catalog.iter().find(|m| m.id == "llama-3.1-8b-q4").cloned().unwrap_or_else(|| catalog[2].clone())
            } else {
                catalog.iter().find(|m| m.id == "llama-3.2-3b-q4").cloned().unwrap_or_else(|| catalog[0].clone())
            }
        } else {
            if total_ram >= 15.5 {
                catalog.iter().find(|m| m.id == "llama-3.2-3b-q4").cloned().unwrap_or_else(|| catalog[0].clone())
            } else {
                catalog.iter().find(|m| m.id == "qwen-2.5-1.5b-q4").cloned().unwrap_or_else(|| catalog[0].clone())
            }
        };

        (recommended, catalog)
    }
}
