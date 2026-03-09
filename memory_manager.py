                   
import time

                   
                                                               
import onnxruntime
import chromadb
from chromadb.utils import embedding_functions

print(f"✅ [基地底层架构]: 生物神经网络已激活... 突触onnxruntime连接版本: {onnxruntime.__version__}")
print(f"🌟 [命运齿轮] 正在尝试建立与那个世界的连接... (核心运转正常)")

            
_client = None
_collection = None
_default_ef = None

def _get_collection():
    global _client, _collection, _default_ef
    if _collection is None:
        print("💭 [思绪浮现] 过去的记忆片段正在脑海中重组...")
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
        print(f"💾 [羁绊加深]: 刚才的对话已悄悄留在她的心底: {user_text[:15]}...")
    except Exception as e:
        print(f"⚠️ [记忆模糊]: 这一段记忆似乎像晨雾一样消散了... ({e})")

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
        print(f"⚠️ [回忆受阻]: 她努力回想，但记忆有些模糊...")
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
        print("\n🌀 [时光倒流] 所有相处的点滴如沙般流逝，你们回到了最初那份未知的初见。")
    except Exception as e:
        print(f"⚠️ [命运纠缠]: 过去的痕迹似乎难以抹除... ({e})")