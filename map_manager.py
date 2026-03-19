                
import os
import json
import sys



                                                                       
                                  
                                                                       
REGION_UNLOCK_CHAPTER = {
                                                         
    "基地核心区（指挥·研究·医疗·档案）": 1,
    "司令室": 1, "研究室": 1, "技术室": 1, "休憩室": 1, "医疗室": 1, "医疗室（石化用）": 1, "档案室": 1, "传送室": 1,

    "基地公共区（大厅·事务·通行）": 1,
    "大厅1F&2F": 1, "大厅1F&2F（周六）": 1, "自动扶梯": 1, "多目的室": 1, "讲义室": 1, "2楼事务室": 1,
    "中央电梯等待室": 1, "公告板": 1, "主柜台": 1, "厕所": 1, "模板地图": 1, "三楼": 1, "3层（初回）": 1,

    "基地训练区": 1,
    "训练室": 1, "右训练室内": 1, "右训练室内（活动用）": 1, "努普龙测试地图": 1,

    "基地生活区（宿舍与个人空间）": 1,
    "罗玛莎的房间": 1, "罗玛莎的房间门口": 1, "男性宿舍": 1, "会议室": 1,
    "卡珠娅的房间": 1, "巴尼拉的房间": 1, "Soot的房间": 1, "安蒂的房间": 1, "男性队员1的房间": 1,
    "队员1的房间(后半）": 1,

    "基地安保与拘禁区": 1,
    "独房": 1,

    "上城区市街与公共设施（索利蒂亚）": 1,
    "上层都市索利蒂亚": 1, "索利提亚": 1, "市街区全景": 1, "喷泉": 1, "喷泉前": 1, "花卉区": 1, "面包店": 1,
    "集合住宅": 1, "海兰达总部": 1,

    "商场与休闲设施（上城区）": 1,
    "商场1F后半(信息台)": 1, "商场3层商店": 1, "泳池接待处": 1, "泳池设施": 1, "男性更衣室": 1,
    "商场4层": 1, "大浴场前台": 1, "大浴场": 1, "游戏区": 1,

    "电视台与媒体设施": 1,
    "TV局": 1, "电视台摄影棚": 1,

                                                       
    "龙人村落与旧文明遗址": 2,
    "斯皮娜的故乡": 2, "吉吉的家": 2, "地下研究室": 2, "第二研究所": 2,

                                                       
    "下城区/储藏区（地下都市）": 3,
    "储藏区": 3, "地下都市中央区块": 3, "地下都市A区块": 3, "地下都市B区块": 3, "地下都市C区块": 3,
    "A区块": 3, "B区块": 3, "C区块": 3, "医院": 3, "更衣室": 3, "厕所事件用A区": 3,
    "自助洗衣店": 3, "垃圾区": 3, "地下城设定用": 3, "休息点": 3, "胶囊旅馆": 3, "旅馆": 3,
    "单间（自由休息用）": 3, "非法商店": 3, "猪鹿蝶": 3, "储存区的猪鹿蝶": 3,

    "下城竞技与赛事设施": 3,
    "斗技场": 3, "斗技场（自由赛第1场）": 3, "斗技场（罗玛莎决胜战）": 3, "走廊・控室": 3, "败者控室": 3,

    "下城风俗与灰色产业区": 3,
    "地下风俗室内": 3, "游郭内装": 3, "游郭控室": 3, "控室": 3, "梅的房间": 3, "竹的房间": 3, "松之间": 3, "竹之间": 3,
    "梅之间": 3, "中庭": 3,
    "花街内装（营业中）": 3, "赌场酒吧": 3, "脱衣剧场入口": 3, "剧院音乐ST": 3,
    "情人旅馆": 3, "许可": 3, "A房间": 3, "B房间": 3, "美容院": 3, "放松理疗馆": 3, "美容护理（事件用）": 3,

                                                           
    "通往研究室的走廊（后半）": 4,
    "大厅1F&2F（周二后半）": 4, "二楼事务室（后半）": 4, "二楼事务室走廊（后半）": 4,
    "3层（后半）": 4, "3层（夜间）": 4, "3层（后半夜用）": 4, "大厅": 4,

    "罗玛莎的房间（后半）": 4, "罗玛莎的房间（审讯后）": 4,
    "4番队宿舍（后半）": 4, "男性队员宿舍（后半）": 4,
    "独房（后半）": 4, "惩罚房": 4, "罗玛莎监禁独房": 4,

    "市街地全景（后半）": 4, "市街地全景后半（夜用）": 4, "长椅": 4,

    "商场2层网咖": 4, "商场2F后半(网咖)": 4, "饮料吧": 4, "7号包厢": 4,
    "商场3F后半": 4, "商场3F后半（泳池）": 4, "女性更衣室": 4,
    "商场3F后半(女性更衣室平泳ぎ3用)": 4, "商场3F后半(女性更衣室ショタ4用)": 4,
    "商场4F后半": 4, "大浴场后半": 4, "大浴场情色综艺用（后半）": 4, "更衣区后半": 4,
    "淋浴室": 4, "淋浴室（夜间）": 4, "淋浴室（后半）": 4,

    "5层后半（电视台演播室新闻用)": 4, "电视台演播室电击烦躁棒": 4, "购物中心5F后半（电视台演播室）": 4,

                                                       
    "终局与灾厄遗址": 5, "避难所": 5, "最终Boss房间": 5,
    "旧转送室": 5, "独房走廊（坏结局用）": 5, "斯皮娜的故乡（监禁结局）": 5
}



             
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

