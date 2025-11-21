# GitHub 发布指南

本指南将帮助你将这个项目发布到 GitHub 上。

## 📋 发布前检查清单

- [x] ✅ `.gitignore` 已更新，排除敏感文件和临时文件
- [x] ✅ `.env.example` 已创建，作为配置模板
- [x] ✅ `README.md` 已更新，包含完整的项目说明
- [x] ✅ `LICENSE` 文件已创建
- [ ] ⚠️ 检查是否有 `.env` 文件（不应提交）
- [ ] ⚠️ 检查是否有敏感信息（密码、密钥等）
- [ ] ⚠️ 检查备份目录是否已排除

## 🚀 发布步骤

### 1. 在 GitHub 上创建新仓库

1. 登录 GitHub
2. 点击右上角的 "+" 按钮，选择 "New repository"
3. 填写仓库信息：
   - **Repository name**: `accounting-system`（或你喜欢的名字）
   - **Description**: `一个基于 FastAPI 的简易财务记账系统`
   - **Visibility**: 选择 Public（公开）或 Private（私有）
   - **不要**勾选 "Initialize this repository with a README"（因为我们已经有了）
4. 点击 "Create repository"

### 2. 初始化本地 Git 仓库（如果还没有）

如果项目还没有初始化为 Git 仓库，执行以下命令：

```bash
# 进入项目目录
cd D:\1

# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 提交初始版本
git commit -m "Initial commit: 财务记账系统"
```

### 3. 连接到 GitHub 仓库

```bash
# 添加远程仓库（将 YOUR_USERNAME 替换为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/accounting-system.git

# 或者使用 SSH（如果你配置了 SSH 密钥）
# git remote add origin git@github.com:YOUR_USERNAME/accounting-system.git

# 验证远程仓库
git remote -v
```

### 4. 推送代码到 GitHub

```bash
# 推送主分支到 GitHub
git branch -M main
git push -u origin main
```

如果遇到认证问题，你可能需要：
- 使用 Personal Access Token（推荐）
- 或者配置 SSH 密钥

### 5. 验证发布

1. 访问你的 GitHub 仓库页面
2. 检查以下内容：
   - README.md 是否正确显示
   - 文件结构是否完整
   - `.env` 文件是否**没有**被提交（应该在 .gitignore 中）
   - 备份目录是否**没有**被提交

## 🔒 安全检查

### 检查敏感文件

在推送前，确保以下文件**没有被提交**：

```bash
# 检查是否有 .env 文件被跟踪
git ls-files | grep .env

# 如果输出为空，说明 .env 没有被跟踪（正确）
# 如果有输出，执行以下命令移除：
# git rm --cached .env
```

### 检查备份目录

```bash
# 检查备份目录是否被跟踪
git ls-files | grep backup

# 如果备份目录被跟踪，需要从 Git 中移除：
# git rm -r --cached backup_original/
```

## 📝 后续维护

### 添加新功能后提交

```bash
# 查看更改
git status

# 添加更改的文件
git add .

# 提交更改
git commit -m "描述你的更改"

# 推送到 GitHub
git push
```

### 创建 Release（可选）

1. 在 GitHub 仓库页面，点击 "Releases"
2. 点击 "Create a new release"
3. 填写版本信息：
   - **Tag version**: `v0.1.0`
   - **Release title**: `v0.1.0 - 初始版本`
   - **Description**: 描述这个版本的功能
4. 点击 "Publish release"

## 🎨 美化仓库（可选）

### 添加仓库主题标签

在 README.md 顶部添加徽章（可选）：

```markdown
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
```

### 添加项目截图

如果有截图，可以：
1. 创建 `docs/images/` 目录
2. 将截图放入该目录
3. 在 README.md 中引用截图

## ⚠️ 常见问题

### 问题：推送时提示认证失败

**解决方案**：
1. 使用 Personal Access Token 代替密码
2. 或者配置 SSH 密钥

### 问题：.env 文件被意外提交

**解决方案**：
```bash
# 从 Git 中移除 .env 文件（但保留本地文件）
git rm --cached .env

# 提交更改
git commit -m "Remove .env from repository"

# 推送到 GitHub
git push
```

### 问题：想忽略已提交的文件

**解决方案**：
```bash
# 从 Git 中移除文件（但保留本地文件）
git rm --cached <文件名>

# 确保 .gitignore 中包含该文件
# 然后提交更改
git commit -m "Remove sensitive files"
git push
```

## 📚 有用的 Git 命令

```bash
# 查看状态
git status

# 查看提交历史
git log --oneline

# 查看远程仓库
git remote -v

# 拉取最新更改
git pull

# 创建新分支
git checkout -b feature/new-feature

# 切换分支
git checkout main

# 合并分支
git merge feature/new-feature
```

## 🎉 完成！

现在你的项目已经成功发布到 GitHub 了！其他人可以通过以下方式使用你的项目：

```bash
git clone https://github.com/YOUR_USERNAME/accounting-system.git
cd accounting-system
```

祝你发布顺利！🚀

