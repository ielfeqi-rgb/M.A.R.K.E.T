import json
import logging
import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator
import httpx

from http_client import AsyncHTTPClient

logger = logging.getLogger(__name__)

# Concurrency & Backpressure Guard: Limits simultaneous local model inference
# Prevents Linux OOM Killer and CPU thread starvation on edge devices
_INFERENCE_SEMAPHORE = asyncio.Semaphore(2)


class AIProviderManager:
    """
    Robust AI Provider Manager with Automatic Fallback Chain:
    Tries Selected Provider -> Gemini API -> Groq API -> Ollama Local -> Rule-Based Fallback.
    Never crashes even if network, Ollama, or API key fails!
    """

    @staticmethod
    async def _get_client() -> httpx.AsyncClient:
        try:
            http = await AsyncHTTPClient.get_instance()
            return http.general
        except Exception:
            return httpx.AsyncClient(timeout=30.0)

    @staticmethod
    async def get_ollama_models(ollama_url: str = "http://localhost:11434") -> List[Dict[str, Any]]:
        """Fetch list of locally installed models from Ollama."""
        try:
            client = await AIProviderManager._get_client()
            resp = await client.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=3.0)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [
                    {
                        "name": m.get("name"),
                        "size": m.get("size"),
                        "digest": m.get("digest")[:12] if m.get("digest") else "",
                        "modified_at": m.get("modified_at")
                    }
                    for m in models
                ]
        except Exception:
            pass
        return []

    @staticmethod
    async def pull_ollama_model(model_name: str, ollama_url: str = "http://localhost:11434") -> AsyncGenerator[Dict[str, Any], None]:
        """Stream progress of pulling an Ollama model."""
        url = f"{ollama_url.rstrip('/')}/api/pull"
        payload = {"name": model_name, "stream": True}

        try:
            async with httpx.AsyncClient(timeout=None) as stream_client:
                async with stream_client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        yield {"status": f"HTTP Error {response.status_code}", "error": True}
                        return

                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                yield data
                            except Exception:
                                pass
        except Exception as e:
            yield {"status": f"Connection Error: {str(e)}", "error": True}

    @staticmethod
    async def generate_code_inference(user_text: str, config: Dict[str, Any]) -> Optional[str]:
        """
        Uses LLM with Rule-Based Fallback to infer product code from text prompt.
        """
        prompt = (
            "أنت نظام ذكي يقوم بتحويل استفسار العميل عن الملابس إلى كود منتج رمزي محدد.\n"
            "قواعد تكوين الكود:\n"
            "- يبدأ بحرف للمنتج (تيشرت: t، سويت شيرت: sw، بنطلون: p، شورت: sh، جاكيت: j).\n"
            "- يليه المقاس بالإنجليزية حروف صغيرة (s, m, l, xl, xxl, xxxl).\n"
            "- ينتهي بحرف اللون بالإنجليزية (أحمر: r، أسود: b، أزرق: l، رمادي: g، أبيض: w، كحلي: n، زيتي: o).\n"
            "مثال: 'تيشرت أحمر xxl' -> txxlr\n"
            "مثال: 'سويت شيرت أسود m' -> swmb\n\n"
            f"طلب العميل: \"{user_text}\"\n"
            "أجب بالكود فقط دون أي كلمات أخرى أو علامات ترقيم على الإطلاق وبأحرف صغيرة:"
        )

        res = await AIProviderManager.complete_text(
            prompt=prompt,
            config=config,
            temperature=0.0
        )
        if res:
            clean_code = "".join(c for c in res.strip().lower() if c.isalnum())
            if clean_code:
                return clean_code

        # Rule-based fallback if AI is unreachable/failed
        return AIProviderManager._rule_based_code_inference(user_text)

    @staticmethod
    def _rule_based_code_inference(text: str) -> Optional[str]:
        """Fallback Regex/Keyword matcher when AI providers fail or offline."""
        t = text.lower().strip()
        prod = ""
        if "تيشرت" in t or "تيشيرت" in t:
            prod = "t"
        elif "سويت شيرت" in t or "سويتشرت" in t or "سويت" in t:
            prod = "sw"
        elif "بنطلون" in t or "بناطيل" in t:
            prod = "p"
        elif "شورت" in t:
            prod = "sh"
        elif "جاكيت" in t:
            prod = "j"

        if not prod:
            return None

        # Size
        size = ""
        if "xxxl" in t or "3xl" in t:
            size = "xxxl"
        elif "xxl" in t or "2xl" in t:
            size = "xxl"
        elif "xl" in t:
            size = "xl"
        elif " m " in f" {t} " or "وسط" in t or "ميديم" in t:
            size = "m"
        elif " l " in f" {t} " or "لارج" in t:
            size = "l"
        elif " s " in f" {t} " or "سمول" in t:
            size = "s"

        # Color
        color = ""
        if "أحمر" in t or "احمر" in t:
            color = "r"
        elif "أسود" in t or "اسود" in t:
            color = "b"
        elif "أزرق" in t or "ازرق" in t:
            color = "l"
        elif "رمادي" in t or "رصاصي" in t:
            color = "g"
        elif "أبيض" in t or "ابيض" in t:
            color = "w"
        elif "كحلي" in t:
            color = "n"
        elif "زيتي" in t:
            color = "o"

        if prod and size and color:
            return f"{prod}{size}{color}"
        elif prod and size:
            return f"{prod}{size}"
        elif prod:
            return prod
        return None

    @staticmethod
    async def complete_chat(messages: List[Dict[str, str]], config: Dict[str, Any], temperature: float = 0.7) -> Optional[str]:
        """
        Unified chat completion with AUTOMATIC FALLBACK CHAIN (Priority Order):
        1. Selected Provider (User choice tried FIRST, defaults to omni_engine / custom)
        2. Configured Omni Engine / Custom Endpoint (local or remote host via custom_ai_url)
        3. Active llama-server process (if running locally on port 8081)
        4. Cloud & Local Providers (Gemini, Groq, Ollama, OpenAI, DeepSeek)
        5. Returns None → caller handles rule-based fallback
        """
        selected_provider = config.get("ai_provider", "custom").lower()

        # Build priority chain
        chain: List[str] = []

        # 1. User's selected provider comes FIRST!
        chain.append(selected_provider)

        # 2. If omni_engine / custom is configured (local or remote server), prioritize it
        if config.get("custom_ai_url", "").strip() and "custom" not in chain:
            chain.append("custom")

        # 3. Auto-detect & auto-start llama-server locally on port 8081 if stopped
        try:
            from llamacpp_manager import llama_manager
            llama_status = llama_manager.get_status()
            if not llama_status.get("running"):
                avail = llama_status.get("available_gguf_models", [])
                if avail:
                    first_model = avail[0]["filename"]
                    logger.info(f"[AI Chain] Auto-starting local llama-server for model: {first_model}")
                    llama_manager.start(first_model, threads=4, context_size=2048, port=8081)
                    await asyncio.sleep(2.5)
                    llama_status = llama_manager.get_status()

            if llama_status.get("running") and "llamacpp" not in chain:
                chain.append("llamacpp")
        except Exception as e:
            logger.debug(f"[AI Chain] Local llama-server auto-start check: {e}")
            llama_status = {}

        # 4. Add remaining configured providers
        for p in ["custom", "gemini", "groq", "ollama", "openai", "deepseek"]:
            if p not in chain:
                chain.append(p)

        last_error = None
        for provider in chain:
            try:
                res = None
                if provider == "llamacpp":
                    port = llama_status.get("port", 8081)
                    model = llama_status.get("running_model", "local-model")
                    res = await AIProviderManager._chat_openai_compatible_provider(
                        messages,
                        {"custom_ai_url": f"http://localhost:{port}/v1", "custom_ai_key": "none", "custom_ai_model": model},
                        "custom",
                        temperature
                    )
                elif provider == "ollama":
                    res = await AIProviderManager._chat_ollama(messages, config, temperature)
                elif provider == "gemini" and config.get("gemini_api_key", "").strip():
                    res = await AIProviderManager._chat_gemini(messages, config, temperature)
                elif provider == "groq" and config.get("groq_api_key", "").strip():
                    res = await AIProviderManager._chat_openai_compatible_provider(messages, config, "groq", temperature)
                elif provider == "openai" and config.get("openai_api_key", "").strip():
                    res = await AIProviderManager._chat_openai_compatible_provider(messages, config, "openai", temperature)
                elif provider == "deepseek" and config.get("deepseek_api_key", "").strip():
                    res = await AIProviderManager._chat_openai_compatible_provider(messages, config, "deepseek", temperature)
                elif provider == "custom" and config.get("custom_ai_url", "").strip():
                    res = await AIProviderManager._chat_openai_compatible_provider(messages, config, "custom", temperature)

                if res and res.strip():
                    if provider != selected_provider:
                        logger.info(f"[AI Chain] Primary '{selected_provider}' unavailable → Responded via '{provider}'")
                    else:
                        logger.info(f"[AI Chain] Successfully generated AI response via '{provider}'")
                    return res.strip()

            except Exception as e:
                last_error = e
                logger.info(f"[AI Chain] Provider '{provider}' failed: {e}")

        logger.error(f"[AI Chain] All AI providers exhausted. Last error: {last_error}")
        return None


    @staticmethod
    async def complete_text(prompt: str, config: Dict[str, Any], temperature: float = 0.0) -> Optional[str]:
        """Unified simple prompt completion entry point."""
        messages = [{"role": "user", "content": prompt}]
        return await AIProviderManager.complete_chat(messages, config, temperature)

    @staticmethod
    async def complete_coder(messages: List[Dict[str, str]], config: Dict[str, Any], temperature: float = 0.2) -> Optional[str]:
        """
        Dedicated code generation engine for Qwen 2.5 Coder 0.5B (or specified coder model).
        Completely isolated from the customer service / chat model.
        Priority:
        1. Ollama local instance running qwen2.5-coder:0.5b (or coder_model in config)
        2. Local llama-server running coder GGUF
        3. Fallback to AI provider chain if coder model isn't currently pulled/running locally
        """
        coder_model = config.get("coder_model", "qwen2.5-coder:0.5b")
        coder_ollama_url = config.get("coder_ollama_url", config.get("ollama_url", "http://localhost:11434"))

        # 1. Try custom local endpoint (llama-server on port 8081) first if configured
        custom_url = config.get("custom_ai_url", "")
        if custom_url:
            try:
                res = await AIProviderManager._chat_openai_compatible_provider(messages, config, "custom", temperature)
                if res and res.strip():
                    logger.info("[CoderEngine:Local] Code generated via local engine endpoint")
                    return res.strip()
            except Exception as e:
                logger.debug(f"[CoderEngine:Local] Custom coder endpoint note: {e}")

        # 2. Try dedicated Qwen Coder in Ollama
        try:
            res = await AIProviderManager._chat_ollama(
                messages,
                {"ollama_url": coder_ollama_url, "ollama_model": coder_model},
                temperature
            )
            if res and res.strip():
                logger.info(f"[CoderEngine:Qwen] Successfully generated extension code using '{coder_model}'")
                return res.strip()
        except Exception as e:
            logger.debug(f"[CoderEngine:Qwen] Ollama coder attempt note: {e}")


        # 3. Fallback to general AI completion chain
        logger.info(f"[CoderEngine] Coder model '{coder_model}' offline. Falling back to primary AI provider for extension code generation.")
        return await AIProviderManager.complete_chat(messages, config, temperature)

    # ---------------- Ollama Implementation ----------------
    @staticmethod
    async def _chat_ollama(messages: List[Dict[str, str]], config: Dict[str, Any], temperature: float) -> Optional[str]:
        url = f"{config.get('ollama_url', 'http://localhost:11434').rstrip('/')}/api/chat"
        model = config.get("ollama_model", "llama3.2:3b")

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature}
        }

        try:
            async with _INFERENCE_SEMAPHORE:
                client = await AIProviderManager._get_client()
                resp = await client.post(url, json=payload, timeout=15.0)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.debug(f"Ollama local not reachable: {e}")
        return None

    # ---------------- Google Gemini API Implementation ----------------
    @staticmethod
    async def _chat_gemini(messages: List[Dict[str, str]], config: Dict[str, Any], temperature: float) -> Optional[str]:
        api_key = config.get("gemini_api_key", "").strip()
        user_model = config.get("gemini_model", "").strip() or "gemini-2.5-flash"

        if not api_key:
            return None

        contents = []
        system_instruction = None

        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})

        clean_user_model = user_model.replace("models/", "")
        # Ordered by speed/cost: fast models first, pro models as last resort
        candidate_models = [
            clean_user_model,
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-flash-latest",
            "gemini-flash-lite-latest",
            "gemini-2.5-pro",
            "gemini-pro-latest",
        ]
        seen = set()
        models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]

        client = await AIProviderManager._get_client()

        for model in models_to_try:
            for api_version in ("v1beta", "v1"):
                url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent?key={api_key}"
                payload: Dict[str, Any] = {
                    "contents": contents,
                    "generationConfig": {"temperature": temperature}
                }
                if system_instruction and api_version == "v1beta":
                    payload["systemInstruction"] = system_instruction
                elif system_instruction and api_version == "v1":
                    if contents and contents[0]["role"] == "user":
                        orig_text = contents[0]["parts"][0]["text"]
                        sys_text = system_instruction["parts"][0]["text"]
                        contents[0]["parts"][0]["text"] = f"{sys_text}\n\n{orig_text}"

                try:
                    resp = await client.post(url, json=payload, timeout=20.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "").strip()
                except Exception as e:
                    logger.debug(f"Gemini candidate '{model}' failed: {e}")
        return None

    # ---------------- OpenAI Compatible Provider ----------------
    @staticmethod
    async def _chat_openai_compatible_provider(messages: List[Dict[str, str]], config: Dict[str, Any], provider: str, temperature: float) -> Optional[str]:
        if provider == "groq":
            base_url = "https://api.groq.com/openai/v1"
            api_key = config.get("groq_api_key", "").strip()
            model = config.get("groq_model", "llama-3.3-70b-versatile").strip()
        elif provider == "deepseek":
            base_url = "https://api.deepseek.com"
            api_key = config.get("deepseek_api_key", "").strip()
            model = config.get("deepseek_model", "deepseek-chat").strip()
        elif provider == "custom":
            base_url = config.get("custom_ai_url", "http://localhost:1234/v1").rstrip('/')
            api_key = config.get("custom_ai_key", "").strip() or "none"
            model = config.get("custom_ai_model", "local-model").strip()
        else:  # openai
            base_url = config.get("openai_base_url", "https://api.openai.com/v1").rstrip('/')
            api_key = config.get("openai_api_key", "").strip()
            model = config.get("openai_model", "gpt-4o-mini").strip()

        if not api_key and provider not in ("custom", "ollama"):
            return None

        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stop": ["```\n\n", "User:", "<|im_end|>", "### Explanation", "### شرح"]
        }

        timeout_val = 5.0 if ("localhost" in base_url or "127.0.0.1" in base_url) else 30.0
        is_local = "localhost" in base_url or "127.0.0.1" in base_url or "8081" in base_url

        try:
            client = await AIProviderManager._get_client()
            if is_local:
                async with _INFERENCE_SEMAPHORE:
                    resp = await client.post(url, headers=headers, json=payload, timeout=timeout_val)
            else:
                resp = await client.post(url, headers=headers, json=payload, timeout=timeout_val)

            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.debug(f"OpenAI-compatible ({provider}) failed: {e}")
        return None

    # ---------------- Connection Test ----------------
    @staticmethod
    async def test_provider(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tests AI connectivity in priority order:
        1. Selected provider (or omni_engine / custom)
        2. Ollama local
        3. Cloud providers
        4. Full fallback chain
        Returns detailed status for the dashboard.
        """
        selected = config.get("ai_provider", "custom")
        test_messages = [
            {"role": "system", "content": "أنت موظف خدمة عملاء ذكي لاختبار الاتصال."},
            {"role": "user", "content": "قل 'تم الاتصال بنجاح ومستعد لخدمة العملاء' فقط."}
        ]

        results: Dict[str, str] = {}

        # ── Step 1: Test selected provider directly ──────────────────────────
        if selected in ("custom", "omni_engine"):
            try:
                res = await AIProviderManager._chat_openai_compatible_provider(test_messages, config, "custom", 0.0)
                if res:
                    results["custom"] = " متصل"
                    return {
                        "status": "success",
                        "response": res,
                        "provider": "custom",
                        "provider_label": f"Omni Engine ({config.get('custom_ai_url', '')})",
                        "all_results": results,
                    }
                else:
                    results["custom"] = " غير متاح (لم يستجب محرك Omni Engine)"
            except Exception as e:
                results["custom"] = f" خطأ: {str(e)[:60]}"
        elif selected == "ollama":
            try:
                res = await AIProviderManager._chat_ollama(test_messages, config, 0.0)
                if res:
                    results["ollama"] = " متصل"
                    return {
                        "status": "success",
                        "response": res,
                        "provider": "ollama",
                        "provider_label": f"Ollama ({config.get('ollama_model', 'local')})",
                        "all_results": results,
                    }
                else:
                    results["ollama"] = " غير متاح (الخادم المحلي لم يستجب)"
            except Exception as e:
                results["ollama"] = f" خطأ: {str(e)[:60]}"

        # ── Step 2: Try selected cloud provider ──────────────────────────────
        if selected != "ollama":
            try:
                res = None
                label = selected
                if selected == "gemini" and config.get("gemini_api_key", "").strip():
                    res = await AIProviderManager._chat_gemini(test_messages, config, 0.0)
                    label = f"Gemini ({config.get('gemini_model', '')})"
                elif selected == "groq" and config.get("groq_api_key", "").strip():
                    res = await AIProviderManager._chat_openai_compatible_provider(test_messages, config, "groq", 0.0)
                    label = f"Groq ({config.get('groq_model', '')})"
                elif selected in ("openai", "deepseek", "custom"):
                    res = await AIProviderManager._chat_openai_compatible_provider(test_messages, config, selected, 0.0)
                    label = selected.capitalize()

                if res:
                    results[selected] = " متصل"
                    return {
                        "status": "success",
                        "response": res,
                        "provider": selected,
                        "provider_label": label,
                        "all_results": results,
                    }
                else:
                    results[selected] = " لا استجابة (تحقق من الـ API Key)"
            except Exception as e:
                results[selected] = f" خطأ: {str(e)[:60]}"

        # ── Step 3: Try full chain ────────────────────────────────────────────
        res_chain = await AIProviderManager.complete_chat(test_messages, config, temperature=0.0)
        if res_chain:
            return {
                "status": "success",
                "response": res_chain + " (عبر السلسلة الاحتياطية)",
                "provider": "fallback_chain",
                "provider_label": "سلسلة الاحتياط التلقائية",
                "all_results": results,
            }

        # ── All failed ────────────────────────────────────────────────────────
        err_msg = (
            " لا يوجد اتصال بأي موديل AI.\n"
            "• تأكد أن Ollama مشغّل: ollama serve\n"
            "• أو تأكد من صحة الـ API Key في إعدادات لوحة التحكم.\n"
            "• ملاحظة: تثبيت Ollama يتيح العمل بدون إنترنت نهائياً."
        )
        return {"status": "failed", "error": err_msg, "provider": selected, "all_results": results}


async def complete_chat(messages: List[Dict[str, str]], config: Optional[Dict[str, Any]] = None, temperature: float = 0.7) -> str:
    """Convenience top-level async helper for plugins and scratch pipelines."""
    if config is None:
        try:
            from bot_logic import load_config
            config = load_config()
        except Exception:
            config = {}
    res = await AIProviderManager.complete_chat(messages, config, temperature=temperature)
    return res or "أهلاً بك! نسعد بخدمتك دائماً."

