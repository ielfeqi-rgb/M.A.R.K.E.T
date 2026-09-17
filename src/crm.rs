use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use tracing::info;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LeadRecord {
    pub id: String,
    pub timestamp: String,
    pub channel: String,
    pub customer_id: String,
    pub customer_name: String,
    pub phone: Option<String>,
    pub intent: String,
    pub product_code: Option<String>,
    pub summary: String,
    pub reply_sent: String,
    pub status: String,
}

pub struct CrmManager {
    db_path: PathBuf,
    leads: Vec<LeadRecord>,
}

impl CrmManager {
    pub fn new() -> Self {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let db_dir = PathBuf::from(home).join("omnicontext_ai").join("db");
        let _ = fs::create_dir_all(&db_dir);
        let db_path = db_dir.join("leads.json");

        let leads = if db_path.exists() {
            fs::read_to_string(&db_path)
                .ok()
                .and_then(|content| serde_json::from_str::<Vec<LeadRecord>>(&content).ok())
                .unwrap_or_default()
        } else {
            Vec::new()
        };

        Self { db_path, leads }
    }

    pub fn save(&self) -> Result<(), String> {
        let json_str = serde_json::to_string_pretty(&self.leads)
            .map_err(|e| format!("فشل تحويل البيانات لـ JSON: {}", e))?;
        fs::write(&self.db_path, json_str)
            .map_err(|e| format!("فشل كتابة ملف CRM: {}", e))?;
        Ok(())
    }

    pub fn add_lead(&mut self, record: LeadRecord) -> Result<(), String> {
        info!("تسجيل عميل جديد في CRM: [{}] {}", record.channel, record.customer_name);
        self.leads.insert(0, record);
        self.save()
    }

    pub fn list_leads(&self) -> Vec<LeadRecord> {
        self.leads.clone()
    }

    pub fn update_status(&mut self, id: &str, new_status: &str) -> Result<bool, String> {
        if let Some(lead) = self.leads.iter_mut().find(|l| l.id == id) {
            lead.status = new_status.to_string();
            self.save()?;
            Ok(true)
        } else {
            Ok(false)
        }
    }

    pub fn export_csv(&self) -> String {
        let mut csv = String::from("ID,Timestamp,Channel,Customer ID,Customer Name,Phone,Intent,Product Code,Summary,Status\n");
        for l in &self.leads {
            let line = format!(
                "\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\"\n",
                l.id.replace('"', "\"\""),
                l.timestamp.replace('"', "\"\""),
                l.channel.replace('"', "\"\""),
                l.customer_id.replace('"', "\"\""),
                l.customer_name.replace('"', "\"\""),
                l.phone.as_deref().unwrap_or("").replace('"', "\"\""),
                l.intent.replace('"', "\"\""),
                l.product_code.as_deref().unwrap_or("").replace('"', "\"\""),
                l.summary.replace('\n', " ").replace('"', "\"\""),
                l.status.replace('"', "\"\"")
            );
            csv.push_str(&line);
        }
        csv
    }
}
