from typing import List, Dict, Optional

from pymilvus import (
    MilvusClient,
    DataType,
    AnnSearchRequest,
    RRFRanker,
    WeightedRanker,
    Function,
    FunctionType,
)

from app.core.config import settings


class VectorService:
    """Milvus 操作封装（全局单例）。

    schema：dense 向量（语义） + SPARSE_FLOAT_VECTOR（关键词/BM25，由 Milvus BM25 Function 自动生成）。
    检索：混合检索 Hybrid Search，支持 RRF / Weighted 两种融合。
    """

    _instance: "VectorService | None" = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 单例：首次构造时连接 Milvus，之后复用同一 client
        if VectorService._initialized:
            return

        uri = f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}"
        print(f"-----------uri={uri}---------------")

        # 使用 MilvusClient
        self.client = MilvusClient(uri=uri)

        try:
            self.client.use_database('docs')
            print("✅ 已切换到 Milvus 数据库: docs")
        except Exception as e:
            print(f"⚠️ 切换数据库失败: {e}")
            raise

        # ✅ 定义统一的维度
        self.embedding_dim = 1024  # text-embedding-v3 默认维度
        self.collection_name = settings.MILVUS_COLLECTION  # 默认 rag_collection_v2
        self._init_collection()

        # 初始化成功后才标记，避免失败后跳过重试
        VectorService._initialized = True

    # ------------------------------------------------------------------ #
    # 集合初始化
    # ------------------------------------------------------------------ #
    def _init_collection(self):
        """初始化集合：不存在则按新 schema（dense + BM25 function sparse）创建"""
        try:
            self.client.use_database('docs')

            if self.client.has_collection(self.collection_name):
                self._load_collection()
                print(f"✅ Collection '{self.collection_name}' 已存在")
                return

            schema = self.client.create_schema(
                auto_id=True,
                enable_dynamic_field=True,
            )
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self.embedding_dim)
            # BM25 输入字段必须开启 analyzer，Function 才能对 text 分词生成稀疏向量
            schema.add_field(
                field_name="text",
                datatype=DataType.VARCHAR,
                max_length=65535,
                enable_analyzer=True,  # BM25 输入字段必须开启 analyzer
            )
            schema.add_field(field_name="sparse", datatype=DataType.SPARSE_FLOAT_VECTOR)
            schema.add_field(field_name="metadata", datatype=DataType.JSON)
            schema.add_field(field_name="doc_id", datatype=DataType.VARCHAR, max_length=100)

            # BM25 Function：插入时由 Milvus 根据 text 自动生成稀疏向量
            # 注意：本服务端版本 BM25 Function 不接受 params（analyzer_params），
            # 故不传参数，使用 Milvus 内置默认分词。
            schema.add_function(
                Function(
                    name="text_bm25",
                    function_type=FunctionType.BM25,
                    input_field_names=["text"],
                    output_field_names=["sparse"],
                )
            )

            self.client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
            )

            index_params = self.client.prepare_index_params()
            # 稠密向量索引（语义检索）
            index_params.add_index(
                field_name="vector",
                metric_type="COSINE",
                index_type="IVF_FLAT",
                params={"nlist": 1024},
            )
            # 稀疏向量索引（BM25 关键词检索）
            index_params.add_index(
                field_name="sparse",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="BM25",
            )
            self.client.create_index(
                collection_name=self.collection_name,
                index_params=index_params,
            )
            self._load_collection()
            print(f"✅ Collection '{self.collection_name}' 创建成功（hybrid schema）")

        except Exception as e:
            print(f"❌ Collection 初始化失败: {e}")
            raise

    def _load_collection(self):
        """加载 Collection 到内存"""
        try:
            self.client.load_collection(self.collection_name)
            print(f"✅ Collection '{self.collection_name}' 已加载")
        except Exception as e:
            print(f"⚠️ 加载 Collection 失败: {e}")
            raise

    # ------------------------------------------------------------------ #
    # 写入
    # ------------------------------------------------------------------ #
    def insert_vectors(
        self,
        vectors: List[List[float]],
        texts: List[str],
        metadata: List[Dict],
        doc_id: str,
    ):
        """插入向量数据（稀疏向量由 Milvus BM25 Function 根据 text 自动生成，无需传入）"""
        if not vectors:
            print("⚠️ 没有向量数据需要插入")
            return {"insert_count": 0}

        for i, vec in enumerate(vectors):
            if len(vec) != self.embedding_dim:
                raise ValueError(
                    f"向量 {i} 维度不正确: 期望 {self.embedding_dim}, 实际 {len(vec)}"
                )

        entities = []
        for vector, text, meta in zip(vectors, texts, metadata):
            entities.append(
                {
                    "vector": [float(v) for v in vector],
                    "text": text,
                    "metadata": meta,
                    "doc_id": doc_id,
                }
            )
        try:
            result = self.client.insert(
                collection_name=self.collection_name,
                data=entities
            )
            print(f"✅ 成功插入 {len(entities)} 条向量")
            return result
        except Exception as e:
            print(f"❌ 插入向量失败: {e}")
            raise

    # ------------------------------------------------------------------ #
    # 检索
    # ------------------------------------------------------------------ #
    def search(self, query_vector: List[float], top_k: int = 5, filter_expr: str = None):
        """纯稠密向量检索（语义），供需要单独语义检索的场景使用"""
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        result = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            anns_field="vector",
            limit=top_k,
            search_params=search_params,
            filter=filter_expr,
            output_fields=["text", "metadata", "doc_id"]
        )
        return result

    def hybrid_search(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int = 5,
        filter_expr: Optional[str] = None,
    ):
        """混合检索：稠密向量（语义） + BM25 稀疏向量（关键词），RRF 融合结果。

        Milvus ≥2.5：sparse 字段由 BM25 Function 自动从 query_text 生成，无需应用层编码。
        """
        # 1. 稠密检索请求
        dense_req = AnnSearchRequest(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=top_k,
        )
        # 2. 稀疏检索请求（BM25 Function，data 传原始文本）
        sparse_req = AnnSearchRequest(
            data=[query_text],
            anns_field="sparse",  # 对应 Collection Schema 中的 SPARSE_FLOAT_VECTOR 字段
            param={"metric_type": "BM25", "params": {}},  # 使用 BM25 算法计算相关性分数（值越大表示文本越匹配）
            limit=top_k,
        )

        ranker_type = (settings.HYBRID_RANKER or "rrf").lower()
        if ranker_type == "weighted":
            # 加权融合：dense:sparse = 0.5:0.5
            # 对两路的原始分数加权求和：Score = 0.5 * dense_score + 0.5 * sparse_score
            ranker = WeightedRanker(0.5, 0.5)
        else:
            # RRF（默认，对两路分数量纲差异不敏感）
            # 基于文档在两路结果中的排名计算融合分数：Score = Σ 1/(k+rank)，k 通常取 60
            ranker = RRFRanker(k=60)

        results = self.client.hybrid_search(
            collection_name=self.collection_name,
            reqs=[dense_req, sparse_req],  # 同时提交两路检索请求
            ranker=ranker,  # 指定的融合算法
            limit=top_k,
            output_fields=["text", "metadata", "doc_id"],
            filter=filter_expr,
        )
        return results

    def delete_by_doc_id(self, doc_id: str):
        """根据文档ID删除向量"""
        expr = f'doc_id == "{doc_id}"'
        self.client.delete(
            collection_name=self.collection_name,
            filter=expr,
        )
        print(f"✅ 已删除 doc_id={doc_id} 的向量")
