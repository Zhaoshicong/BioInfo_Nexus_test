# 第三方许可证声明

本项目使用了以下第三方库，这些库受其各自许可证的保护：

## BioPython

BioPython使用BSD 3-Clause许可证：

```
Biopython License Agreement

Permission to use, copy, modify, and distribute this software and its documentation with or without modifications and for any purpose and without fee is hereby granted, provided that any copyright notices appear in all copies and that both those copyright notices and this permission notice appear in supporting documentation, and that the names of the contributors or copyright holders not be used in advertising or publicity pertaining to distribution of the software without specific prior permission.

THE CONTRIBUTORS AND COPYRIGHT HOLDERS OF THIS SOFTWARE DISCLAIM ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN NO EVENT SHALL THE CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```

BioPython项目主页：https://biopython.org/

## 第三方网络服务

本项目使用了以下第三方生物信息学网络服务。使用这些工具时，请注意遵守各自的使用条款：

### VaxiJen

本项目使用VaxiJen网络服务进行抗原性预测。

- 服务提供方：Faculty of Pharmacy, Medical University of Sofia
- 服务网址：https://ddg-pharmfac.net/vaxijen/
- 引用：Doytchinova IA, Flower DR. (2007) VaxiJen: a server for prediction of protective antigens, tumour antigens and subunit vaccines. BMC Bioinformatics, 8:4.

**重要提示**：VaxiJen是一种在线工具，用于基于分子特性的保护性抗原预测。使用时请尊重其服务条款。

### ToxinPred

本项目使用ToxinPred网络服务进行毒性肽预测。

- 服务提供方：IIIT Delhi
- 服务网址：https://webs.iiitd.edu.in/raghava/toxinpred/
- 引用：Gupta S, et al. (2013) In silico approach for predicting toxicity of peptides and proteins. PLoS One, 8(9):e73957.

**重要提示**：ToxinPred提供用于毒性肽预测的服务，请按照学术标准引用并遵守其使用条款。@

### ExPASy ProtParam

本项目使用ExPASy ProtParam网络服务计算蛋白质的物理化学参数。

- 服务提供方：瑞士生物信息学研究所 (SIB)
- 服务网址：https://web.expasy.org/protparam/
- 使用条款：https://www.expasy.org/terms-of-use
- 引用：Gasteiger E., et al. (2005) Protein Identification and Analysis Tools on the ExPASy Server. In: Walker J.M. (eds) The Proteomics Protocols Handbook. Humana Press.

**重要提示**：ExPASy工具包供学术和个人使用，大规模商业用途可能需要获得SIB的许可。@

## 网络爬虫使用说明

本项目包含访问上述网站的脚本，遵循以下原则：

1. 所有网络请求均设置合理延迟，以避免对目标服务器造成过大负担
2. 脚本使用唯一的会话ID并包含适当的User-Agent
3. 所有获取的数据仅用于研究和教育目的
4. 遵循网站的robots.txt文件规定

**声明**：这些脚本不用于规避任何服务限制或商业用途。我们建议大规模分析需求的用户直接与相应服务提供商联系，获取API访问权限或本地安装版本。 