                  
import chromadb
import time
import os


def read_diary():
    print("📖 正在翻阅 Romasha 的记忆档案...\n")
    export_filename = "romasha_memories_export.txt"

    try:
                        
        client = chromadb.PersistentClient(path="./romasha_memory_db")

                   
        collection = client.get_collection(name="romasha_memories")

                   
        data = collection.get()

        total_memories = len(data['ids'])
        if total_memories == 0:
            print("📭 目前记忆库是空的，你们还没有创造回忆。")
            return

        print(f"✨ 总共找到 {total_memories} 条记忆！\n" + "=" * 40)

                       
        with open(export_filename, "w", encoding="utf-8") as f:
                   
            f.write(f"📖 Romasha 的记忆档案导出\n")
            f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总计记忆数量: {total_memories} 条\n")
            f.write("=" * 40 + "\n\n")

                           
            for i in range(total_memories):
                mem_id = data['ids'][i]
                text = data['documents'][i]
                metadata = data['metadatas'][i]

                       
                timestamp_ms = int(metadata.get('timestamp', 0))
                if timestamp_ms > 0:
                    time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp_ms / 1000))
                else:
                    time_str = "未知时间"

                             
                record = (
                    f"🕰️ 时间: {time_str} | 记忆ID: {mem_id}\n"
                    f"📝 内容: \n{text}\n"
                    f"{'-' * 40}\n"
                )

                              
                print(record, end="")
                f.write(record)

                        
        full_path = os.path.abspath(export_filename)
        print(f"\n✅ 记忆提取完毕！已成功保存为文本文件，你可以随时打开查看：\n📂 {full_path}")

    except Exception as e:
        print(f"⚠️ 读取记忆失败，可能是数据库不存在或被占用: {e}")


if __name__ == "__main__":
    read_diary()