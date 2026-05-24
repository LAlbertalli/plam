import json
import logging
import httpx
import anyio
from uuid import UUID
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from app.models.domain import Agent, LLMModel, ShortTermMemory, RoleEnum
from app.services.docker_manager import docker_manager
from app.services.proxy_service import proxy_service
from app.services.agent_service import agent_service
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

class OrchestratorService:
    async def _get_active_model_port(self, model: LLMModel) -> tuple[str, bool]:
        """
        Ensures the model's container is running and returns the dynamic port.
        If downloading, returns (None, True).
        If fails, raises RuntimeError.
        """
        container = docker_manager.get_model_container(model.id)
        if not container or container.status != "running":
            logger.info(f"Model container not running or not found. Starting and waiting...")
            res = docker_manager.start_model(model, wait=True)
            if res == "downloading":
                return None, True
            elif not res:
                raise RuntimeError("Failed to start model container")
            
            container = docker_manager.get_model_container(model.id)
            
        if container and container.status == "running":
            port_data = container.attrs["NetworkSettings"]["Ports"].get("8000/tcp")
            if port_data:
                return port_data[0]["HostPort"], False
                
        raise RuntimeError("Model server failed to bind port")

    @asynccontextmanager
    async def active_model_context(self, model: LLMModel) -> AsyncGenerator[tuple[str, bool], None]:
        """
        Asynchronous context manager to bind model active stream lifetime tracking
        and container port loading into a single robust block.
        """
        docker_manager.increment_active_stream(model.id)
        try:
            port, downloading = await self._get_active_model_port(model)
            yield port, downloading
        finally:
            docker_manager.decrement_active_stream(model.id)

    def _calculate_stream_diff(
        self,
        accumulated_response: str,
        last_sent_sanitized: str,
        model_id: UUID,
        db: Session,
        delay_chars: int = 50,
        is_final: bool = False
    ) -> tuple[str, str | None]:
        """
        Applies output regex rewriting and calculates SSE delta payload.
        """
        sanitized = proxy_service.apply_output_chain(accumulated_response, model_id, db)
        
        if not is_final:
            safe_len = max(0, len(sanitized) - delay_chars)
            visible_sanitized = sanitized[:safe_len]
        else:
            visible_sanitized = sanitized

        min_len = min(len(last_sent_sanitized), len(visible_sanitized))
        diff_idx = 0
        while diff_idx < min_len and last_sent_sanitized[diff_idx] == visible_sanitized[diff_idx]:
            diff_idx += 1
            
        if diff_idx < len(visible_sanitized) or len(last_sent_sanitized) != len(visible_sanitized):
            diff_payload = {
                "index": diff_idx,
                "text": visible_sanitized[diff_idx:]
            }
            return visible_sanitized, f"data: {json.dumps(diff_payload)}\n\n"
        return last_sent_sanitized, None

    def _parse_thought_and_save_response(
        self,
        session_id: UUID,
        agent_id: UUID,
        next_seq: int,
        raw_response: str,
        model_id: UUID,
        db: Session
    ) -> tuple[str, str | None]:
        """
        Normalizes assistant response, extracts thinking traces, and stores it in database.
        """
        
        sanitized_response = proxy_service.apply_output_chain(raw_response, model_id, db)
        
        thinking_trace = None
        content_body = sanitized_response
        
        if "<thought>" in sanitized_response and "</thought>" in sanitized_response:
            parts = sanitized_response.split("</thought>", 1)
            thought_part = parts[0].replace("<thought>", "").strip()
            content_part = parts[1].strip()
            thinking_trace = thought_part
            content_body = content_part


            
        assistant_memory = ShortTermMemory(
            session_id=session_id,
            agent_id=agent_id,
            sequence_id=next_seq,
            role=RoleEnum.assistant,
            content=content_body,
            thinking_trace=thinking_trace
        )
        db.add(assistant_memory)
        db.commit()
        
        return content_body, thinking_trace

    async def _execute_llm_request(
        self,
        url: str,
        payload: dict,
        model_id: UUID,
        db: Session,
        stream: bool = True
    ) -> AsyncGenerator[tuple[str, str | None], None]:
        """
        Communicates with the local llama.cpp server and yields (accumulated_response, sse_payload).
        """
        accumulated_response = ""
        async with httpx.AsyncClient(timeout=60.0) as client:
            if stream:
                last_sent_sanitized = ""
                in_thought = False
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        raise RuntimeError(f"LLM Server Error: {response.status_code}")
                        
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk["choices"][0]["delta"]
                                reasoning = delta.get("reasoning_content", "")
                                content = delta.get("content", "")
                                
                                chunk_text = ""
                                if reasoning:
                                    if not in_thought:
                                        chunk_text += "<thought>"
                                        in_thought = True
                                    chunk_text += reasoning
                                if content:
                                    if in_thought:
                                        chunk_text += "</thought>"
                                        in_thought = False
                                    chunk_text += content
                                    
                                if chunk_text:
                                    accumulated_response += chunk_text
                                    last_sent_sanitized, payload_str = self._calculate_stream_diff(
                                        accumulated_response, last_sent_sanitized, model_id, db
                                    )
                                    yield accumulated_response, payload_str
                            except Exception:
                                pass
                
                # Final flush: close thoughts if still open, and calculate final diff
                if in_thought:
                    accumulated_response += "</thought>"
                _, final_payload_str = self._calculate_stream_diff(
                    accumulated_response, last_sent_sanitized, model_id, db, is_final=True
                )
                yield accumulated_response, final_payload_str
            else:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    raise RuntimeError(f"LLM Server Error: {response.status_code}")
                chunk = response.json()
                message = chunk["choices"][0]["message"]
                reasoning = message.get("reasoning_content", "")
                content = message.get("content", "")
                if reasoning:
                    accumulated_response = f"<thought>{reasoning}</thought>{content}"
                else:
                    accumulated_response = content
                yield accumulated_response, None


    async def run_chat_stream(
        self,
        agent_id: UUID,
        session_id: UUID,
        user_message: str,
        db: Session,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        # 1. Fetch Agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            yield f"data: {json.dumps({'error': 'Agent not found'})}\n\n"
            return
            
        # 2. Fetch Model
        model = db.query(LLMModel).filter(LLMModel.id == agent.model_id).first()
        if not model:
            yield f"data: {json.dumps({'error': 'Model not found'})}\n\n"
            return

        # 3. Handle model startup & active locks within a clean context manager
        async with self.active_model_context(model) as (port, downloading):
            if downloading:
                yield f"data: {json.dumps({'status': 'downloading', 'message': 'Model is downloading in the background...'})}\n\n"
                return

            # 4. Input Regex Chain
            processed_user_message = proxy_service.apply_input_chain(user_message, model.id, db)
            
            # 5. Build System Prompt with capabilities injected
            system_prompt = agent_service.build_system_prompt(agent.id, db)
            
            # 6. Gather History and sequence index
            history = db.query(ShortTermMemory).filter(
                ShortTermMemory.session_id == session_id
            ).order_by(ShortTermMemory.sequence_id).all()
            
            next_seq = len(history)
            
            # Save User prompt in DB (original un-rewritten user prompt)
            user_memory = ShortTermMemory(
                session_id=session_id,
                agent_id=None,
                sequence_id=next_seq,
                role=RoleEnum.user,
                content=user_message
            )
            db.add(user_memory)
            db.commit()
            
            next_seq += 1
            
            # Construct message payload
            messages = [{"role": "system", "content": system_prompt}]
            for memory in history:
                role = "user" if memory.role == RoleEnum.user else "assistant"
                messages.append({"role": role, "content": memory.content or ""})
                
            messages.append({"role": "user", "content": processed_user_message})
            
            # 7. Query llama.cpp server OpenAI-compatible completions
            url = f"http://localhost:{port}/v1/chat/completions"
            payload = {
                "model": "local-model",
                "messages": messages,
                "stream": stream
            }
            
            accumulated_response = ""
            try:
                async for response_so_far, sse_payload in self._execute_llm_request(
                    url, payload, model.id, db, stream=stream
                ):
                    accumulated_response = response_so_far
                    if sse_payload:
                        yield sse_payload
            except Exception as e:
                yield f"data: {json.dumps({'error': f'Request failed: {str(e)}'})}\n\n"
                return
                
            # 8. Post-generation normalization, thinking trace extraction and db persistence
            content_body, thinking_trace = self._parse_thought_and_save_response(
                session_id, agent.id, next_seq, accumulated_response, model.id, db
            )
            
            yield f"data: {json.dumps({'done': True, 'content': content_body, 'thinking_trace': thinking_trace})}\n\n"

orchestrator_service = OrchestratorService()
