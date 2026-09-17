mod crm;
mod hardware;
mod llamacpp;
mod plugins;
mod server;

use clap::Parser;
use hardware::{SystemProfile, WorkloadMode};
use std::process::Command;

#[derive(Parser, Debug)]
#[command(
    author = "M.A.R.K.E.T. Core Team",
    version = "1.0.0",
    about = "M.A.R.K.E.T. - Modular AI Runtime & Knowledge Extension Toolkit for Enterprise Linux Deployments"
)]
struct Cli {
    /// Print hardware profile and recommended AI model
    #[arg(short, long)]
    profile: bool,

    /// Force dedicated 100% server workload profile
    #[arg(short = 's', long)]
    server_mode: bool,

    /// Automatically install llama.cpp and download recommended model
    #[arg(short, long)]
    install: bool,

    /// Run local web server and control dashboard
    #[arg(short = 'P', long, default_value_t = 8080)]
    port: u16,

    /// Test prompt directly from terminal
    #[arg(short, long)]
    chat: Option<String>,
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();
    let mode = if cli.server_mode {
        WorkloadMode::DedicatedServer
    } else {
        WorkloadMode::CasualTrial
    };

    let profile = SystemProfile::probe_with_mode(mode);

    if cli.profile {
        print_profile(&profile);
        return;
    }

    if cli.install {
        run_installer(&profile);
        return;
    }

    if let Some(msg) = cli.chat {
        println!("Testing prompt on M.A.R.K.E.T. engine: {}", msg);
        return;
    }

    print_profile(&profile);
    println!("\n🚀 بدء تشغيل محرك M.A.R.K.E.T. وواجهة المحولات مدمجة v1.0.0...");
    server::run_web_server(cli.port).await;
}

fn print_profile(p: &SystemProfile) {
    let mode_str = match p.active_mode {
        WorkloadMode::CasualTrial => "🟢 وضع التجربة الخفيفة (Casual Trial)",
        WorkloadMode::DedicatedServer => "🔥 وضع السيرفر المخصص 100% (Dedicated Server)",
    };

    println!("\n🐧 [M.A.R.K.E.T. AI Systems v1.0.0 - Modular Engine & Hardware Profiler]");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("📋  وضع التشغيل: {}", mode_str);
    println!("⚙️  المعالج: {} ({} أنوية)", p.cpu_model, p.cpu_cores);
    println!("🧠  الرامات: {} GB الكلية (المتاح: {} GB)", p.total_ram_gb, p.free_ram_gb);
    println!("⚡  دعم AVX2: {}", if p.has_avx2 { "نعم (أداء فائق ✅)" } else { "غير مدعوم" });
    if let Some(ref gpu) = p.gpu_name {
        println!("🎮  كارت الشاشة: {} (VRAM: {} GB)", gpu, p.gpu_vram_gb.unwrap_or(0.0));
    } else {
        println!("🎮  كارت الشاشة: غير متوفر (سيتم التشغيل على المعالج CPU)");
    }
    println!("─────────────────────────────────────────────────────");
    println!("🎯 الموديل الموصى به لهذا الوضع:");
    println!("   • الاسم: {}", p.recommended_model.name);
    println!("   • الحجم والضغط: {} ({})", p.recommended_model.size, p.recommended_model.quant);
    println!("   • استهلاك الرام المطلوب: {} GB", p.recommended_model.ram_required_gb);
    println!("   • خيوط المعالجة المثالية: {}", p.recommended_model.recommended_threads);
    println!("   • سبب الاختيار: {}", p.recommended_model.reasoning);
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
}

fn run_installer(p: &SystemProfile) {
    println!("\n📦 [تثبيت llama.cpp التلقائي لنظام لينكس - M.A.R.K.E.T. Engine]");
    let script = format!(
        "mkdir -p ~/omnicontext_ai/models && cd ~/omnicontext_ai && \
        if [ ! -d 'llama.cpp' ]; then git clone https://github.com/ggerganov/llama.cpp.git; fi && \
        cd llama.cpp && cmake -B build -DGGML_AVX2=ON -DGGML_NATIVE=ON && cmake --build build --config Release -j{} && \
        cd ~/omnicontext_ai/models && \
        if [ ! -f '{}' ]; then curl -L '{}' -o '{}'; fi",
        p.recommended_model.recommended_threads,
        p.recommended_model.filename,
        p.recommended_model.download_url,
        p.recommended_model.filename
    );

    println!("جاري تنفيذ أوامر البناء والتحميل...");
    let status = Command::new("sh").arg("-c").arg(&script).status();
    match status {
        Ok(s) if s.success() => println!("✅ تم التثبيت بنجاح!"),
        _ => println!("⚠️ يرجى التأكد من توفر git و cmake على جهازك."),
    }
}
