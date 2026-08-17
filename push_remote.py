"""
一键推送脚本 - 将项目推送到 GitHub 或 Gitee
使用方法: python push_remote.py
"""

import subprocess
import sys
import os
import urllib.request
import urllib.error
import json

GIT_PATH = r"C:\Program Files\Git\cmd\git.exe"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_NAME = "db-query-tool"
REPO_DESC = "智能数据库查询工具 v2.0 - 数据导出功能(CSV/JSON) + AI Agent自动化"


def run_git(*args):
    """执行 git 命令"""
    cmd = [GIT_PATH] + list(args)
    result = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, text=True)
    if result.returncode != 0 and result.stderr:
        print(f"  [git] {result.stderr.strip()}")
    return result.returncode == 0, result.stdout.strip()


def create_github_repo(username, token):
    """通过 GitHub API 创建新仓库"""
    url = "https://api.github.com/user/repos"
    data = json.dumps({
        "name": REPO_NAME,
        "description": REPO_DESC,
        "private": False,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return True, result.get("html_url", "")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        if e.code == 422:
            # 仓库已存在
            return True, f"https://github.com/{username}/{REPO_NAME}"
        print(f"  [错误] GitHub API 返回 {e.code}: {error_body}")
        return False, ""
    except Exception as e:
        print(f"  [错误] {e}")
        return False, ""


def create_gitee_repo(username, token):
    """通过 Gitee API 创建新仓库"""
    url = "https://gitee.com/api/v5/user/repos"
    data = json.dumps({
        "access_token": token,
        "name": REPO_NAME,
        "description": REPO_DESC,
        "private": False,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return True, result.get("html_url", "")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        if "already" in error_body.lower() or "exist" in error_body.lower():
            return True, f"https://gitee.com/{username}/{REPO_NAME}"
        print(f"  [错误] Gitee API 返回 {e.code}: {error_body}")
        return False, ""
    except Exception as e:
        print(f"  [错误] {e}")
        return False, ""


def push_to_remote(platform, username, token):
    """推送代码到远程仓库"""
    if platform == "github":
        print("\n  [1/3] 正在通过 GitHub API 创建仓库...")
        success, repo_url = create_github_repo(username, token)
        remote_url = f"https://{username}:{token}@github.com/{username}/{REPO_NAME}.git"
        public_url = f"https://github.com/{username}/{REPO_NAME}"
    else:
        print("\n  [1/3] 正在通过 Gitee API 创建仓库...")
        success, repo_url = create_gitee_repo(username, token)
        remote_url = f"https://{username}:{token}@gitee.com/{username}/{REPO_NAME}.git"
        public_url = f"https://gitee.com/{username}/{REPO_NAME}"

    if not success:
        print("  仓库创建失败，请检查用户名和 Token 是否正确。")
        return False

    print(f"  仓库地址: {public_url}")

    # 添加远程仓库
    print("\n  [2/3] 添加远程仓库...")
    run_git("remote", "remove", "origin")
    ok, _ = run_git("remote", "add", "origin", remote_url)
    if not ok:
        # 尝试 set-url
        run_git("remote", "set-url", "origin", remote_url)

    # 推送代码
    print("\n  [3/3] 推送代码到远程仓库...")
    ok, output = run_git("push", "-u", "origin", "master")
    if ok:
        print(f"\n  推送成功!")
        print(f"  仓库链接: {public_url}")
        return True
    else:
        # 尝试 main 分支
        run_git("branch", "-M", "main")
        ok, output = run_git("push", "-u", "origin", "main")
        if ok:
            print(f"\n  推送成功!")
            print(f"  仓库链接: {public_url}")
            return True
        else:
            print(f"\n  推送失败，请检查网络和凭据。")
            return False


def main():
    print("""
  ╔══════════════════════════════════════════╗
  ║     一键推送到 GitHub / Gitee            ║
  ╚══════════════════════════════════════════╝
    """)

    print("  选择推送平台:")
    print("    1. GitHub (github.com)")
    print("    2. Gitee  (gitee.com)")
    choice = input("\n  请输入 1 或 2: ").strip()

    if choice == "1":
        platform = "github"
        print("\n  --- GitHub 推送 ---")
        print("  需要提供 GitHub Personal Access Token")
        print("  获取方式: GitHub → Settings → Developer settings → Personal access tokens → Generate new token")
        print("  勾选 repo 权限即可\n")
    elif choice == "2":
        platform = "gitee"
        print("\n  --- Gitee 推送 ---")
        print("  需要提供 Gitee 私人令牌")
        print("  获取方式: Gitee → 设置 → 私人令牌 → 生成新令牌")
        print("  勾选 projects 权限即可\n")
    else:
        print("  无效选择")
        return

    username = input("  请输入你的用户名: ").strip()
    token = input("  请输入你的 Personal Access Token: ").strip()

    if not username or not token:
        print("  用户名和 Token 不能为空!")
        return

    print(f"\n  平台: {platform}")
    print(f"  用户名: {username}")
    print(f"  仓库名: {REPO_NAME}")
    confirm = input("\n  确认推送? (y/n): ").strip().lower()
    if confirm != "y":
        print("  已取消")
        return

    push_to_remote(platform, username, token)


if __name__ == "__main__":
    main()
