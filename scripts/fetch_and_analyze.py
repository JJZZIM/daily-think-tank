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
    """调用 DeepSeek API 进行深度分析"""
    # 拼接新闻摘要
    news_text = ""
    for i, h in enumerate(headlines, 1):
        news_text += f"{i}. [{h['source']}] {h['title']}\n   {h['description']}\n"
    
    system_prompt = """你是一位资深的社会科学、文化哲学和经济科技领域趋势分析师。
请根据提供的今日热点新闻，生成一份具有洞察价值的每日信息简报。按以下结构输出：

1. **今日关键信号**：提炼3-5个最关键、可能产生深远影响的信号或趋势，简要说明理由。
2. **跨领域连接点**：寻找社会科学、文化哲学、经济科技之间的交叉议题，提出1-2个值得深入思考的方向。
3. **深度思考方向**：为每个领域（社科、文化哲学、经科）分别提出1-2个可供进一步研究的问题或视角。

语言精炼，观点鲜明，总字数控制在600字内。"""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"今日热点新闻如下：\n{news_text}"}
        ],
        "temperature": 0.7,
        "max_tokens": 1200
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    response = requests.post(DEEPSEEK_URL, headers=headers, json=payload)
    data = response.json()
    
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        print(f"❌ AI 分析失败：{data}")
        return "分析生成失败，请检查 API 或日志。"

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
