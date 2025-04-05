import requests
import os
import json
from Bio import PDB

def find_protein_structure(sequence):
    """
    通过蛋白质序列在PDB中查找最相似的结构并返回结果
    
    参数:
        sequence: 蛋白质氨基酸序列
        
    返回:
        字典对象,包含查找结果
    """
    # 创建临时目录
    output_dir = "temp"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 使用RCSB搜索API查询相似结构
        response = requests.post(
            "https://search.rcsb.org/rcsbsearch/v2/query",
            json={
                "query": {
                    "type": "terminal",
                    "service": "sequence",
                    "parameters": {
                        "evalue_cutoff": 0.01,
                        "identity_cutoff": 0.9,
                        "target": "pdb_protein_sequence",
                        "value": sequence
                    }
                },
                "return_type": "entry"
            },
            timeout=30
        )
        
        results = response.json().get("result_set", [])
        if not results:
            return {"status": "not_found", "message": "未找到相似结构"}
            
        # 获取最佳匹配
        best_hit = results[0]["identifier"].lower()
        
        # 基本结果信息
        result = {
            "status": "success",
            "pdb_id": best_hit
        }
        
        # 获取更多结构信息
        try:
            detail_response = requests.get(
                f"https://data.rcsb.org/rest/v1/core/entry/{best_hit}",
                timeout=10
            )
            details = detail_response.json()
            if "rcsb_entry_info" in details:
                info = details["rcsb_entry_info"]
                if "resolution_combined" in info:
                    result["resolution"] = info["resolution_combined"][0]
                if "polymer_entity_count_protein" in info:
                    result["protein_chains"] = info["polymer_entity_count_protein"]
        except:
            pass
        
        # 下载PDB结构文件
        pdb_file = os.path.join(output_dir, f"{best_hit}.pdb")
        pdb_url = f"https://files.rcsb.org/download/{best_hit}.pdb"
        file_response = requests.get(pdb_url, timeout=30)
        
        if file_response.status_code != 200:
            # 尝试欧洲镜像
            pdb_url = f"https://www.ebi.ac.uk/pdbe/entry-files/download/pdb{best_hit}.ent"
            file_response = requests.get(pdb_url, timeout=30)
            
        if file_response.status_code == 200:
            with open(pdb_file, "w") as f:
                f.write(file_response.text)
            result["file_path"] = pdb_file
            
            # 解析结构获取更多信息
            parser = PDB.PDBParser(QUIET=True)
            try:
                structure = parser.get_structure(best_hit, pdb_file)
                chains = {}
                for model in structure:
                    for chain in model:
                        chain_id = chain.id
                        residue_count = len(list(chain))
                        atom_count = len(list(chain.get_atoms()))
                        chains[chain_id] = {
                            "residues": residue_count,
                            "atoms": atom_count
                        }
                result["chains"] = chains
            except:
                pass
        else:
            result["status"] = "download_failed"
            result["message"] = f"无法下载PDB文件,状态码:{file_response.status_code}"
            
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    # 直接从输入获取序列
    print("请输入蛋白质氨基酸序列:")
    sequence = input().strip()
    
    if not sequence:
        print("未提供序列,使用示例序列...")
        sequence = "MVKVGVNGFGRIGRLVTRAAFNSGKVDIVAINDPFIDLNYMVYMFQYDSTHGKFHGTVKAENGKLVINGNPITIFQERDPSKIKWGDAGAEYVVESTGVFTTMEKAGAHLQGGAKRVIISAPSADAPMFVMGVNHEKYDNSLKIISNASCTTNCLAPLAKVIHDNFGIVEGLMTTVHAITATQKTVDGPSGKLWRDGRGALQNIIPASTGAAKAVGKVIPELNGKLTGMAFRVPTANVSVVDLTCRLEKPAKYDDIKKVVKQASEGPLKGILGYTEHQVVSSDFNSDTHSSTFDAGAGIALNDHFVKLISWYDNEFGYSNRVVDLMAHMASKE"
    
    # 执行查询并输出结果
    result = find_protein_structure(sequence)
    print(json.dumps(result, indent=2, ensure_ascii=False))