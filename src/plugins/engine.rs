use super::manifest::{PipelineResult, PluginInput, PluginManifest, PluginOutput};
use mlua::{Lua, LuaSerdeExt};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use tracing::{error, info};

#[derive(Debug, Clone)]
pub struct PluginEntry {
    pub manifest: PluginManifest,
    pub path: PathBuf,
}

pub struct PluginEngine {
    plugins_dir: PathBuf,
    loaded_plugins: Vec<PluginEntry>,
}

impl PluginEngine {
    pub fn new<P: AsRef<Path>>(dir: P) -> Self {
        let plugins_dir = dir.as_ref().to_path_buf();
        let mut engine = Self {
            plugins_dir,
            loaded_plugins: Vec::new(),
        };
        engine.reload();
        engine
    }

    pub fn reload(&mut self) {
        self.loaded_plugins.clear();
        if !self.plugins_dir.exists() {
            let _ = fs::create_dir_all(&self.plugins_dir);
            info!("أنشئ مجلد الإضافات: {:?}", self.plugins_dir);
            return;
        }

        if let Ok(entries) = fs::read_dir(&self.plugins_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    let manifest_path = path.join("plugin.json");
                    if manifest_path.exists() {
                        if let Ok(content) = fs::read_to_string(&manifest_path) {
                            match serde_json::from_str::<PluginManifest>(&content) {
                                Ok(manifest) => {
                                    info!("تم اكتشاف إضافة: {} ({})", manifest.name, manifest.id);
                                    self.loaded_plugins.push(PluginEntry { manifest, path });
                                }
                                Err(e) => {
                                    error!("فشل في تحليل ملف تعريف الإضافة {:?}: {}", manifest_path, e);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    pub fn list_plugins(&self) -> Vec<PluginManifest> {
        self.loaded_plugins.iter().map(|p| p.manifest.clone()).collect()
    }

    pub fn toggle_plugin(&mut self, plugin_id: &str, enable: bool) -> Result<bool, String> {
        for entry in &mut self.loaded_plugins {
            if entry.manifest.id == plugin_id {
                entry.manifest.enabled = enable;
                let manifest_path = entry.path.join("plugin.json");
                if let Ok(json_str) = serde_json::to_string_pretty(&entry.manifest) {
                    let _ = fs::write(manifest_path, json_str);
                }
                return Ok(enable);
            }
        }
        Err(format!("الإضافة غير موجودة: {}", plugin_id))
    }

    pub fn execute_plugin(&self, plugin_id: &str, input: &PluginInput) -> Result<PluginOutput, String> {
        let entry = self
            .loaded_plugins
            .iter()
            .find(|p| p.manifest.id == plugin_id)
            .ok_or_else(|| format!("الإضافة غير موجودة: {}", plugin_id))?;

        if !entry.manifest.enabled {
            return Err(format!("الإضافة {} معطلة حالياً", plugin_id));
        }

        let script_path = entry.path.join(&entry.manifest.entrypoint);
        if !script_path.exists() {
            return Err(format!("ملف التشغيل غير موجود: {:?}", script_path));
        }

        let ext = script_path
            .extension()
            .and_then(|s| s.to_str())
            .unwrap_or("");

        match ext {
            "lua" => self.run_lua_script(&script_path, input),
            "py" => self.run_python_script(&script_path, input),
            _ => Err(format!("نوع الملف غير مدعوم: {}", ext)),
        }
    }

    fn run_lua_script(&self, script_path: &Path, input: &PluginInput) -> Result<PluginOutput, String> {
        let lua_code = fs::read_to_string(script_path)
            .map_err(|e| format!("فشل في قراءة ملف Lua: {}", e))?;

        let lua = Lua::new();
        let globals = lua.globals();

        lua.load(&lua_code)
            .exec()
            .map_err(|e| format!("خطأ في تنفيذ كود Lua: {}", e))?;

        let process_fn: mlua::Function = globals
            .get("process")
            .map_err(|_| "الدالة 'process(input)' غير معرفة داخل ملف Lua".to_string())?;

        let lua_input = lua
            .to_value(input)
            .map_err(|e| format!("فشل تحويل البيانات لـ Lua: {}", e))?;

        let lua_output: mlua::Value = process_fn
            .call(lua_input)
            .map_err(|e| format!("خطأ أثناء استدعاء process() في Lua: {}", e))?;

        let output: PluginOutput = lua
            .from_value(lua_output)
            .map_err(|e| format!("فشل تحويل مخرجات Lua إلى PluginOutput: {}", e))?;

        Ok(output)
    }

    fn run_python_script(&self, script_path: &Path, input: &PluginInput) -> Result<PluginOutput, String> {
        let json_input = serde_json::to_string(input).map_err(|e| e.to_string())?;

        let python_cmd = format!(
            "import sys, json, importlib.util; \
             spec = importlib.util.spec_from_file_location('mod', r'{}'); \
             mod = importlib.util.module_from_spec(spec); \
             spec.loader.exec_module(mod); \
             data = json.loads(sys.stdin.read()); \
             res = mod.process(data); \
             print(json.dumps(res))",
            script_path.to_string_lossy()
        );

        use std::io::Write;
        let mut child = Command::new("python3")
            .arg("-c")
            .arg(&python_cmd)
            .stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .spawn()
            .map_err(|e| format!("فشل إطلاق بيئة Python: {}", e))?;

        if let Some(mut stdin) = child.stdin.take() {
            let _ = stdin.write_all(json_input.as_bytes());
        }

        let output = child
            .wait_with_output()
            .map_err(|e| format!("خطأ في تنفيذ سكربت بايثون: {}", e))?;

        if !output.status.success() {
            let err_str = String::from_utf8_lossy(&output.stderr);
            return Err(format!("خطأ مخرجات بايثون: {}", err_str));
        }

        let stdout_str = String::from_utf8_lossy(&output.stdout);
        let plugin_out: PluginOutput = serde_json::from_str(&stdout_str)
            .map_err(|e| format!("فشل تحويل مخرجات Python إلى PluginOutput: {} (المخرجات: {})", e, stdout_str))?;

        Ok(plugin_out)
    }

    pub fn run_pipeline(
        &self,
        user_message: &str,
        channel_plugin_id: Option<&str>,
        domain_plugin_id: Option<&str>,
        base_system_instruction: &str,
        metadata: serde_json::Value,
    ) -> PipelineResult {
        let mut active_plugins = Vec::new();
        let mut merged_context = String::new();
        let mut final_system_instruction = base_system_instruction.to_string();
        let mut outbound_payload = None;

        let input = PluginInput {
            user_message: user_message.to_string(),
            metadata,
            db_context: String::new(),
        };

        if let Some(id) = domain_plugin_id {
            if let Ok(out) = self.execute_plugin(id, &input) {
                active_plugins.push(id.to_string());
                if !out.injected_context.is_empty() {
                    merged_context.push_str(&out.injected_context);
                    merged_context.push('\n');
                }
                if let Some(override_sys) = out.system_instruction_override {
                    final_system_instruction = override_sys;
                }
            }
        }

        if let Some(id) = channel_plugin_id {
            if let Ok(out) = self.execute_plugin(id, &input) {
                active_plugins.push(id.to_string());
                if !out.injected_context.is_empty() {
                    merged_context.push_str(&out.injected_context);
                    merged_context.push('\n');
                }
                if let Some(override_sys) = out.system_instruction_override {
                    final_system_instruction = override_sys;
                }
                if let Some(outbound) = out.outbound_meta {
                    outbound_payload = Some(outbound);
                }
            }
        }

        PipelineResult {
            original_message: user_message.to_string(),
            enriched_system_instruction: final_system_instruction,
            merged_injected_context: merged_context,
            active_plugins,
            llm_response: None,
            outbound_payload,
        }
    }
}
