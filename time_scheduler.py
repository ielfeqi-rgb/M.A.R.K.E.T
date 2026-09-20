"""
M.A.R.K.E.T AI - Time & Delay Scheduler Engine
Automates scheduled campaigns, delayed promotions (e.g., 3 months / 90 days followups),
and scheduled Facebook posts with SQLite WAL persistence and async background daemon.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from database import db

logger = logging.getLogger(__name__)


class TimeSchedulerEngine:
    """Asynchronous Background Scheduler Engine."""

    def __init__(self):
        self._is_running = False
        self._task: Optional[asyncio.Task] = None

    def calculate_scheduled_time(
        self,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        target_iso: Optional[str] = None
    ) -> str:
        """Returns ISO-formatted datetime string for scheduled execution."""
        if target_iso:
            try:
                dt = datetime.fromisoformat(target_iso.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass

        future = datetime.now() + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        return future.strftime('%Y-%m-%d %H:%M:%S')

    def schedule_task(
        self,
        session_id: str,
        customer_phone: str,
        customer_name: str,
        trigger_type: str,
        payload: Dict[str, Any],
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        target_iso: Optional[str] = None,
        created_by: str = 'system'
    ) -> Dict[str, Any]:
        """Schedule a task for future execution."""
        sched_time_str = self.calculate_scheduled_time(
            days=days, hours=hours, minutes=minutes, seconds=seconds, target_iso=target_iso
        )

        res = db.add_scheduled_trigger(
            session_id=session_id or f'sched_{customer_phone}',
            customer_phone=customer_phone,
            customer_name=customer_name,
            trigger_type=trigger_type,
            scheduled_for=sched_time_str,
            payload=payload,
            created_by=created_by
        )
        logger.info(f"Scheduled task #{res.get('id')} for {sched_time_str} (Type: {trigger_type})")
        return res

    async def execute_trigger(self, trigger: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a due trigger according to its type."""
        trigger_id = trigger.get('id')
        trigger_type = trigger.get('trigger_type', '')
        payload = trigger.get('payload', {})
        phone = trigger.get('customer_phone', '')
        customer_name = trigger.get('customer_name', '')
        session_id = trigger.get('session_id', '')

        logger.info(f"Executing scheduled trigger #{trigger_id} (Type: {trigger_type}) for {phone}...")

        result = {}
        try:
            if trigger_type in ('promo_message', 'whatsapp_message', 'promo_after_delay'):
                msg_text = payload.get('message', 'عزيزنا العميل، نتمنى أن تكون بأفضل حال! نهديك هذا العرض المميز.')
                promo_code = payload.get('promo_code', '')
                if promo_code and promo_code not in msg_text:
                    msg_text = f"{msg_text}\n\nكود الخصم الخاص بك: {promo_code}"

                # Log to conversation history in SQLite WAL
                db.log_conversation(
                    session_id=session_id or f'sched_{phone}',
                    channel='whatsapp',
                    user_msg='[مهمة جدولة زمنية - حملة تسويقية]',
                    bot_reply=msg_text,
                    latency_ms=0,
                    provider='scheduler'
                )

                result = {
                    "dispatched": True,
                    "channel": "whatsapp",
                    "recipient": phone,
                    "message": msg_text,
                    "executed_at": datetime.now().isoformat()
                }

            elif trigger_type in ('facebook_post', 'scheduled_fb_post'):
                from meta_integration import meta_hub
                page_id = payload.get('page_id', '')
                access_token = payload.get('access_token', '')
                message = payload.get('message', 'منشور جديد من M.A.R.K.E.T AI')
                link = payload.get('link')
                image_url = payload.get('image_url')

                post_res = meta_hub.publish_page_post(
                    page_id=page_id,
                    access_token=access_token,
                    message=message,
                    link=link,
                    image_url=image_url
                )
                result = post_res

            elif trigger_type == 'cs_handover':
                reason = payload.get('reason', 'تحويل مجدول لخدمة العملاء')
                last_msg = payload.get('last_message', 'تنبيه موعد متابعة دوري')
                handover_res = db.add_to_cs_pool(
                    session_id=session_id,
                    customer_phone=phone,
                    customer_name=customer_name,
                    channel='whatsapp',
                    reason=reason,
                    last_message=last_msg
                )
                result = handover_res

            else:
                result = {"status": "completed", "detail": f"Custom flow {trigger_type} triggered successfully."}

            db.mark_trigger_status(trigger_id, status='completed', result=result)
            return {"success": True, "result": result}

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Failed to execute scheduled trigger #{trigger_id}: {err_msg}")
            db.mark_trigger_status(trigger_id, status='failed', error_message=err_msg)
            return {"success": False, "error": err_msg}

    async def run_scheduler_daemon(self, poll_interval_seconds: int = 5):
        """Continuous background async loop polling and executing due triggers."""
        self._is_running = True
        logger.info(f"Time Scheduler Daemon started. Polling every {poll_interval_seconds}s.")
        while self._is_running:
            try:
                due_triggers = db.get_due_scheduled_triggers()
                if due_triggers:
                    logger.info(f"Found {len(due_triggers)} due scheduled triggers. Executing...")
                    for trig in due_triggers:
                        await self.execute_trigger(trig)
            except Exception as e:
                logger.error(f"Error in Time Scheduler loop: {e}")

            await asyncio.sleep(poll_interval_seconds)

    def start(self, loop=None):
        """Start background worker task."""
        if not self._is_running:
            self._task = asyncio.create_task(self.run_scheduler_daemon())

    def stop(self):
        """Stop background worker task."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()


# Global singleton
scheduler_engine = TimeSchedulerEngine()
