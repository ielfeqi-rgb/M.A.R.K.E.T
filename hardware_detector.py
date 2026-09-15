import os
import sys
import platform
from typing import Dict, Any, List


def get_system_hardware() -> Dict[str, Any]:
    """
    Detects system RAM, CPU cores, architecture, and platform specs.
    Works across standard Linux, Tiny Core Linux, Windows, and macOS without extra heavy dependencies.
    """
    # 1. Total & Available Memory (RAM) in MB
    ram_total_mb = 0
    ram_available_mb = 0

    if os.path.exists("/proc/meminfo"):
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val_str = parts[1].strip().split()[0]
                        if key == "MemTotal":
                            ram_total_mb = int(int(val_str) / 1024)
                        elif key in ("MemAvailable", "MemFree"):
                            if ram_available_mb == 0:
                                ram_available_mb = int(int(val_str) / 1024)
        except Exception:
            pass

    if ram_total_mb == 0:
        # Fallback for Windows / macOS or systems without /proc/meminfo
        try:
            import psutil
            mem = psutil.virtual_memory()
            ram_total_mb = int(mem.total / (1024 * 1024))
            ram_available_mb = int(mem.available / (1024 * 1024))
        except Exception:
            # Safe minimum default estimation if detection fails
            ram_total_mb = 2048
            ram_available_mb = 1024

    # 2. CPU Cores & Arch
    cpu_cores = os.cpu_count() or 1
    arch = platform.machine() or "x86_64"
    system_os = platform.system()

    # 3. Assess Hardware Tier
    # Tier 1: Micro / Very Low (< 3.5 GB RAM) -> Lightweight local models or Cloud API recommended
    # Tier 2: Low-Medium (3.5 GB - 7 GB RAM) -> 1B - 3B local models
    # Tier 3: Medium-High (7 GB - 15 GB RAM) -> 7B - 8B local models
    # Tier 4: High (>= 15 GB RAM) -> 8B - 14B+ models
    if ram_total_mb < 3500:
        tier = "low"
        tier_label = "جهاز خفيف / موارد محدودة (ينصح بالـ API السحابي أو موديلات 0.5B-1B)"
        tier_color = "warning"
    elif ram_total_mb < 7500:
        tier = "medium"
        tier_label = "جهاز متوسط (مناسب لموديلات 1B إلى 3B)"
        tier_color = "blue"
    elif ram_total_mb < 15500:
        tier = "high"
        tier_label = "جهاز قوي (مناسب لموديلات 3B إلى 8B)"
        tier_color = "purple"
    else:
        tier = "ultra"
        tier_label = "جهاز فائق القوة (يدعم معظم الموديلات المحلية 8B+)"
        tier_color = "success"

    # 4. Filter Recommended Local Models based on RAM
    all_known_models = [
        {
            "name": "qwen2.5:0.5b",
            "displayName": "Qwen 2.5 (0.5B) - فائق الخفة والسرعة",
            "size_gb": 0.4,
            "min_ram_mb": 1500,
            "description": "ممتاز جداً للأجهزة الضعيفة وخوادم Tiny Core و VPS الصغير.",
            "recommended": True
        },
        {
            "name": "llama3.2:1b",
            "displayName": "Llama 3.2 (1B) - خفيف ودقيق",
            "size_gb": 1.3,
            "min_ram_mb": 2500,
            "description": "سريع جداً واستجابة ممتازة مع استهلاك قليل للذاكرة.",
            "recommended": ram_total_mb >= 2500
        },
        {
            "name": "qwen2.5:1.5b",
            "displayName": "Qwen 2.5 (1.5B) - متوازن جداً باللغة العربية",
            "size_gb": 1.0,
            "min_ram_mb": 2800,
            "description": "فهم رائع للهجات واستخراج أكواد المنتجات بدقة.",
            "recommended": ram_total_mb >= 2800
        },
        {
            "name": "llama3.2:3b",
            "displayName": "Llama 3.2 (3B) - الموديل القياسي الموصى به",
            "size_gb": 2.0,
            "min_ram_mb": 4000,
            "description": "توازن مثالي بين الذكاء وسرعة الرد في خدمة العملاء.",
            "recommended": ram_total_mb >= 4000
        },
        {
            "name": "qwen2.5:3b",
            "displayName": "Qwen 2.5 (3B) - ممتاز بالعربية",
            "size_gb": 1.9,
            "min_ram_mb": 4000,
            "description": "قوي جداً في المحادثات الودية والعامية.",
            "recommended": ram_total_mb >= 4000
        },
        {
            "name": "mistral:7b",
            "displayName": "Mistral (7B) - موديل ذكي وكبير",
            "size_gb": 4.1,
            "min_ram_mb": 8000,
            "description": "يحتاج لجهاز ذو رام 8GB فما فوق لأداء سلس.",
            "recommended": ram_total_mb >= 8000
        },
        {
            "name": "llama3.1:8b",
            "displayName": "Llama 3.1 (8B) - ذكاء متقدم",
            "size_gb": 4.7,
            "min_ram_mb": 9000,
            "description": "يحتاج جهاز قوي بذاكرة 8GB - 16GB.",
            "recommended": ram_total_mb >= 9000
        }
    ]

    # Models compatible with this machine (won't crash the server)
    compatible_models = [
        m for m in all_known_models
        if ram_total_mb >= m["min_ram_mb"]
    ]

    # If RAM is very small, always keep at least the smallest model
    if not compatible_models:
        compatible_models = [all_known_models[0]]

    return {
        "ram_total_mb": ram_total_mb,
        "ram_total_gb": round(ram_total_mb / 1024, 1),
        "ram_available_mb": ram_available_mb,
        "ram_available_gb": round(ram_available_mb / 1024, 1),
        "cpu_cores": cpu_cores,
        "arch": arch,
        "os": system_os,
        "tier": tier,
        "tier_label": tier_label,
        "tier_color": tier_color,
        "recommended_cloud": ram_total_mb < 4000,
        "compatible_models": compatible_models
    }
