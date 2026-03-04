import time

import onnxruntime
import chromadb
from chromadb.utils import embedding_functions

print(f"✅ 底层 AI 引擎已预加载... onnxruntime版本: {onnxruntime.__version__}")

_client = None
_collection = None
_default_ef = None

def _get_collection():
    global _client, _collection, _default_ef
    if _collection is None:
        print("🧠 大脑线程正在接管记忆中枢...")
        _default_ef = embedding_functions.DefaultEmbeddingFunction()
        _client = chromadb.PersistentClient(path="./romasha_memory_db")
        _collection = _client.get_or_create_collection(
            name="romasha_memories",
            embedding_function=_default_ef
        )
    return _collection

def add_memory(user_text, ai_text):
    if not user_text or not ai_text: return
    timestamp = str(int(time.time() * 1000))
    memory_content = f"我曾经对Romasha说：{user_text}\nRomasha当时的回应是：{ai_text}"
    try:
        _get_collection().add(
            documents=[memory_content],
            metadatas=[{"timestamp": timestamp}],
            ids=[f"mem_{timestamp}"]
        )
        print(f"💾 [记忆已保存]: {user_text[:15]}...")
    except Exception as e:
        print(f"⚠️ 记忆写入失败: {e}")

def retrieve_relevant_memories(current_query, n_results=3):
    col = _get_collection()
    if col.count() == 0: return ""
    actual_n = min(n_results, col.count())
    try:
        results = col.query(query_texts=[current_query], n_results=actual_n)
        documents = results.get('documents', [[]])[0]
        if not documents: return ""
        return "\n---\n".join(documents)
    except Exception as e:
        print(f"⚠️ 记忆检索失败: {e}")
        return ""

def clear_all_memories():
    global _client, _collection, _default_ef
    try:
        col = _get_collection()
        _client.delete_collection(name="romasha_memories")
        _collection = _client.get_or_create_collection(
            name="romasha_memories",
            embedding_function=_default_ef
        )
        print("\n🌀 [世界线变动] 所有的过往记忆已彻底清空，迎来了崭新的相遇。")
    except Exception as e:
        print(f"⚠️ 重置失败: {e}")