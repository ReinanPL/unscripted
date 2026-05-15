from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.config import Settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Interface para o provider de embedding.

    Toda chamada de embedding do projeto passa por aqui. Nenhum outro módulo
    importa diretamente sentence-transformers ou cliente de embedding remoto.
    """

    @property
    def dim(self) -> int: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalSentenceTransformersProvider:
    """Provider local com sentence-transformers.

    O modelo é carregado lazy na primeira chamada de `embed`. Isso evita
    pagar download + RAM no import dos testes que não usam embedding real.

    Vetores são L2-normalizados antes de retornar — pgvector usa distância
    coseno (`<=>`), que pressupõe normalização para resultados estáveis.
    """

    def __init__(self, settings: Settings) -> None:
        self._model_name = settings.embedding_model
        self._expected_dim = settings.embedding_dim
        self._model: SentenceTransformer | None = None

    @property
    def dim(self) -> int:
        return self._expected_dim

    def _load(self) -> SentenceTransformer:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            actual_dim = int(self._model.get_sentence_embedding_dimension() or 0)
            if actual_dim != self._expected_dim:
                raise RuntimeError(
                    f"Dimensão do modelo '{self._model_name}' é {actual_dim}, "
                    f"mas EMBEDDING_DIM está configurado como {self._expected_dim}. "
                    "Ajuste a env var ou troque o modelo."
                )
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load()
        vectors = model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [vec.tolist() for vec in vectors]


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Factory que retorna o provider de embedding com base em EMBEDDING_PROVIDER."""
    if settings.embedding_provider == "local":
        return LocalSentenceTransformersProvider(settings)
    raise RuntimeError(f"EMBEDDING_PROVIDER desconhecido: '{settings.embedding_provider}'")
