pub mod engine;
pub mod manifest;

pub use engine::PluginEngine;
pub use manifest::{PipelineResult, PluginInput, PluginManifest, PluginOutput, PluginType};
