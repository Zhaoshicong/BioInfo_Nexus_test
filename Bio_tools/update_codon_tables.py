#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kazusa密码子使用数据库批量下载工具

功能:
1. 通过字母索引(A-Z)遍历所有物种
2. 按需下载物种的密码子使用频率数据
3. 将数据保存为JSON格式
4. 生成物种ID、英文名和中文名对照表
"""

import os
import re
import time
import json
import csv
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

# 常见模式生物的中英文名称对照
COMMON_SPECIES_CN = {
    "83333": {"en": "Escherichia coli K-12", "cn": "大肠杆菌K-12"},
    "559292": {"en": "Saccharomyces cerevisiae", "cn": "酿酒酵母"},
    "7227": {"en": "Drosophila melanogaster", "cn": "黑腹果蝇"},
    "9606": {"en": "Homo sapiens", "cn": "人类"},
    "10090": {"en": "Mus musculus", "cn": "小鼠"},
    "10116": {"en": "Rattus norvegicus", "cn": "大鼠"},
    "3702": {"en": "Arabidopsis thaliana", "cn": "拟南芥"},
    "7955": {"en": "Danio rerio", "cn": "斑马鱼"},
    "4932": {"en": "Saccharomyces cerevisiae", "cn": "酿酒酵母"},
    "284812": {"en": "Schizosaccharomyces pombe", "cn": "裂殖酵母"},
    "6239": {"en": "Caenorhabditis elegans", "cn": "秀丽隐杆线虫"},
    "511145": {"en": "Escherichia coli str. K-12 substr. MG1655", "cn": "大肠杆菌K-12 MG1655"},
    "224308": {"en": "Bacillus subtilis subsp. subtilis str. 168", "cn": "枯草芽孢杆菌168"},
    "243232": {"en": "Methanocaldococcus jannaschii", "cn": "简氏甲烷球菌"},
    "99287": {"en": "Salmonella typhimurium", "cn": "鼠伤寒沙门氏菌"}
}

class KazusaDownloader:
    def __init__(self, output_dir="Bio_tools/data/codon_tables", max_workers=5, delay=1, save_json=False):
        self.base_url = "https://www.kazusa.or.jp/codon/"
        self.output_dir = output_dir
        self.max_workers = max_workers  # 并行下载线程数
        self.delay = delay  # 请求间隔(秒)
        self.stats = {"success": 0, "failed": 0, "skipped": 0}
        self.species_map = {}  # 存储物种ID和名称的映射
        self.save_json = save_json  # 是否保存JSON格式的对照表
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def get_alpha_links(self):
        """获取所有字母索引链接(A-Z)"""
        response = requests.get(self.base_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        alpha_links = []
        # 查找A-Z字母链接
        for link in soup.find_all('a'):
            href = link.get('href')
            text = link.text.strip()
            if text in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                alpha_links.append(urljoin(self.base_url, href))
        
        # 添加特殊类别
        for special in ["Chloroplast", "Mitochondrion", "Others"]:
            for link in soup.find_all('a', text=special):
                alpha_links.append(urljoin(self.base_url, link.get('href')))
        
        return alpha_links
    
    def get_species_from_page(self, page_url):
        """从字母索引页面提取所有物种链接"""
        print(f"获取物种列表: {page_url}")
        response = requests.get(page_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        species_links = []
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and "showcodon.cgi?species=" in href:
                species_url = urljoin(self.base_url, href)
                species_name = link.text.strip()
                species_id = href.split("species=")[1].split("&")[0]
                species_links.append({
                    "name": species_name,
                    "id": species_id,
                    "url": species_url
                })
        
        return species_links
    
    def extract_codon_data(self, html_content):
        """从HTML内容中提取密码子使用频率数据"""
        frequencies = {}
        
        # 匹配密码子使用表数据，尝试多种可能的格式
        patterns = [
            r'([ACGT]{3})\s+([\d\.]+)\(\s*(\d+)\)',  # 格式1: TTT 17.6(250971)
            r'([ACGT]{3})\s+([\d\.]+)\s+\(\s*(\d+)\)'  # 格式2: TTT 17.6 (250971)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                break
        
        if not matches:
            return None
            
        # 计算总密码子数
        total_count = sum(int(count) for _, _, count in matches)
        if total_count == 0:
            return None
            
        # 计算频率
        for codon, _, count in matches:
            # 将DNA密码子转换为RNA密码子
            rna_codon = codon.replace('T', 'U')
            freq = int(count) / total_count
            frequencies[rna_codon] = freq
            
        return frequencies
    
    def download_codon_data(self, species):
        """下载单个物种的密码子使用数据"""
        species_id = species["id"]
        species_name = species["name"]
        output_file = os.path.join(self.output_dir, f"{species_id}.json")
        
        # 添加到物种映射表
        self.species_map[species_id] = {
            "name": species_name,
            "cn_name": COMMON_SPECIES_CN.get(species_id, {}).get("cn", "")
        }
        
        # 如果文件已存在则跳过下载，但仍然将物种信息添加到映射表
        if os.path.exists(output_file):
            print(f"跳过 [{species_id}] {species_name} - 文件已存在")
            self.stats["skipped"] += 1
            return
        
        try:
            print(f"下载 [{species_id}] {species_name}")
            response = requests.get(species["url"])
            
            # 提取密码子频率数据
            frequencies = self.extract_codon_data(response.text)
            if not frequencies:
                print(f"错误: 无法提取 [{species_id}] {species_name} 的密码子数据")
                self.stats["failed"] += 1
                return
            
            # 保存为JSON文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(frequencies, f, indent=2, ensure_ascii=False)
            
            print(f"成功保存 [{species_id}] {species_name} 的数据")
            self.stats["success"] += 1
            
            # 添加延迟防止过快请求
            time.sleep(self.delay)
            
        except Exception as e:
            print(f"错误: 下载 [{species_id}] {species_name} 时发生错误: {str(e)}")
            self.stats["failed"] += 1
    
    def run(self, letters=None, limit=None):
        """运行下载器，可以指定要下载的字母和限制数量"""
        # 获取字母索引链接
        all_alpha_links = self.get_alpha_links()
        
        # 如果指定了字母，只下载这些字母的物种
        if letters:
            letters = [l.upper() for l in letters]
            alpha_links = [link for link in all_alpha_links if any(letter in link for letter in letters)]
        else:
            alpha_links = all_alpha_links
        
        print(f"准备处理 {len(alpha_links)} 个字母索引页面")
        all_species = []
        
        # 获取所有物种列表
        for alpha_link in alpha_links:
            species_list = self.get_species_from_page(alpha_link)
            all_species.extend(species_list)
            print(f"找到 {len(species_list)} 个物种，当前总数: {len(all_species)}")
            time.sleep(0.5)  # 短暂延迟
        
        # 如果有限制，只下载指定数量
        if limit and limit > 0:
            all_species = all_species[:limit]
            
        print(f"总共需要下载 {len(all_species)} 个物种的数据")
        
        # 并行下载物种数据
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            executor.map(self.download_codon_data, all_species)
        
        # 保存物种ID-名称对照表
        self.save_species_map()
        
        # 打印统计信息
        print("\n====== 下载统计 ======")
        print(f"总物种数: {len(all_species)}")
        print(f"成功: {self.stats['success']}")
        print(f"失败: {self.stats['failed']}")
        print(f"跳过: {self.stats['skipped']}")
        print(f"数据保存位置: {os.path.abspath(self.output_dir)}")
        print(f"物种对照表: {os.path.join(self.output_dir, 'species_map.csv')}")
    
    def save_species_map(self):
        """保存物种ID-名称对照表"""
        # 保存为CSV文件
        csv_file = os.path.join(self.output_dir, "species_map.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["物种ID", "英文名称", "中文名称"])
            for species_id, info in self.species_map.items():
                writer.writerow([species_id, info["name"], info["cn_name"]])
        
        # 保存为JSON文件(可选)
        if self.save_json:
            json_file = os.path.join(self.output_dir, "species_map.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.species_map, f, indent=2, ensure_ascii=False)
            print(f"物种对照表已保存至: {csv_file} 和 {json_file}")
        else:
            print(f"物种对照表已保存至: {csv_file}")


def lookup_species_by_id(species_id, species_map_file=None):
    """通过ID查询物种信息"""
    # 如果未指定物种映射文件，使用默认路径
    if not species_map_file:
        species_map_file = os.path.join("Bio_tools/data/codon_tables", "species_map.json")
    
    if not os.path.exists(species_map_file):
        print(f"错误: 物种映射文件 {species_map_file} 不存在，请先运行下载器生成")
        return None
    
    # 载入物种映射表
    with open(species_map_file, 'r', encoding='utf-8') as f:
        species_map = json.load(f)
    
    # 查找物种信息
    species_info = species_map.get(species_id)
    if not species_info:
        print(f"未找到ID为 {species_id} 的物种")
        return None
    
    # 打印物种信息
    print(f"\n物种ID: {species_id}")
    print(f"英文名称: {species_info['name']}")
    print(f"中文名称: {species_info.get('cn_name', '未知')}")
    
    return species_info


def update_chinese_names(species_map_file=None, input_file=None, save_json=False):
    """更新物种中文名称"""
    # 如果未指定物种映射文件，使用默认路径
    if not species_map_file:
        species_map_file = os.path.join("Bio_tools/data/codon_tables", "species_map.json")
    
    if not os.path.exists(species_map_file):
        print(f"错误: 物种映射文件 {species_map_file} 不存在，请先运行下载器生成")
        return
    
    # 载入物种映射表
    with open(species_map_file, 'r', encoding='utf-8') as f:
        species_map = json.load(f)
    
    # 如果提供了输入文件，从中读取中文名
    if input_file and os.path.exists(input_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # 跳过表头
            for row in reader:
                if len(row) >= 3:
                    species_id, _, cn_name = row[:3]
                    if species_id in species_map and cn_name.strip():
                        species_map[species_id]["cn_name"] = cn_name.strip()
        print(f"已从 {input_file} 更新物种中文名")
    
    # 否则，手动输入常用物种的中文名
    else:
        print("\n请输入物种ID和中文名（每行一个，格式: 物种ID,中文名，输入空行结束）:")
        while True:
            line = input().strip()
            if not line:
                break
            
            parts = line.split(',')
            if len(parts) != 2:
                print("格式错误，请使用: 物种ID,中文名")
                continue
            
            species_id, cn_name = parts
            species_id = species_id.strip()
            cn_name = cn_name.strip()
            
            if species_id in species_map:
                species_map[species_id]["cn_name"] = cn_name
                print(f"已更新 [{species_id}] {species_map[species_id]['name']} 的中文名为: {cn_name}")
            else:
                print(f"警告: 未找到ID为 {species_id} 的物种")
    
    # 保存更新后的物种映射表(仅在使用JSON文件时)
    if save_json:
        with open(species_map_file, 'w', encoding='utf-8') as f:
            json.dump(species_map, f, indent=2, ensure_ascii=False)
    
    # 更新CSV文件
    csv_file = os.path.splitext(species_map_file)[0] + ".csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["物种ID", "英文名称", "中文名称"])
        for species_id, info in species_map.items():
            writer.writerow([species_id, info["name"], info.get("cn_name", "")])
    
    if save_json:
        print(f"物种中文名已更新并保存到 {species_map_file} 和 {csv_file}")
    else:
        print(f"物种中文名已更新并保存到 {csv_file}")


def rebuild_species_map(directory=None, save_json=False):
    """重新构建物种ID-名称对照表，基于已下载的数据文件"""
    if not directory:
        directory = "Bio_tools/data/codon_tables"
    
    if not os.path.exists(directory):
        print(f"错误: 目录 {directory} 不存在")
        return
    
    # 创建新的映射表
    species_map = {}
    
    # 遍历目录中的所有JSON文件
    json_files = [f for f in os.listdir(directory) if f.endswith('.json') and f != 'species_map.json']
    print(f"找到 {len(json_files)} 个密码子数据文件")
    
    # 从文件名提取物种ID
    for json_file in json_files:
        species_id = os.path.splitext(json_file)[0]
        
        # 尝试从文件中读取物种信息（如果以前保存过）
        try:
            with open(os.path.join(directory, json_file), 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 一些文件可能包含物种信息元数据
                species_name = data.get("species_name", "Unknown species")
        except:
            # 如果文件不包含物种名称，使用ID作为名称
            species_name = f"Species {species_id}"
        
        # 添加到映射表
        species_map[species_id] = {
            "name": species_name,
            "cn_name": COMMON_SPECIES_CN.get(species_id, {}).get("cn", "")
        }
    
    # 保存为CSV文件
    csv_file = os.path.join(directory, "species_map.csv")
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["物种ID", "英文名称", "中文名称"])
        for species_id, info in species_map.items():
            writer.writerow([species_id, info["name"], info.get("cn_name", "")])
    
    # 保存为JSON文件(可选)
    if save_json:
        json_file = os.path.join(directory, "species_map.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(species_map, f, indent=2, ensure_ascii=False)
        print(f"已重建物种对照表，包含 {len(species_map)} 个物种")
        print(f"对照表保存至: {csv_file} 和 {json_file}")
    else:
        print(f"已重建物种对照表，包含 {len(species_map)} 个物种")
        print(f"对照表保存至: {csv_file}")
    
    return species_map


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Kazusa密码子使用数据库工具')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 下载命令
    download_parser = subparsers.add_parser('download', help='下载密码子使用数据')
    download_parser.add_argument('--letters', help='要下载的字母，如A,B,C')
    download_parser.add_argument('--limit', type=int, help='限制下载物种数量')
    download_parser.add_argument('--output', default='Bio_tools/data/codon_tables', help='输出目录')
    download_parser.add_argument('--workers', type=int, default=3, help='并行下载线程数')
    download_parser.add_argument('--delay', type=float, default=1.0, help='请求间隔(秒)')
    download_parser.add_argument('--save-json', action='store_true', help='同时保存JSON格式的对照表')
    
    # 查询命令
    lookup_parser = subparsers.add_parser('lookup', help='查询物种信息')
    lookup_parser.add_argument('id', help='物种ID')
    lookup_parser.add_argument('--map', help='物种映射文件路径')
    
    # 更新中文名命令
    update_parser = subparsers.add_parser('update_cn', help='更新物种中文名')
    update_parser.add_argument('--map', help='物种映射文件路径')
    update_parser.add_argument('--input', help='输入CSV文件，包含ID和中文名')
    update_parser.add_argument('--save-json', action='store_true', help='同时保存JSON格式的对照表')
    
    # 重建对照表命令
    rebuild_parser = subparsers.add_parser('rebuild_map', help='重建物种ID-名称对照表')
    rebuild_parser.add_argument('--dir', help='数据目录路径')
    rebuild_parser.add_argument('--save-json', action='store_true', help='同时保存JSON格式的对照表')
    
    args = parser.parse_args()
    
    # 执行对应命令
    if args.command == 'download':
        # 解析字母参数
        letters = args.letters.split(',') if args.letters else None
        
        # 创建下载器并运行
        downloader = KazusaDownloader(
            output_dir=args.output,
            max_workers=args.workers,
            delay=args.delay,
            save_json=args.save_json
        )
        downloader.run(letters=letters, limit=args.limit)
    
    elif args.command == 'lookup':
        lookup_species_by_id(args.id, args.map)
    
    elif args.command == 'update_cn':
        update_chinese_names(args.map, args.input, args.save_json)
    
    elif args.command == 'rebuild_map':
        rebuild_species_map(args.dir, args.save_json)
    
    else:
        parser.print_help() 