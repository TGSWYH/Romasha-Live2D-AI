              
import re
import os
import sys
import json
import datetime
import requests                           
from openai import OpenAI                   

import persona
import world_info
import memory_manager
import outfit_manager
import motion_manager

                              
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(app_dir, "config.json")


             
def load_config():
    default_config = {
        "api_type": "openai",                               
        "api_key": "你的apikey",
        "base_url": "你的大模型接口",
        "target_model": "gemini-3-flash-preview",
        "intimacy": 0,                
                         
        "scale": 0.5,
        "pos_x": -1,                       
        "pos_y": 200,
        "track_enabled": True,
        "touch_enabled": True,
                            
        "voice_enabled": True,
        "tts_engine": "cosyvoice",                              
        "tts_translate_to_ja": False,                                          
        "bubble_size": 1,                      
                             
        "sovits_url": "http://127.0.0.1:9880/",
                                                            
        "sovits_ref_audio": "E:/Game/Romasha_Voice/full5_356_demo.ogg",             
        "sovits_ref_text": "でもジジはそれを後悔しながら日々を過ごしていた。そうでしょ?",            
        "sovits_ref_lang": "ja",                       
        "sovits_target_lang": "ja",                         
                             
        "cosy_url": "http://127.0.0.1:9880/api/tts",
        "cosy_character": "Romasha",                                      
        "cosy_mode": "指令控制"                      
    }

                       
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            print(f"🔧 已在目录下自动生成默认配置文件: {CONFIG_FILE}")
        except Exception as e:
            print(f"⚠️ 生成配置文件失败: {e}")
        return default_config

                    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            user_config = json.load(f)

                                            
        updated = False
        for key, value in default_config.items():
            if key not in user_config:
                user_config[key] = value
                updated = True

                           
        if updated:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(user_config, f, indent=4, ensure_ascii=False)
            print("🔧 已自动为你补充缺失的配置字段。")

        print("🔧 成功读取外部配置文件 config.json！")
        return user_config

    except Exception as e:
        print(f"⚠️ 配置文件读取失败，将使用默认内置配置。错误: {e}")
        return default_config

                  
def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ 保存配置失败: {e}")


      
config = load_config()

       
SILLY_HEADERS = {
    "User-Agent": "SillyTavern/1.12.0",
    "Referer": "http://localhost:8000/",
    "Origin": "http://localhost:8000",
    "X-Requested-With": "XMLHttpRequest",
}

                         
client = OpenAI(
    api_key=config.get("api_key", ""),
    base_url=config.get("base_url", ""),
    default_headers=SILLY_HEADERS,
    timeout=120.0                                          
)
TARGET_MODEL = config.get("target_model", "")

chat_history = []


