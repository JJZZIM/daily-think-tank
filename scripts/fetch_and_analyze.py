import os
import requests
import json
from datetime import datetime, timedelta

# ---------- 配置区 ----------
NEWS_API_KEY = os.environ["NEWS_API_KEY"]
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
FEISHU_WEBHOOK_URL = os.environ["FEISHU_WEBHOOK_URL"]

# 要搜索的关键词（覆盖你关注的领域）
KEYWORDS = "社会科学 OR 文化哲学 OR 经济科技 OR 社会科学 OR philosophy OR technology economy"
# 获取过去 24 小时的新闻
FROM_DATE = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

# DeepSeek API 配置
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
# ---------- 配置区结束 ----------

def fetch_top_headlines():
    """从多个类别获取全球热点新闻，拼合为跨领域视野"""
    url = "https://newsapi.org/v2/top-headlines"

    # 你想要覆盖的新闻类别
    categories = [
        "business",      # 商业
        "technology",    # 科技
        "science",       # 科学
        "general",       # 综合（含政治、社会等）
    ]

    all_headlines = []

    for category in categories:
        params = {
            "apiKey": NEWS_API_KEY,
            "category": category,
            "pageSize": 10,         # 每个类别取 10 条
        }
        try:
            response = requests.get(url, params=params)
            data = response.json()
            if data["status"] == "ok":
                articles = data.get("articles", [])
                for article in articles:
                    all_headlines.append({
                        "title": article["title"],
                        "description": article.get("description", ""),
                        "url": article["url"],
                        "source": f"{article['source']['name']} [{category}]"
                    })
                print(f"✅ 类别 {category}：获取到 {len(articles)} 条新闻")
            else:
                print(f"⚠️ 类别 {category} 获取失败：{data.get('message', '未知')}")
        except Exception as e:
            print(f"❌ 类别 {category} 请求异常：{e}")

    print(f"📰 共获取 {len(all_headlines)} 条全球跨领域新闻")
    return all_headlines

def analyze_with_deepseek(headlines):
    """调用 DeepSeek API 进行深度分析（含 content 为空时的内部重试）"""
    # 拼接新闻摘要
    news_text = ""
    for i, h in enumerate(headlines, 1):
        news_text += f"{i}. [{h['source']}] {h['title']}\n   {h['description']}\n"

    base_prompt = """你是一位资深的社会科学、文化哲学和经济科技领域趋势分析师。
请根据提供的今日热点新闻，生成一份具有洞察价值的每日信息简报。按以下结构输出：

1. **今日关键信号**：提炼3-5个最关键、可能产生深远影响的信号或趋势，简要说明理由。
2. **跨领域连接点**：寻找社会科学、文化哲学、经济科技之间的交叉议题，提出1-2个值得深入思考的方向。
3. **深度思考方向**：为每个领域（社科、文化哲学、经科）分别提出1-2个可供进一步研究的问题或视角。

要求：语言精炼，观点鲜明，总字数控制在 350 字以内。"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    # 最多请求两次：第一次正常，第二次加强化提示词
    for attempt in range(1, 3):
        # 第二次请求时，追加禁止思考过程的指令
        system_prompt = base_prompt
        if attempt == 2:
            system_prompt += "\n\n重要：请直接输出最终报告，不要包含任何思考过程、分析步骤或中间推理。"

        payload = {
            "model": "deepseek-flash",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"今日热点新闻如下：\n{news_text}"}
            ],
            "temperature": 0.7,
            "max_tokens": 800
        }

        try:
            response = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=90)

            # 处理非 200 状态码
            if response.status_code != 200:
                print(f"❌ DeepSeek API 返回状态码 {response.status_code}（第 {attempt} 次）")
                print(f"   响应内容：{response.text[:300]}")
                if attempt == 1:
                    time.sleep(5)
                    continue
                return f"AI 分析失败：API 返回状态码 {response.status_code}"

            # 解析 JSON
            data = response.json()

            if "choices" not in data or len(data["choices"]) == 0:
                print(f"⚠️ 返回结构异常（第 {attempt} 次）：{json.dumps(data, ensure_ascii=False)[:300]}")
                if attempt == 1:
                    time.sleep(3)
                    continue
                return "AI 分析失败：API 返回结构异常。"

            message = data["choices"][0].get("message", {})
            content = message.get("content", "").strip()
            reasoning = message.get("reasoning_content", "").strip()

            # ✅ content 有效 → 直接返回，完全忽略 reasoning
            if content:
                print(f"✅ 成功获取分析报告，长度：{len(content)} 字符")
                return content

            # ⚠️ content 为空，但存在 reasoning → 不使用它，进入下一次重试
            if reasoning:
                print(f"⚠️ content 为空，检测到 reasoning_content（长度 {len(reasoning)}）")
                print(f"   第 {attempt} 次尝试未产出有效内容，准备重试...")
                if attempt == 1:
                    time.sleep(3)
                    continue
                return "AI 分析失败：模型仅返回了推理过程，未产出最终报告。"

            # ⚠️ 两者都为空
            print(f"⚠️ content 和 reasoning_content 均为空（第 {attempt} 次）")
            print(f"   完整响应：{json.dumps(data, ensure_ascii=False)[:500]}")
            if attempt == 1:
                time.sleep(3)
                continue
            return "AI 分析失败：API 返回了空内容。"

        except requests.exceptions.Timeout:
            print(f"❌ 请求超时（第 {attempt} 次）")
            if attempt == 1:
                time.sleep(5)
                continue
            return "AI 分析失败：请求超时，请稍后重试。"

        except Exception as e:
            print(f"❌ 调用异常（第 {attempt} 次）：{type(e).__name__}: {e}")
            if attempt == 1:
                time.sleep(5)
                continue
            return f"AI 分析失败：{type(e).__name__}"

def send_to_feishu(content):
    """推送报告到飞书群"""
    payload = {
        "msgtype": "markdown",
        "markdown": {"content": content}
    }
    
    response = requests.post(FEISHU_WEBHOOK_URL, json=payload)
    if response.status_code == 200 and response.json().get("StatusCode") == 0:
        print("✅ 报告已成功推送到飞书。")
    else:
        print(f"❌ 飞书推送失败：{response.text}")

def main():
    print("🔍 正在获取新闻...")
    headlines = fetch_top_headlines()
    if not headlines:
        print("⚠️ 未获取到新闻，程序结束。")
        return
    
    print(f"📰 获取到 {len(headlines)} 条新闻，开始 AI 分析...")
    analysis = analyze_with_deepseek(headlines)
    
    print("📤 正在推送到飞书...")
    send_to_feishu(analysis)

if __name__ == "__main__":
    main()
