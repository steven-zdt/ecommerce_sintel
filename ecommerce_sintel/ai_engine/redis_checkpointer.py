"""
Checkpointer de LangGraph para el Action Graph, sobre el Redis que YA existe en el proyecto.

B2 (AUDITORIA/16_AUDITORIA_AI_ENGINE_SYNC.md): antes de esto, action_graph.py usaba
MemorySaver() -- memoria de conversacion 100% en RAM del proceso, sin backend externo. Cualquier
reinicio del contenedor sintel_ai (deploy, crash, --reload de uvicorn en cada cambio de archivo)
borraba TODAS las conversaciones activas, incluidas confirmaciones de escritura a mitad de curso.

NO usa el paquete oficial langgraph-checkpoint-redis: requiere el modulo RediSearch, verificado
en vivo que NO esta disponible en el Redis real del proyecto (redis:7.2-alpine, la misma
instancia que Channels/Celery/Cache -- "unknown command 'FT._LIST'"). La alternativa oficial de
Postgres tampoco resuelve limpio: exige degradar langgraph-checkpoint a una version que choca con
el langgraph==0.2.x ya fijado en requirements.txt. Subir langgraph en si es un cambio de mayor
riesgo (API de grafo cambio entre versiones), fuera de alcance de "agregar persistencia".

Esta clase solo implementa las operaciones que el Action Graph realmente usa (ver
action_graph.py::get_action_graph/_pending_interrupt/run_action_chat) -- sin indices de busqueda
ni deduplicacion de channel_values entre checkpoints (esa optimizacion de MemorySaver/los
checkpointers oficiales no vale la complejidad aca: una conversacion de soporte tiene decenas de
turnos, no miles). Cada checkpoint se guarda completo (incluidos channel_values) bajo su propia
clave, con TTL -- conversaciones abandonadas expiran solas en vez de acumularse para siempre.
"""
import pickle
import time
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

import redis
import redis.asyncio as aredis
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
    get_checkpoint_metadata,
)

# Misma vida util que REFRESH_TOKEN_LIFETIME de Django (convencion de "sesion" ya usada en el
# resto del proyecto) -- una conversacion sin actividad por mas de esto ya no tiene sentido
# retomarla igual, y Redis la libera solo sin necesidad de un scanner/cron aparte.
CHECKPOINT_TTL_SECONDS = 7 * 24 * 60 * 60


def _cp_key(thread_id: str, ns: str, checkpoint_id: str) -> str:
    return f"ai:cp:{thread_id}:{ns}:{checkpoint_id}"


def _writes_key(thread_id: str, ns: str, checkpoint_id: str) -> str:
    return f"ai:cpw:{thread_id}:{ns}:{checkpoint_id}"


def _index_key(thread_id: str, ns: str) -> str:
    return f"ai:cpidx:{thread_id}:{ns}"


