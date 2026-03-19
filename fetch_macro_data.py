import requests
import pandas as pd
from datetime import datetime
import os

def get_oil_price():
    """获取WTI原油价格（美元/桶）- 使用您的免费API key"""
    try:
        # 使用您刚注册的API key
        api_key = "3CI95UKF5IK07OU1"
        url = f"https://www.alphavantage.co/query?function=WTI&interval=monthly&apikey={api_key}"
        
        print(f"正在请求油价API: {url}")
        response = requests.get(url)
        data = response.json()
        
        # 打印返回的数据，方便调试
        print("API返回数据:", data)
        
        # Alpha Vantage的返回格式是固定的
        if "data" in data:
            latest = data["data"][0]
            oil_price = float(latest["value"])
            print(f"获取到油价: {oil_price} 美元")
            return oil_price
        else:
            # 如果API返回错误信息
            print("API返回格式异常，使用默认值85.5")
            return 85.5
            
    except Exception as e:
        print(f"获取油价出错: {e}")
        return 85.0  # 出错时返回默认值

def get_term_premium():
    """获取10年期美债期限溢价（来自NY Fed）- 修复版本"""
    try:
        # NY Fed的ACM模型数据
        url = "https://www.newyorkfed.org/medialibrary/interactives/acm/acm.csv"
        print(f"正在获取期限溢价: {url}")
        
        # 关键修复：指定跳过前几行，并正确处理列
        df = pd.read_csv(url, skiprows=13, header=None, names=['date', 'term_premium'])
        print(f"获取到数据，共{len(df)}行")
        
        # 转换日期列，并按日期排序
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 取最新一行的期限溢价
        latest = df.iloc[-1]
        term_premium = float(latest['term_premium'])
        print(f"最新日期: {latest['date'].strftime('%Y-%m-%d')}, 期限溢价: {term_premium}%")
        return term_premium
    except Exception as e:
        print(f"获取期限溢价出错: {e}")
        # 备用方案：如果解析失败，尝试另一种读取方式
        try:
            df = pd.read_csv(url, skiprows=13)
            latest = df.iloc[-1]
            term_premium = float(latest.iloc[-1])
            print(f"备用方法成功，期限溢价: {term_premium}%")
            return term_premium
        except:
            return 0.75  # 出错时返回默认值

def get_rate_hike_expect():
    """获取加息预期 - 手动模式"""
    # 由于CME API需要付费，我们先用手动方式
    # 您可以每天打开 https://www.cmegroup.cn/fed-watch/ 看一眼
    # 然后把结果填在这里
    print("\n⚠️ 注意：加息预期需要手动确认！")
    print("请访问 https://www.cmegroup.cn/fed-watch/")
    print("查看最近一次FOMC会议的加息概率")
    print("如果 >30%，请把下面的返回值改成 True")
    
    # 默认返回False（不加息）
    # 如果您想手动输入，可以取消下面一行的注释，并输入y或n
    # user_input = input("今天有加息预期吗？(y/n): ").lower()
    # return user_input == 'y'
    
    return False  # 默认不加息

def calculate_macro_score(oil_price, term_premium, rate_hike):
    """计算宏观预警分数（0-10分）"""
    score = 0
    details = []
    
    # 油价评分
    if oil_price > 95:
        score += 3
        details.append(f"油价{oil_price}>95: +3分")
    elif oil_price > 90:
        score += 2
        details.append(f"油价{oil_price}>90: +2分")
    elif oil_price > 85:
        score += 1
        details.append(f"油价{oil_price}>85: +1分")
    else:
        details.append(f"油价{oil_price}<=85: +0分")
        
    # 期限溢价评分
    if term_premium > 0.8:
        score += 3
        details.append(f"期限溢价{term_premium}>0.8: +3分")
    elif term_premium > 0.7:
        score += 2
        details.append(f"期限溢价{term_premium}>0.7: +2分")
    elif term_premium > 0.6:
        score += 1
        details.append(f"期限溢价{term_premium}>0.6: +1分")
    else:
        details.append(f"期限溢价{term_premium}<=0.6: +0分")
        
    # 加息预期评分
    if rate_hike:
        score += 2
        details.append("加息预期: +2分")
    else:
        details.append("加息预期: +0分")
    
    # 打印详细评分过程
    print("\n📊 评分详情:")
    for d in details:
        print(f"  {d}")
    print(f"总分: {score}/10")
        
    return min(score, 10)  # 最高10分

def main():
    print("="*50)
    print("🚀 开始获取宏观数据")
    print("="*50)
    
    # 获取数据
    oil = get_oil_price()
    term = get_term_premium()
    hike = get_rate_hike_expect()
    
    # 计算分数
    score = calculate_macro_score(oil, term, hike)
    
    # 创建新数据行
    now = datetime.now()
    new_data = pd.DataFrame({
        'timestamp': [now.strftime('%Y-%m-%d %H:%M:%S')],
        'macro_score': [score],
        'oil_price': [round(oil, 2)],
        'term_premium': [round(term, 3)],
        'rate_hike': [hike]
    })
    
    print("\n📝 新数据:")
    print(new_data)
    
    # 读取现有文件或创建新文件
    filename = 'macro_score.csv'
    if os.path.exists(filename):
        print(f"\n📂 读取现有文件 {filename}")
        existing = pd.read_csv(filename)
        print(f"现有数据 {len(existing)} 条")
        updated = pd.concat([existing, new_data], ignore_index=True)
    else:
        print(f"\n📂 创建新文件 {filename}")
        updated = new_data
    
    # 只保留最近100条记录，避免文件太大
    if len(updated) > 100:
        updated = updated.tail(100)
        print(f"保留最近100条记录")
    
    # 保存文件
    updated.to_csv(filename, index=False)
    print(f"\n✅ 数据已保存到 {filename}")
    print(f"现在共有 {len(updated)} 条记录")
    print("="*50)

if __name__ == "__main__":
    main()
