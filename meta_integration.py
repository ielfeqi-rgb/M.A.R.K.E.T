"""
M.A.R.K.E.T AI - Meta Integration Hub (Facebook Webhooks & Graph API Client)
Enables bi-directional Meta platform capabilities:
1. Inbound Webhooks: Real-time listener for comments, Messenger messages, leads, and post reactions.
2. Outbound Graph API: Publishing feed posts, auto-replying to comments, and direct Messenger replies.
Includes sandbox simulation fallback for IT testing.
"""

import json
import time
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class MetaIntegrationManager:
    """Enterprise Meta/Facebook Gateway Manager."""

    def __init__(self):
        pass

    def verify_webhook_handshake(
        self,
        hub_mode: Optional[str],
        hub_verify_token: Optional[str],
        hub_challenge: Optional[str],
        expected_verify_token: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates Meta's webhook subscription challenge.
        Meta sends GET with: hub.mode=subscribe & hub.verify_token=YOUR_TOKEN & hub.challenge=CHALLENGE
        """
        if hub_mode == "subscribe" and hub_verify_token == expected_verify_token:
            logger.info("Facebook Webhook verification challenge passed successfully.")
            return True, hub_challenge
        logger.warning(f"Facebook Webhook verification failed. Received token: {hub_verify_token}")
        return False, None

    def publish_page_post(
        self,
        page_id: str,
        access_token: str,
        message: str,
        link: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publishes a new feed post to the Facebook Page via Meta Graph API.
        Endpoint: POST /{PAGE_ID}/feed or /{PAGE_ID}/photos
        """
        clean_page_id = page_id.strip() if page_id else ""
        clean_token = access_token.strip() if access_token else ""

        # Sandbox / Dry-Run mode if credentials are mock/empty
        if not clean_page_id or not clean_token or clean_token.startswith("mock_") or clean_token == "EAAB...":
            logger.info(f"[Meta Sandbox] Simulated Page Post to '{clean_page_id or 'Demo Page'}': {message[:60]}...")
            return {
                "success": True,
                "sandbox": True,
                "post_id": f"mock_post_{int(time.time())}",
                "message": "تم نشر البوست بنجاح في بيئة المحاكاة التجريبية (Sandbox Mode).",
                "details": {
                    "page_id": clean_page_id or "Demo Page",
                    "text": message,
                    "link": link,
                    "image_url": image_url
                }
            }

        try:
            url = f"{GRAPH_API_BASE}/{clean_page_id}/feed"
            payload = {
                "message": message,
                "access_token": clean_token
            }
            if link:
                payload["link"] = link

            data = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            
            with urllib.request.urlopen(req, timeout=15) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                post_id = res_json.get("id")
                logger.info(f"Published Facebook Post to Page {clean_page_id}: Post ID {post_id}")
                return {
                    "success": True,
                    "sandbox": False,
                    "post_id": post_id,
                    "message": "تم نشر البوست بنجاح على صفحة الفيسبوك الرسمية!"
                }
        except urllib.error.HTTPError as he:
            err_text = he.read().decode("utf-8")
            logger.error(f"Graph API HTTP Error: {he.code} - {err_text}")
            return {
                "success": False,
                "sandbox": False,
                "error": f"Graph API Error ({he.code}): {err_text}"
            }
        except Exception as e:
            logger.error(f"Error publishing Facebook post: {e}")
            return {
                "success": False,
                "sandbox": False,
                "error": str(e)
            }

    def reply_to_comment(
        self,
        comment_id: str,
        access_token: str,
        message: str
    ) -> Dict[str, Any]:
        """Replies directly to a customer's comment on a post."""
        clean_comment_id = comment_id.strip() if comment_id else ""
        clean_token = access_token.strip() if access_token else ""

        if not clean_comment_id or not clean_token or clean_token.startswith("mock_"):
            return {
                "success": True,
                "sandbox": True,
                "reply_id": f"mock_comment_reply_{comment_id}",
                "message": "تم إرسال الرد على التعليق في وضع المحاكاة بنجاح."
            }

        try:
            url = f"{GRAPH_API_BASE}/{clean_comment_id}/comments"
            payload = {
                "message": message,
                "access_token": clean_token
            }
            data = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=15) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                return {
                    "success": True,
                    "sandbox": False,
                    "reply_id": res_json.get("id"),
                    "message": "تم نشر الرد على التعليق بنجاح!"
                }
        except Exception as e:
            return {"success": False, "sandbox": False, "error": str(e)}

    def parse_webhook_event(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses incoming Meta Webhook JSON payloads (Feed changes or Messenger messages).
        """
        object_type = body.get("object", "")
        entries = body.get("entry", [])

        events = []
        for entry in entries:
            messaging_list = entry.get("messaging", [])
            for msg_item in messaging_list:
                sender_id = msg_item.get("sender", {}).get("id", "")
                text = msg_item.get("message", {}).get("text", "")
                if text:
                    events.append({
                        "type": "messenger_message",
                        "sender_id": sender_id,
                        "text": text,
                        "timestamp": msg_item.get("timestamp")
                    })

            changes_list = entry.get("changes", [])
            for ch in changes_list:
                val = ch.get("value", {})
                item_type = val.get("item", "")
                verb = val.get("verb", "")
                
                if item_type == "comment" and verb == "add":
                    events.append({
                        "type": "feed_comment",
                        "comment_id": val.get("comment_id"),
                        "post_id": val.get("post_id"),
                        "sender_id": val.get("from", {}).get("id"),
                        "sender_name": val.get("from", {}).get("name", "عميل"),
                        "text": val.get("message", ""),
                        "created_time": val.get("created_time")
                    })

        return {
            "object": object_type,
            "events_count": len(events),
            "events": events
        }


# Global singleton
meta_hub = MetaIntegrationManager()