class RedisCheckpointSaver(BaseCheckpointSaver[str]):

    def __init__(self, redis_url: str, *, ttl_seconds: int = CHECKPOINT_TTL_SECONDS) -> None:
        super().__init__()
        # decode_responses=False a proposito: los checkpoints/writes se serializan con
        # self.serde (JsonPlusSerializer) a bytes, y forzar utf-8 en el cliente rompe cualquier
        # blob binario.
        self._sync = redis.Redis.from_url(redis_url, decode_responses=False)
        self._async = aredis.Redis.from_url(redis_url, decode_responses=False)
        self._ttl = ttl_seconds

    # ── Codificacion (pura, sin I/O -- compartida entre las rutas sync y async) ──────────────

    def _encode_row(self, checkpoint: Checkpoint, metadata: CheckpointMetadata, parent_id: str | None) -> bytes:
        return pickle.dumps({
            "checkpoint": self.serde.dumps_typed(checkpoint),
            "metadata": self.serde.dumps_typed(metadata),
            "parent": parent_id,
        })

    def _decode_row(self, raw: bytes) -> tuple[Checkpoint, CheckpointMetadata, str | None]:
        row = pickle.loads(raw)
        return (
            self.serde.loads_typed(row["checkpoint"]),
            self.serde.loads_typed(row["metadata"]),
            row["parent"],
        )

    def _encode_write(self, task_id: str, channel: str, value: Any, task_path: str) -> bytes:
        return pickle.dumps((task_id, channel, self.serde.dumps_typed(value), task_path))

    def _decode_write(self, raw: bytes) -> tuple[str, str, Any, str]:
        task_id, channel, value_typed, task_path = pickle.loads(raw)
        return task_id, channel, self.serde.loads_typed(value_typed), task_path

    def _build_tuple(self, config: RunnableConfig, thread_id: str, ns: str, checkpoint_id: str,
                      row_raw: bytes, writes_raw: dict) -> CheckpointTuple:
        checkpoint, metadata, parent_id = self._decode_row(row_raw)
        pending_writes = [self._decode_write(v) for v in writes_raw.values()]
        return CheckpointTuple(
            config={"configurable": {"thread_id": thread_id, "checkpoint_ns": ns, "checkpoint_id": checkpoint_id}},
            checkpoint=checkpoint,
            metadata=metadata,
            pending_writes=pending_writes,
            parent_config=(
                {"configurable": {"thread_id": thread_id, "checkpoint_ns": ns, "checkpoint_id": parent_id}}
                if parent_id else None
            ),
        )

    # ── Sync ──────────────────────────────────────────────────────────────────────────────

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id: str = config["configurable"]["thread_id"]
        ns: str = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)
        if checkpoint_id is None:
            ids = self._sync.smembers(_index_key(thread_id, ns))
            if not ids:
                return None
            checkpoint_id = max(cid.decode() for cid in ids)
        row_raw = self._sync.get(_cp_key(thread_id, ns, checkpoint_id))
        if row_raw is None:
            return None
        writes_raw = self._sync.hgetall(_writes_key(thread_id, ns, checkpoint_id))
        return self._build_tuple(config, thread_id, ns, checkpoint_id, row_raw, writes_raw)

    def list(self, config: RunnableConfig | None, *, filter: dict[str, Any] | None = None,
             before: RunnableConfig | None = None, limit: int | None = None) -> Iterator[CheckpointTuple]:
        if config is None:
            return
        thread_id: str = config["configurable"]["thread_id"]
        ns: str = config["configurable"].get("checkpoint_ns", "")
        ids = sorted((cid.decode() for cid in self._sync.smembers(_index_key(thread_id, ns))), reverse=True)
        before_id = get_checkpoint_id(before) if before else None
        yielded = 0
        for checkpoint_id in ids:
            if before_id and checkpoint_id >= before_id:
                continue
            row_raw = self._sync.get(_cp_key(thread_id, ns, checkpoint_id))
            if row_raw is None:
                continue
            checkpoint, metadata, parent_id = self._decode_row(row_raw)
            if filter and not all(v == metadata.get(k) for k, v in filter.items()):
                continue
            if limit is not None and yielded >= limit:
                break
            writes_raw = self._sync.hgetall(_writes_key(thread_id, ns, checkpoint_id))
            yield self._build_tuple(config, thread_id, ns, checkpoint_id, row_raw, writes_raw)
            yielded += 1

    def put(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata,
            new_versions: ChannelVersions) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        ns = config["configurable"]["checkpoint_ns"]
        checkpoint_id = checkpoint["id"]
        parent_id = config["configurable"].get("checkpoint_id")
        row = self._encode_row(checkpoint, get_checkpoint_metadata(config, metadata), parent_id)
        key = _cp_key(thread_id, ns, checkpoint_id)
        pipe = self._sync.pipeline()
        pipe.set(key, row, ex=self._ttl)
        pipe.sadd(_index_key(thread_id, ns), checkpoint_id)
        pipe.expire(_index_key(thread_id, ns), self._ttl)
        pipe.execute()
        return {"configurable": {"thread_id": thread_id, "checkpoint_ns": ns, "checkpoint_id": checkpoint_id}}

    def put_writes(self, config: RunnableConfig, writes: Sequence[tuple[str, Any]],
                    task_id: str, task_path: str = "") -> None:
        thread_id = config["configurable"]["thread_id"]
        ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]
        key = _writes_key(thread_id, ns, checkpoint_id)
        existing = self._sync.hkeys(key) if writes else []
        existing_fields = {f.decode() for f in existing}
        mapping = {}
        for idx, (channel, value) in enumerate(writes):
            field = f"{task_id}:{WRITES_IDX_MAP.get(channel, idx)}"
            if WRITES_IDX_MAP.get(channel, idx) >= 0 and field in existing_fields:
                continue
            mapping[field] = self._encode_write(task_id, channel, value, task_path)
        if not mapping:
            return
        pipe = self._sync.pipeline()
        pipe.hset(key, mapping=mapping)
        pipe.expire(key, self._ttl)
        pipe.execute()

    def delete_thread(self, thread_id: str) -> None:
        for pattern in (f"ai:cp:{thread_id}:*", f"ai:cpw:{thread_id}:*", f"ai:cpidx:{thread_id}:*"):
            keys = list(self._sync.scan_iter(match=pattern, count=200))
            if keys:
                self._sync.delete(*keys)

    def get_next_version(self, current: str | None, channel: None) -> str:
        # Identico a InMemorySaver.get_next_version -- version string monotonicamente
        # creciente, formato ya esperado por el resto del Action Graph.
        import random
        current_v = 0 if current is None else (current if isinstance(current, int) else int(current.split(".")[0]))
        return f"{current_v + 1:032}.{random.random():016}"

    # ── Async (mismo modelo de datos, cliente redis.asyncio -- nunca bloquea el event loop) ──

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id: str = config["configurable"]["thread_id"]
        ns: str = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)
        if checkpoint_id is None:
            ids = await self._async.smembers(_index_key(thread_id, ns))
            if not ids:
                return None
            checkpoint_id = max(cid.decode() for cid in ids)
        row_raw = await self._async.get(_cp_key(thread_id, ns, checkpoint_id))
        if row_raw is None:
            return None
        writes_raw = await self._async.hgetall(_writes_key(thread_id, ns, checkpoint_id))
        return self._build_tuple(config, thread_id, ns, checkpoint_id, row_raw, writes_raw)

    async def alist(self, config: RunnableConfig | None, *, filter: dict[str, Any] | None = None,
                     before: RunnableConfig | None = None, limit: int | None = None) -> AsyncIterator[CheckpointTuple]:
        if config is None:
            return
        thread_id: str = config["configurable"]["thread_id"]
        ns: str = config["configurable"].get("checkpoint_ns", "")
        raw_ids = await self._async.smembers(_index_key(thread_id, ns))
        ids = sorted((cid.decode() for cid in raw_ids), reverse=True)
        before_id = get_checkpoint_id(before) if before else None
        yielded = 0
        for checkpoint_id in ids:
            if before_id and checkpoint_id >= before_id:
                continue
            row_raw = await self._async.get(_cp_key(thread_id, ns, checkpoint_id))
            if row_raw is None:
                continue
            checkpoint, metadata, parent_id = self._decode_row(row_raw)
            if filter and not all(v == metadata.get(k) for k, v in filter.items()):
                continue
            if limit is not None and yielded >= limit:
                break
            writes_raw = await self._async.hgetall(_writes_key(thread_id, ns, checkpoint_id))
            yield self._build_tuple(config, thread_id, ns, checkpoint_id, row_raw, writes_raw)
            yielded += 1

    async def aput(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata,
                   new_versions: ChannelVersions) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        ns = config["configurable"]["checkpoint_ns"]
        checkpoint_id = checkpoint["id"]
        parent_id = config["configurable"].get("checkpoint_id")
        row = self._encode_row(checkpoint, get_checkpoint_metadata(config, metadata), parent_id)
        key = _cp_key(thread_id, ns, checkpoint_id)
        pipe = self._async.pipeline()
        pipe.set(key, row, ex=self._ttl)
        pipe.sadd(_index_key(thread_id, ns), checkpoint_id)
        pipe.expire(_index_key(thread_id, ns), self._ttl)
        await pipe.execute()
        return {"configurable": {"thread_id": thread_id, "checkpoint_ns": ns, "checkpoint_id": checkpoint_id}}

    async def aput_writes(self, config: RunnableConfig, writes: Sequence[tuple[str, Any]],
                           task_id: str, task_path: str = "") -> None:
        thread_id = config["configurable"]["thread_id"]
        ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]
        key = _writes_key(thread_id, ns, checkpoint_id)
        existing = await self._async.hkeys(key) if writes else []
        existing_fields = {f.decode() for f in existing}
        mapping = {}
        for idx, (channel, value) in enumerate(writes):
            field = f"{task_id}:{WRITES_IDX_MAP.get(channel, idx)}"
            if WRITES_IDX_MAP.get(channel, idx) >= 0 and field in existing_fields:
                continue
            mapping[field] = self._encode_write(task_id, channel, value, task_path)
        if not mapping:
            return
        pipe = self._async.pipeline()
        pipe.hset(key, mapping=mapping)
        pipe.expire(key, self._ttl)
        await pipe.execute()

    async def adelete_thread(self, thread_id: str) -> None:
        for pattern in (f"ai:cp:{thread_id}:*", f"ai:cpw:{thread_id}:*", f"ai:cpidx:{thread_id}:*"):
            keys = [k async for k in self._async.scan_iter(match=pattern, count=200)]
            if keys:
                await self._async.delete(*keys)
