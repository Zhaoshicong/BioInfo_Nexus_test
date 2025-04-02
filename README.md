# BioInfo Nexus

BioInfo Nexus是一个专业的生物信息学集成平台，致力于为科研人员提供全面的生物序列分析工具和数据资源。

## 功能特点

- **强大的序列分析工具**：支持蛋白质参数计算、信号肽预测、抗原性预测等多种分析功能
- **用户账户系统**：支持用户注册、登录、邮箱验证等功能
- **数据可视化**：提供直观的结果展示和图表生成
- **安全可靠**：采用JWT认证，确保用户数据安全

## 快速开始

### 开发环境

1. 克隆代码库：
```bash
git clone https://github.com/your-username/bioinfo-nexus.git
cd bioinfo-nexus
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp .env.example .env
# 编辑.env文件，填写必要的配置信息
```

4. 运行应用：
```bash
python app.py
```

5. 访问应用：
在浏览器中打开 http://localhost:5000

### 生产环境部署

详细的部署指南请参考 [BioInfo_Nexus_宝塔部署流程.txt](BioInfo_Nexus_宝塔部署流程.txt) 文件。

## 主要工具

BioInfo Nexus集成了以下生物信息学工具：

1. **ProtParam**：计算蛋白质分子量等基本物理化学参数，基于BioPython工具
2. **SignalP**：预测蛋白质信号肽位置和切割位点，使用DTU SignalP-4.1服务
3. **VaxiJen**：预测蛋白质抗原性，判断蛋白质是否具有抗原特性
4. **ToxinPred**：预测蛋白质毒性，评估蛋白质是否具有毒素特征
5. **PhysChemParameter**：全面分析蛋白质物理化学性质，包括氨基酸组成、等电点、稳定性指数、消光系数和半衰期等


## 技术栈

- **后端**：Flask, SQLAlchemy, Flask-JWT-Extended, Flask-Mail, Flask-Migrate
- **前端**：HTML, CSS, JavaScript
- **数据库**：SQLite (开发), MySQL/PostgreSQL (生产)
- **部署**：Gunicorn, Nginx, Supervisor
- **其他**：BeautifulSoup4, Pillow, Python-dotenv

## 贡献指南

我们欢迎各种形式的贡献，包括但不限于：

- 报告问题
- 提交功能请求
- 提交代码修复
- 添加新功能
- 改进文档

## 许可证

本项目采用MIT许可证。详情请查看[LICENSE](LICENSE)文件。

项目中使用的第三方库受其各自许可证的保护，详情请查看[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)文件。

## 联系方式

如有任何问题或建议，请联系：
- **项目维护者**：BioInfo Nexus团队
- **问题反馈**：请在项目仓库中提交Issue
- **功能建议**：欢迎通过Pull Request贡献代码