import re
import json

def main(text: str) -> dict:
    json_match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = text
    
    json_str = json_str.replace('\\n', '').replace('\\"', '"').strip()
    
    data = json.loads(json_str)
    
    thinking_process = data.get("thinking_process", "")
    similarity_score = data.get("similarity_score", "未找到相似度评分，请重试")
    
    print(type(similarity_score).__name__)
    if isinstance(similarity_score, (int, float)):
        similarity_score = f"相似度评分score:{similarity_score:.2f}"
    
    return {
        "thinking_process": thinking_process,
        "similarity_score": similarity_score
    }

text = "{\n\"thinking_process\":\"首先，我对比了原始审计发现报告和上传的整改报告的整体结构和内容。两份报告的格式完全一致，包含姓名、部门、日期、今日工作完成情况、遇到的问题与需协调事项、明日工作计划等部分。这表明上传的报告并非格式上的重大改动，而是内容上的调整。在'今日工作完成情况'部分，两个报告都列出了'用户中心页面改版'、'项目周会'和'技术学习'三个主要工作模块，说明结构和工作重点保持一致。然而，内容上存在一些变化。例如，布局重构技术从CSS Grid变为Flexbox，联调的后端工程师从王涛变为张伟，功能从用户个人简介修改变为昵称和头像修改，同时兼容性问题也从iOS设备输入框边框异常变为Safari浏览器样式错位。这些变化虽然体现了内容的调整，但并未改变整体工作内容的性质。在'技术学习'部分，内容从Vue 3 Composition API改为Vue 3性能优化，这表明学习内容有微调但未脱离主题范围。遇到的问题部分，问题描述从用户简介加载缓慢变为头像上传失败，原因从数据库查询效率变为网络波动，这些变化属于细节调整，但未体现深层次的整改措施。明日工作计划部分，虽然任务名称略有不同（如从'继续开发'变为'开始开发'，注册组件改为登录组件），但任务性质和范围未发生实质性改变。综上所述，虽然上传的整改报告在内容上存在一些细节调整，但整体结构、工作内容和目标均未发生重大变化，表明整改并未深入，主要为表面修改。\",\n\"similarity_score\":\"0.85\"\n}"

print(main(text)['similarity_score'])