from typing import List, Dict
from pymilvus import MilvusClient, DataType  # 只导入这些
from app.core.config import settings


class VectorService:
    """Milvus 操作封装（全局单例：进程内只连接/初始化一次，避免每个请求重复握手）"""

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
        self.collection_name = "rag_collection"
        self._init_collection()

        # 初始化成功后才标记，避免失败后跳过重试
        VectorService._initialized = True

    def _init_collection(self):
        """初始化Milvus集合（完全使用 MilvusClient）"""
        try:
            self.client.use_database('docs')

            # 检查 collection 是否存在
            if self.client.has_collection(self.collection_name):
                # 将 Milvus 中的 Collection（集合）从磁盘加载到内存中，使其可以进行查询、搜索和删除等操作。
                self._load_collection()
                print(f"✅ Collection '{self.collection_name}' 已存在")
                return

            # 使用 MilvusClient 创建 schema
            schema = self.client.create_schema(
                auto_id=True,
                enable_dynamic_field=True,
            )

            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self.embedding_dim)
            schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
            schema.add_field(field_name="metadata", datatype=DataType.JSON)
            schema.add_field(field_name="doc_id", datatype=DataType.VARCHAR, max_length=100)

            # 创建 collection
            self.client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
            )

            # 创建索引
            index_params = self.client.prepare_index_params()
            index_params.add_index(
                field_name="vector",
                metric_type="COSINE",
                index_type="IVF_FLAT",
                params={"nlist": 1024}
            )

            self.client.create_index(
                collection_name=self.collection_name,
                index_params=index_params
            )

            print(f"✅ Collection '{self.collection_name}' 创建成功")

        except Exception as e:
            print(f"❌ Collection 初始化失败: {e}")
            raise

    def _load_collection(self):
        """加载 Collection 到内存"""
        try:
            # MilvusClient 使用 load_collection 方法
            self.client.load_collection(self.collection_name)
            print(f"✅ Collection '{self.collection_name}' 已加载")
        except Exception as e:
            print(f"⚠️ 加载 Collection 失败: {e}")
            raise

    def insert_vectors(self, vectors: List[List[float]], texts: List[str], metadata: List[Dict], doc_id: str):
        """插入向量数据"""
        if not vectors:
            print("⚠️ 没有向量数据需要插入")
            return {"insert_count": 0}
        # ✅ 检查每个向量的维度是否正确，阿里云 text-embedding-v3 模型默认输出的是 1024 维。
        embedding_dim = 1024
        for i, vec in enumerate(vectors):
            if len(vec) != embedding_dim:
                raise ValueError(f"向量 {i} 维度不正确: 期望 {embedding_dim}, 实际 {len(vec)}")
        # ✅ 构建正确的数据格式
        entities = []
        for vector, text, meta in zip(vectors, texts, metadata):
            entities.append({
                'vector': [float(v) for v in vector],  # 确保是浮点数列表
                'text': text,
                'metadata': meta,
                'doc_id': doc_id
            })
        # ✅ 使用正确的插入方式
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

    def search(self, query_vector: List[float], top_k: int = 5, filter_expr: str = None):
        """搜索相似向量"""
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }
        result = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=top_k,
            search_params=search_params,
            filter=filter_expr,
            output_fields=["text", "metadata", "doc_id"]
        )
        return result

    def delete_by_doc_id(self, doc_id: str):
        """根据文档ID删除向量"""
        expr = f'doc_id == "{doc_id}"'
        self.client.delete(
            collection_name=self.collection_name,
            filter=expr
        )
        print(f"✅ 已删除 doc_id={doc_id} 的向量")