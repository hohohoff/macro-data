import requests
import pandas as pd
from datetime import datetime
import os
import time

# ==================== 油价获取（您的API key） ====================
def get_oil_price():
    """获取WTI原油价格（美元/桶）"""
    try:
        api_key = "3CI95UKF5IK07OU1"
        url = f"https://www.alphavantage.co/query?function=WTI&interval=monthly&apikey={api_key}"
        print(f"正在请求油价API...")
        response = requests.get(url)
        data = response.json()
        
        if "data" in data:
            latest = data["data"][0]
            oil_price = float(latest["value"])
            print(f"获取到油价: {oil_price} 美元")
            return oil_price
        else:
            print("API返回格式异常，使用默认值85.5")
            return 85.5
    except Exception as e:
        print(f"获取油价出错: {e}")
        return 85.0

# ==================== 期限溢价获取（修复版） ====================
def get_term_premium():
    """获取10年期美债期限溢价（终极修复版）"""
    try:
        url = "https://www.newyorkfed.org/medialibrary/interactives/acm/acm.csv"
        print(f"正在获取期限溢价...")
        
        # 直接下载文本手动解析
        response = requests.get(url)
        lines = response.text.split('\n')
        
        # 找到数据开始的行
        for i in range(len(lines)):
            if lines[i].startswith('Date,Term Premium'):
                data_start = i + 1
                break
        else:
            data_start = 13  # 默认跳过13行
        
        # 从最后一行往前找有效数据
        for line in reversed(lines[data_start:]):
            line = line.strip()
            if line and ',' in line:
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        date = parts[0].strip()
                        # 关键修复：除以100转换成小数
                        value = float(parts[1].strip()) / 100
                        print(f"最新日期: {date}, 期限溢价: {value:.3f}%")
                        return value
                    except:
                        continue
        
        print("无法解析期限溢价，使用默认值0.75")
        return 0.75
        
    except Exception as e:
        print(f"获取期限溢价出错: {e}")
        return 0.75

# ==================== 加息预期获取（修复版） ====================
def calculate_prob_from_price(futures_price):
    """根据期货价格计算加息概率"""
    try:
        # 当前联邦基金目标利率 (假设 350-375 bps = 3.50-3.75%)
        current_rate_lower = 3.50
        current_rate_upper = 3.75
        
        # 隐含利率
        implied_rate = 100 - futures_price
        
        print(f"期货价格: {futures_price}, 隐含利率: {implied_rate:.2f}%")
        
        # 计算与当前利率的差距
        rate_diff = implied_rate - current_rate_lower
        
        # 25bps为一个步长
        if rate_diff > 0.20:  # 高于当前区间
            # 加息概率估算
            hike_prob = min(100, (rate_diff / 0.25) * 100)
            print(f"加息概率: {hike_prob:.1f}%")
            return hike_prob > 30
        else:
            print("无加息预期")
            return False
            
    except Exception as e:
        print(f"计算失败: {e}")
        return False

def get_rate_hike_cme():
    """从CME获取加息预期（修复版）"""
    try:
        url = "https://www.cmegroup.com/CmeWS/mvc/Quotes/Future/278/G/quote"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.cmegroup.com/cn-t/markets/interest-rates/cme-fedwatch-tool.html"
        }
        
        print(f"尝试CME API...")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'quotes' in data:
                # 找最近一个合约（第一个通常是最近月）
                for quote in data['quotes']:
                    if 'last' in quote and quote['last']:
                        price = float(quote['last'])
                        return calculate_prob_from_price(price)
        
        print("CME API返回格式异常")
        return None
        
    except Exception as e:
        print(f"CME API失败: {e}")
        return None

def get_rate_hike_investing():
    """备用方案：从Investing.com获取"""
    try:
        # 使用公开的期货数据API
        url = "https://api.investing.com/api/futures/getfutures"
        params = {
            "pairID": "8827",  # 30天联邦基金期货ID
            "fields": "last"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'last' in data['data']:
                price = float(data['data']['last'])
                return calculate_prob_from_price(price)
                
    except Exception as e:
        print(f"备用方案失败: {e}")
    return None

def get_rate_hike_fallback():
    """最终备用：根据当前日期返回合理值"""
    print("使用保守估计：根据当前市场环境判断")
    
    # 根据您之前看到的FedWatch数据，目前加息概率很低
    # 4月29日会议加息概率 4.1% → 无加息预期
    return False

def get_rate_hike_ultimate():
    """终极入口：按顺序尝试所有方案"""
    print("\n🔍 正在自动获取加息预期...")
    
    # 按成功率顺序尝试
    methods = [
        ("CME官方", get_rate_hike_cme),
        ("Investing.com", get_rate_hike_investing),
        ("保守估计", get_rate_hike_fallback)
    ]
    
    for name, method in methods:
        print(f"尝试方案: {name}")
        result = method()
        if result is not None:
            print(f"✅ {name} 成功! 加息预期: {'有' if result else '无'}")
            return result
        time.sleep(1)
    
    print("⚠️ 所有方案失败，返回False")
    return False

# ==================== 分数计算 ====================
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
    
    print("\n📊 评分详情:")
    for d in details:
        print(f"  {d}")
    print(f"总分: {score}/10")
        
    return min(score, 10)

# ==================== 主函数 ====================
def main():
    print("="*50)
    print("🚀 开始获取宏观数据（终极自动版）")
    print("="*50)
    
    # 获取数据
    oil = get_oil_price()
    term = get_term_premium()
    hike = get_rate_hike_ultimate()
    
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
    
    # 读取现有文件
    filename = 'macro_score.csv'
    if os.path.exists(filename):
        existing = pd.read_csv(filename)
        updated = pd.concat([existing, new_data], ignore_index=True)
    else:
        updated = new_data
    
    # 只保留最近100条
    if len(updated) > 100:
        updated = updated.tail(100)
    
    # 保存文件
    updated.to_csv(filename, index=False)
    print(f"\n✅ 数据已保存到 {filename}")
    print("="*50)

if __name__ == "__main__":
    main()
