# orchestrators_master.py
import numpy as np
from utils_logger import get_logger
from services_embedding_service import embed_text, get_embedding_service
from services_vector_store import get_vector_store
from services_llm_service import get_llm_service
from config_settings import settings

logger = get_logger("orchestrator")

class MasterOrchestrator:
    def __init__(self):
        # ensure services are initialized externally (main startup)
        self.embedder = get_embedding_service({"model": settings.sentence_transformers_model})
        self.vstore = get_vector_store()
        self.llm = get_llm_service({
            "groq_api_key": settings.groq_api_key,
            "groq_model": settings.groq_model
        })

    async def process(self, channel: dict, videos: list, transcripts: dict = None, top_k: int = 5):
        """
        Metadata-only FULL MODE:
        - embed title + description per video
        - store in HNSW
        - seed LLM with trimmed sample of videos + top semantic neighbors
        """
        logger.info("Starting FULL MODE Orchestrator (HNSW metadata-only)")

        # limit number of videos used to avoid large prompts
        MAX_VIDEOS = min(len(videos), getattr(settings, "max_videos_for_llm", 12))
        videos_sample = videos[:MAX_VIDEOS]

        # embed and store (metadata only)
        stored = 0
        semantic_snippets = []
        for v in videos_sample:
            vid = v.get("id")
            title = v.get("title", "") or ""
            desc = v.get("description", "") or ""
            text_to_embed = (title + "\n\n" + desc).strip()
            emb = embed_text(text_to_embed)
            if emb is not None:
                self.vstore.add(emb, vid)
                stored += 1
                semantic_snippets.append(text_to_embed[:300])

        logger.info(f"Stored {stored} metadata embeddings in HNSW.")

        # Make a seed by embedding the channel title
        channel_title = channel.get("snippet", {}).get("title", "") or channel.get("title", "") or ""
        seed_emb = embed_text(channel_title) if channel_title else None
        seed_neighbors = self.vstore.search(seed_emb, k=top_k) if seed_emb is not None else []

        # Build compact prompt (trimmed titles/descriptions)
        prompt = self._build_prompt(channel, videos_sample, seed_neighbors)

        # Call LLM with robust error handling
        try:
            llm_text_or_json = await self.llm.async_generate(prompt)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"error": f"LLM call failed: {e}", "seed_neighbors": seed_neighbors}

        # Try parse JSON; if fails, return raw text
        try:
            import json
            parsed = json.loads(llm_text_or_json)
            return {"report": parsed, "seed_neighbors": seed_neighbors}
        except Exception:
            # return raw text in report
            return {"report": llm_text_or_json, "seed_neighbors": seed_neighbors}

    def _build_prompt(self, channel, videos, neighbors):
        # compact channel block
        ch_title = channel.get("snippet", {}).get("title", "") or channel.get("title", "")
        ch_desc = channel.get("snippet", {}).get("description", "") or ""
        ch_summary = f"Channel: {ch_title}\nDescription: {ch_desc[:300]}"

        lines = [ch_summary, "\nVideos (sample):"]
        for v in videos:
            t = (v.get("title") or "")[:120]
            d = (v.get("description") or "")[:240]
            lines.append(f"- {t}\n  {d}")

        if neighbors:
            lines.append("\nTop semantic neighbors (video ids & similarity):")
            for vid, dist in neighbors:
                lines.append(f"- {vid} (dist={dist:.4f})")

        # instructions: concise output
        lines.append(
            "\nTASK: Using the above, produce a concise JSON object with keys: executive_summary (string), themes (list of strings), top_recommendations (list of short objects with title/priority), and short_actionable_tips (list). Keep output minimal and JSON only."
        )

        prompt = "\n".join(lines)
        # final safety clip
        if len(prompt) > 8000:
            prompt = prompt[:8000]
        return prompt