def stream_chat_with_romasha(user_text, interrupted_text, thread_obj):
    global chat_history

    memories = memory_manager.retrieve_relevant_memories(user_text)

                     
    motions_list_str = ""
    for act_key, act_info in motion_manager.MOTIONS.items():
        motions_list_str += f"- [act_{act_key}]: {act_info['desc']}\n"

                             
                             
    moods_list_str = (
        "- [mood_talk]: 正常交流的动态常态 (有呼吸感和轻微摇摆)\n"
        "- [mood_talk_alc]: 脸红娇羞、不知所措的动态常态\n"
        "- [mood_talk_ero]: 极度委屈、含泪或深情的动态常态\n"
        "- [mood_neutral]: 【特定姿势定格】强制收回动作，变成最基础的呆立静止姿势 (可在玩“一二三木头人”、被罚站、或彻底放空归零等时使用)\n"
        "- [mood_wait]: 【当前姿势冻结】保持你前一秒的动作直接定格，完全屏息不动 (适合被吓到愣住、或者屏住呼吸等僵住的情境)\n"
        "- [mood_wait_haji]: 【当前姿势冻结+碎碎念】保持你前一秒的动作定格，但嘴巴微动 (适合在任何姿势下突然陷入纠结、小声嘀咕、赌气等)\n"
    )

    outfits_list_str = (
        "- [wear_uniform_tight]: 紧身制服 (日常居家/白天)\n"
        "- [wear_uniform_dress]: 连衣裙制服 (更文雅的日常)\n"
        "- [wear_sleepwear]: 睡衣 (夜晚睡觉时穿)\n"
        "- [wear_swimsuit]: 泳装 (去海边或游泳池时穿)\n"
        "- [wear_ethnic_wear]: 民族风服饰 (较为暴露，可以当做特殊节日的服装)\n"
        "- [wear_ethnic_cloak]: 民族风斗篷 (防风防寒，里面穿着民族风服饰，或为了遮挡身体感到害羞时穿)\n"
        "- [wear_towel]: 裹浴巾 (刚洗完澡时穿)\n"
        "- [wear_bunny]: 兔女郎装 (情趣/被特殊要求时)\n"
    )

            
    hairs_list_str = (
        "- [hair_loose]: 散开头发\n"
        "- [hair_bun]: 把头发盘起来 (丸子头/马尾)\n"
    )

    current_time_str = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")
    current_outfit = outfit_manager._current_outfit if outfit_manager._current_outfit else "未知"

                                                
    is_voice_on = config.get("voice_enabled", True)
    tts_engine = config.get("tts_engine", "cosyvoice")
    use_cosyvoice = is_voice_on and (tts_engine == "cosyvoice")

                                  
    dynamic_system_prompt = f"{persona.get_romasha_prompt(use_cosyvoice)}\n\n"
    dynamic_system_prompt += f"【世界与背景档案】\n{world_info.get_full_lore()}\n\n"
    dynamic_system_prompt += f"【来自海马体的过往记忆】\n{memories if memories else '（当前没有唤醒特定的过往回忆）'}\n\n"

    dynamic_system_prompt += f"【你的当前物理状态】\n"
    dynamic_system_prompt += f"- 现实时间：{current_time_str}\n"
    dynamic_system_prompt += f"- 你当前正穿着：{current_outfit}\n"
    dynamic_system_prompt += f"- 你当前对我的【亲密度】：{config.get('intimacy', 0)} / 100 \n"
    dynamic_system_prompt += f"  (说明：负数代表厌恶/恐惧，0-30是陌生/戒备，30-60是朋友/信任，60-80是暧昧，80-100是极度依赖/深爱)\n"
    dynamic_system_prompt += f"⚠️ 换装与发型规则：你可以根据聊天情境（例如我要你换衣服、你要去洗澡、睡觉或庆祝特殊节日）自主输出 [wear_xxx] 或 [hair_xxx] 标签换衣服或发型。如果没有换装或换发型的行为，【绝对禁止】输出这两个标签！保持现状即可。\n\n"

    dynamic_system_prompt += f"【⚠️ 你的物理引擎边界（极其重要） ⚠️】\n"
    dynamic_system_prompt += f"可用服装库：\n{outfits_list_str}\n"
    dynamic_system_prompt += f"可用发型库：\n{hairs_list_str}\n"
    dynamic_system_prompt += f"常驻情绪库（决定互动后的余温）：\n{moods_list_str}\n"
    dynamic_system_prompt += f"瞬间动作库（决定第一反应）：\n{motions_list_str}\n"
    dynamic_system_prompt += f"再次警告：绝不能创造上面四个列表以外的任何标签！"

    if interrupted_text:
        injected_user_text = (
            f"【系统提示：你刚才正说到“{interrupted_text}”时被用户的以下行为打断了。"
            f"请先对行为做出自然反应，然后自行决定是否接着说完。】\n用户的行为/话语：{user_text}"
        )
    else:
        injected_user_text = user_text

    messages = [{"role": "system", "content": dynamic_system_prompt}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": injected_user_text})

    try:
        full_reply = ""
        api_type = config.get("api_type", "openai").lower()

                         
        if api_type == "openai":
                            
                                                             
            response = client.chat.completions.create(
                model=TARGET_MODEL,
                messages=messages,
                temperature=0.7,                           
                                                      
                stream=True
            )
            for chunk in response:
                if thread_obj.is_cancelled: break
                                      
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        full_reply += delta
                        thread_obj.chunk_received.emit(delta)

        elif api_type == "ollama":
                                    
            base_url = config.get("base_url", "").rstrip('/')
                                              
            if not base_url.endswith('/api/chat'):
                base_url = f"{base_url}/api/chat"

            payload = {
                "model": TARGET_MODEL,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": 0.7
                }
            }

            headers = {"Content-Type": "application/json"}
                                   
            api_key = config.get("api_key", "")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

                    
            with requests.post(base_url, json=payload, headers=headers, stream=True, timeout=120.0) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if thread_obj.is_cancelled: break
                    if line:
                                                                   
                        try:
                            data = json.loads(line)
                                                                            
                            if "message" in data and "content" in data["message"]:
                                delta = data["message"]["content"]
                                full_reply += delta
                                thread_obj.chunk_received.emit(delta)
                        except json.JSONDecodeError:
                            pass                          
        else:
                                
            error_msg = f"[act_trouble] 唔……头好痛……非常抱歉，我的头佩设备好像接收到了一个完全无法解析的指令（{api_type}）……我的思维暂时连不上了……是我哪里做错了吗？"
            thread_obj.chunk_received.emit(error_msg)

                                
        if not user_text.startswith("[系统机制"):
            memory_manager.add_memory(user_text, full_reply)

        chat_history.append({"role": "user", "content": user_text})
        chat_history.append({"role": "assistant", "content": full_reply})
                                        
        if len(chat_history) > 12: chat_history = chat_history[-12:]

    except Exception as e:
                                
                                       
        short_error = str(e)[:30] + "..." if len(str(e)) > 30 else str(e)
        print(e)
        error_msg = f"[act_trouble] 呃……抱歉，我的意识刚才好像突然被切断了，脑海里只有一阵尖锐的杂音（{short_error}）……请稍微给我一点时间平复一下……"
        thread_obj.chunk_received.emit(error_msg)