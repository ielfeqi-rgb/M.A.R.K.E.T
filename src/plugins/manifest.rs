use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum PluginType {
    Channel,   // Messaging channel adapters (Instagram, Messenger, Telegram, Webhook)
    Domain,    // Business domain adapters (Fashion, Real Estate, Inventory)
    Processor, // Text transformers and context processors
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginManifest {
    pub id: String,
    pub name: String,
    pub version: String,
    pub plugin_type: PluginType,
    pub description: String,
    pub entrypoint: String,
    #[serde(default = "default_true")]
    pub enabled: bool,
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginInput {
    pub user_message: String,
    #[serde(default)]
    pub metadata: serde_json::Value,
    #[serde(default)]
    pub db_context: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginOutput {
    #[serde(default = "default_success")]
    pub status: String,
    #[serde(default)]
    pub plugin: String,
    #[serde(default)]
    pub injected_context: String,
    #[serde(default)]
    pub system_instruction_override: Option<String>,
    #[serde(default)]
    pub outbound_meta: Option<serde_json::Value>,
}

fn default_success() -> String {
    "success".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineResult {
    pub original_message: String,
    pub enriched_system_instruction: String,
    pub merged_injected_context: String,
    pub active_plugins: Vec<String>,
    pub llm_response: Option<String>,
    pub outbound_payload: Option<serde_json::Value>,
}
