#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions 自动化测速脚本
默认使用高质量测试配置
"""

import os
import sys
import subprocess
import csv
import time

# 地区配置
REGIONS = {
    'HKG': {'name': '香港', 'code': 'HKG'},
    'NRT': {'name': '日本', 'code': 'NRT'},
    'ICN': {'name': '韩国', 'code': 'ICN'},
    'LAX': {'name': '美国', 'code': 'LAX'},
    'SIN': {'name': '新加坡', 'code': 'SIN'}
}

# 地区映射（用于解析CSV）
REGION_MAP = {
    'HKG': '香港',
    'NRT': '日本',
    'KIX': '日本',
    'ITM': '日本',
    'FUK': '日本',
    'ICN': '韩国',
    'LAX': '美国',
    'SJC': '美国',
    'SEA': '美国',
    'SFO': '美国',
    'EWR': '美国',
    'IAD': '美国',
    'ORD': '美国',
    'DFW': '美国',
    'SIN': '新加坡'
}

# 高质量测试配置
SPEEDTEST_CONFIG = {
    'dn_count': '20',      # 测试50个IP
    'speed_limit': '100',    # 下载速度下限 5 MB/s
    'time_limit': '200'    # 延迟上限 200 ms
}

def run_command(cmd, timeout=600):
    """运行命令并返回结果"""
    try:
        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, 
            timeout=timeout,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"⏱️  命令超时 ({timeout}秒)")
        return False
    except Exception as e:
        print(f"❌ 命令执行失败: {e}")
        return False

def download_speedtest_tool():
    """下载测速工具"""
    print("\n" + "="*70)
    print("步骤0: 下载测速工具")
    print("="*70)
    
    tool_name = 'CloudflareST_proxy_linux_amd64'
    
    if os.path.exists(tool_name):
        print(f"✓ 工具已存在: {tool_name}")
        return tool_name
    
    # 下载工具
    download_url = "https://github.com/byJoey/CloudflareSpeedTest/releases/download/v1.0/CloudflareST_proxy_linux_amd64.tar.gz"
    
    print(f"下载地址: {download_url}")
    
    # 使用 wget 下载
    cmd = ['wget', '-O', 'speedtest.tar.gz', download_url]
    if not run_command(cmd, timeout=120):
        print("❌ 下载失败")
        return None
    
    # 解压
    print("解压文件...")
    cmd = ['tar', '-xzf', 'speedtest.tar.gz']
    if not run_command(cmd, timeout=60):
        print("❌ 解压失败")
        return None
    
    # 赋予执行权限
    if os.path.exists(tool_name):
        os.chmod(tool_name, 0o755)
        print(f"✓ 工具准备完成: {tool_name}")
        return tool_name
    else:
        print("❌ 未找到可执行文件")
        return None

def download_cloudflare_ips():
    """下载 Cloudflare IP 列表"""
    print("\n" + "="*70)
    print("下载 Cloudflare IP 列表")
    print("="*70)
    
    if os.path.exists('Cloudflare.txt'):
        print("✓ IP列表已存在")
        return True
    
    url = "https://www.cloudflare.com/ips-v4"
    cmd = ['wget', '-O', 'Cloudflare.txt', url]
    
    if run_command(cmd, timeout=30):
        print("✓ IP列表下载完成")
        return True
    else:
        print("❌ IP列表下载失败")
        return False

def detect_regions(tool_name):
    """检测可用地区"""
    print("\n" + "="*70)
    print("步骤1: 检测可用地区")
    print("="*70)
    
    # 检查是否已有扫描结果
    if os.path.exists('region_scan.csv'):
        print("✓ 找到已有地区扫描结果，跳过检测")
        return True
    
    print("🔍 开始扫描 Cloudflare 数据中心...")
    print("⏱️  预计需要 1-2 分钟...")
    
    # 运行地区检测
    cmd = [
        f'./{tool_name}',
        '-dd',  # 禁用下载测速
        '-tl', '9999',  # 高延迟阈值
        '-httping',  # 使用HTTPing模式
        '-url', 'https://jhb.ovh',
        '-o', 'region_scan.csv'
    ]
    
    success = run_command(cmd, timeout=180)
    
    if success and os.path.exists('region_scan.csv'):
        print("✅ 地区检测完成")
        return True
    else:
        print("⚠️  地区检测失败，将使用默认配置")
        return False

def extract_region_ips(region_code):
    """从扫描结果中提取指定地区的IP"""
    if not os.path.exists('region_scan.csv'):
        return []
    
    ips = []
    try:
        with open('region_scan.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                colo = row.get('地区码', '').strip()
                if colo == region_code:
                    ip = row.get('IP 地址', '').strip()
                    if ip and ip != 'N/A':
                        ips.append(ip)
    except Exception as e:
        print(f"读取地区IP失败: {e}")
    
    return ips

def test_region(tool_name, region_code, region_name):
    """测试指定地区"""
    print("\n" + "="*70)
    print(f"测试地区: {region_name} ({region_code})")
    print("="*70)
    print(f"📊 测试配置: 高质量测试")
    print(f"   - IP数量: {SPEEDTEST_CONFIG['dn_count']}")
    print(f"   - 速度下限: {SPEEDTEST_CONFIG['speed_limit']} MB/s")
    print(f"   - 延迟上限: {SPEEDTEST_CONFIG['time_limit']} ms")
    
    # 提取该地区的IP
    region_ips = extract_region_ips(region_code)
    
    if region_ips:
        print(f"✓ 找到 {len(region_ips)} 个 {region_name} 地区的IP")
        
        # 创建临时IP文件
        ip_file = f"{region_code.lower()}_ips.txt"
        with open(ip_file, 'w', encoding='utf-8') as f:
            for ip in region_ips:
                f.write(f"{ip}\n")
        
        # 运行测速
        output_file = f"{region_code.lower()}_result.csv"
        cmd = [
            f'./{tool_name}',
            '-f', ip_file,
            '-dn', SPEEDTEST_CONFIG['dn_count'],
            '-sl', SPEEDTEST_CONFIG['speed_limit'],
            '-tl', SPEEDTEST_CONFIG['time_limit'],
            '-o', output_file
        ]
        
        print(f"⏱️  开始测速（预计需要2-5分钟）...")
        success = run_command(cmd, timeout=600)
        
        # 清理临时文件
        if os.path.exists(ip_file):
            os.remove(ip_file)
        
        if success and os.path.exists(output_file):
            # 统计结果
            count = 0
            with open(output_file, 'r', encoding='utf-8') as f:
                count = len(f.readlines()) - 1  # 减去标题行
            print(f"✅ {region_name} 测速完成，找到 {count} 个优质IP")
            return True
        else:
            print(f"⚠️  {region_name} 测速失败")
            return False
    else:
        print(f"⚠️  未找到 {region_name} 地区的IP，使用全量IP测试")
        
        # 使用全量IP并通过cfcolo过滤
        output_file = f"{region_code.lower()}_result.csv"
        cmd = [
            f'./{tool_name}',
            '-f', 'Cloudflare.txt',
            '-dn', SPEEDTEST_CONFIG['dn_count'],
            '-sl', SPEEDTEST_CONFIG['speed_limit'],
            '-tl', SPEEDTEST_CONFIG['time_limit'],
            '-cfcolo', region_code,
            '-o', output_file
        ]
        
        print(f"⏱️  开始测速（预计需要3-8分钟）...")
        success = run_command(cmd, timeout=900)
        
        if success and os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                count = len(f.readlines()) - 1
            print(f"✅ {region_name} 测速完成，找到 {count} 个优质IP")
            return True
        else:
            print(f"⚠️  {region_name} 测速失败")
            return False

def generate_ip_txt():
    """生成 ip.txt 文件"""
    print("\n" + "="*70)
    print("步骤3: 生成优选IP列表 (ip.txt)")
    print("="*70)
    
    all_results = []
    
    # 读取所有地区的测速结果
    for region_code, region_info in REGIONS.items():
        csv_file = f"{region_code.lower()}_result.csv"
        region_name = region_info['name']
        
        if not os.path.exists(csv_file):
            print(f"⚠️  未找到 {region_name} 的结果文件")
            continue
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ip = None
                    port = None
                    
                    # 查找IP地址
                    for key in row.keys():
                        if 'IP' in key and '地址' in key:
                            ip = row[key].strip()
                            break
                    
                    # 查找端口
                    for key in row.keys():
                        if '端口' in key:
                            port = row[key].strip()
                            break
                    
                    # 处理IP中包含端口的情况
                    if ip and ':' in ip:
                        parts = ip.split(':')
                        ip = parts[0]
                        if not port and len(parts) > 1:
                            port = parts[1]
                    
                    if not port:
                        port = '443'
                    
                    if ip and ip != 'N/A':
                        all_results.append({
                            'ip': ip,
                            'port': port,
                            'country': region_name
                        })
            
            print(f"✓ 读取 {region_name}: {len([r for r in all_results if r['country'] == region_name])} 个IP")
        
        except Exception as e:
            print(f"❌ 读取 {region_name} 失败: {e}")
    
    # 写入 ip.txt
    if all_results:
        with open('ip.txt', 'w', encoding='utf-8') as f:
            for result in all_results:
                line = f"{result['ip']}:{result['port']}#{result['country']}\n"
                f.write(line)
        
        print(f"\n✅ 已生成 ip.txt，共 {len(all_results)} 个优质IP")
        
        # 按国家统计
        country_stats = {}
        for result in all_results:
            country = result['country']
            country_stats[country] = country_stats.get(country, 0) + 1
        
        print("\n📊 IP分布统计:")
        for country, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {country}: {count} 个")
        
        # 显示前10个IP
        print("\n📝 前10个IP示例:")
        for i, result in enumerate(all_results[:10], 1):
            print(f"   {i:2d}. {result['ip']}:{result['port']}#{result['country']}")
        
        return True
    else:
        print("❌ 没有找到任何测速结果")
        with open('ip.txt', 'w', encoding='utf-8') as f:
            f.write('# 暂无数据\n')
        return False

def test_proxy_ips(tool_name):
    """对优选IP进行反代测速"""
    print("\n" + "="*70)
    print("步骤4: 反代IP测速")
    print("="*70)
    
    if not os.path.exists('ip.txt'):
        print("❌ ip.txt 不存在，跳过反代测速")
        return False
    
    # 将 ip.txt 转换为纯IP列表
    print("📝 准备反代IP列表...")
    ips = []
    with open('ip.txt', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # 提取IP:端口部分
                if '#' in line:
                    ip_port = line.split('#')[0]
                    ips.append(ip_port)
    
    if not ips:
        print("❌ 没有可测试的IP")
        return False
    
    # 创建测试文件
    with open('proxy_test.txt', 'w', encoding='utf-8') as f:
        for ip_port in ips:
            f.write(f"{ip_port}\n")
    
    print(f"✓ 准备测试 {len(ips)} 个IP")
    print(f"📊 测试配置: 高质量测试")
    print(f"   - IP数量: {SPEEDTEST_CONFIG['dn_count']}")
    print(f"   - 速度下限: {SPEEDTEST_CONFIG['speed_limit']} MB/s")
    print(f"   - 延迟上限: {SPEEDTEST_CONFIG['time_limit']} ms")
    
    # 运行反代测速
    cmd = [
        f'./{tool_name}',
        '-f', 'proxy_test.txt',
        '-dn', SPEEDTEST_CONFIG['dn_count'],
        '-sl', SPEEDTEST_CONFIG['speed_limit'],
        '-tl', SPEEDTEST_CONFIG['time_limit'],
        '-o', 'proxy_result.csv'
    ]
    
    print(f"⏱️  开始反代测速（预计需要3-10分钟）...")
    success = run_command(cmd, timeout=900)
    
    # 清理临时文件
    if os.path.exists('proxy_test.txt'):
        os.remove('proxy_test.txt')
    
    if success and os.path.exists('proxy_result.csv'):
        with open('proxy_result.csv', 'r', encoding='utf-8') as f:
            count = len(f.readlines()) - 1
        print(f"✅ 反代测速完成，找到 {count} 个优质反代IP")
        return True
    else:
        print("⚠️  反代测速失败")
        return False

def generate_proxy_txt():
    """生成 pyip.txt 文件"""
    print("\n" + "="*70)
    print("步骤5: 生成反代IP列表 (pyip.txt)")
    print("="*70)
    
    if not os.path.exists('proxy_result.csv'):
        print("❌ proxy_result.csv 不存在")
        with open('pyip.txt', 'w', encoding='utf-8') as f:
            f.write('# 暂无数据\n')
        return False
    
    # 创建IP到国家的映射
    ip_country_map = {}
    if os.path.exists('ip.txt'):
        with open('ip.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '#' in line:
                    ip_port, country = line.split('#', 1)
                    ip_country_map[ip_port] = country
    
    proxy_ips = []
    
    try:
        with open('proxy_result.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ip = None
                port = None
                
                # 查找IP和端口
                for key in row.keys():
                    if 'IP' in key and '地址' in key:
                        ip = row[key].strip()
                        break
                
                for key in row.keys():
                    if '端口' in key:
                        port = row[key].strip()
                        break
                
                if ip and ':' in ip:
                    parts = ip.split(':')
                    ip = parts[0]
                    if not port and len(parts) > 1:
                        port = parts[1]
                
                if not port:
                    port = '443'
                
                if ip and ip != 'N/A':
                    ip_port = f"{ip}:{port}"
                    country = ip_country_map.get(ip_port, '未知')
                    proxy_ips.append({
                        'ip': ip,
                        'port': port,
                        'country': country
                    })
    
    except Exception as e:
        print(f"❌ 读取反代结果失败: {e}")
        return False
    
    # 写入 pyip.txt
    if proxy_ips:
        with open('pyip.txt', 'w', encoding='utf-8') as f:
            for item in proxy_ips:
                line = f"{item['ip']}:{item['port']}#{item['country']}\n"
                f.write(line)
        
        print(f"\n✅ 已生成 pyip.txt，共 {len(proxy_ips)} 个优质反代IP")
        
        # 按国家统计
        country_stats = {}
        for item in proxy_ips:
            country = item['country']
            country_stats[country] = country_stats.get(country, 0) + 1
        
        print("\n📊 反代IP分布统计:")
        for country, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {country}: {count} 个")
        
        # 显示前10个
        print("\n📝 前10个反代IP示例:")
        for i, item in enumerate(proxy_ips[:10], 1):
            print(f"   {i:2d}. {item['ip']}:{item['port']}#{item['country']}")
        
        return True
    else:
        print("❌ 没有找到任何反代IP")
        with open('pyip.txt', 'w', encoding='utf-8') as f:
            f.write('# 暂无数据\n')
        return False

def main():
    """主函数"""
    print("="*70)
    print(" Cloudflare IP 自动化测速")
    print(" 配置: 高质量测试 (50个IP, 5MB/s, 200ms)")
    print("="*70)
    
    start_time = time.time()
    
    # 步骤0: 下载测速工具
    tool_name = download_speedtest_tool()
    if not tool_name:
        print("\n❌ 测速工具下载失败")
        return 1
    
    # 下载 Cloudflare IP 列表
    if not download_cloudflare_ips():
        print("\n❌ IP列表下载失败")
        return 1
    
    # 步骤1: 检测可用地区
    detect_regions(tool_name)
    
    # 步骤2: 测试各个地区
    print("\n" + "="*70)
    print("步骤2: 测试各个地区")
    print("="*70)
    
    for region_code, region_info in REGIONS.items():
        test_region(tool_name, region_code, region_info['name'])
        time.sleep(2)  # 稍作延迟
    
    # 步骤3: 生成优选IP列表
    if not generate_ip_txt():
        print("\n❌ 优选IP列表生成失败")
        return 1
    
    # 步骤4-5: 反代测速
    test_proxy_ips(tool_name)
    generate_proxy_txt()
    
    # 完成
    elapsed_time = time.time() - start_time
    print("\n" + "="*70)
    print("✅ 所有任务完成！")
    print("="*70)
    print(f"⏱️  总耗时: {elapsed_time/60:.1f} 分钟")
    print("\n📦 生成的文件:")
    print("   - ip.txt (优选IP列表)")
    print("   - pyip.txt (反代IP列表)")
    print("="*70)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