MAP_FILE = os.path.join(app_dir, "world_data", "game_map_system.json")


class MapManager:
    def __init__(self):
        self.map_data = {}
        self.flat_locations = {}
        self.load_map()

    def load_map(self):
        if not os.path.exists(MAP_FILE):
            print(f"⚠️ [空间感知]: 找不到地图文件: {MAP_FILE}")
            return

        try:
            with open(MAP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.map_data = data.get("MapSystem", {})

                                
            for zone_name, zone_info in self.map_data.items():
                for sub_loc_name, sub_loc_info in zone_info.get("sub_locations", {}).items():
                    self.flat_locations[sub_loc_name] = sub_loc_info
                    self.flat_locations[sub_loc_name]["zone"] = zone_name
                    self.flat_locations[sub_loc_name]["zone_desc"] = zone_info.get("description", "")
            print("🗺️ [空间感知]: 地图系统已成功加载并拍平索引。")
        except Exception as e:
            print(f"⚠️ [空间感知]: 地图文件读取失败: {e}")

    def get_current_location_lore(self, location_name, current_chapter=1):

        loc = self.flat_locations.get(location_name)
        if not loc:
            return f"【未知区域 - {location_name}】：似乎不在基地的常规地图记录中。"

                                            
        required_chapter = REGION_UNLOCK_CHAPTER.get(location_name)
        if required_chapter is None:
            required_chapter = REGION_UNLOCK_CHAPTER.get(loc['zone'], 1)

                                  
        if current_chapter < required_chapter:
                                      
            if required_chapter >= 4:
                return f"系统提示：【{location_name}】当前被高级物理安全锁封闭，罗玛莎目前的ID权限不足以进入，或者该区域正在进行系统升级。不要过度谈论此区域。"
            else:
                return f"系统提示：【{location_name}】通道受限，前方是未探索或被封锁的区域。罗玛莎对此地的情报极度匮乏。"

        info = f"你当前位于【{loc['zone']}】的【{location_name}】。\n"
        info += f"- 区域大背景：{loc.get('zone_desc', '')}\n"
        info += f"- 当前场景氛围：{loc.get('lore', '无特殊说明')}\n"

        if loc.get('related_characters'):
            info += f"- 这里常出现的人：{', '.join(loc['related_characters'])}\n"

        return info


    def get_available_locations(self, current_chapter=1):

        if not self.map_data:
            return "无可用地点"

        lines = []
        for region, data in self.map_data.items():
                                           
            req_chapter = REGION_UNLOCK_CHAPTER.get(region, 1)
            if current_chapter < req_chapter:
                continue

            locs = list(data.get("sub_locations", {}).keys())
                          
            lines.append(f"- {region}: {', '.join(locs)}")
        return "\n".join(lines)

       
map_instance = MapManager()