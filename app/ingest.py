
import os
import git

REPO_DIR = "repos"

def clone_repo(repo_url: str):
    repo_name = repo_url.split("/")[-1]
    repo_path = os.path.join(REPO_DIR, repo_name)

    if not os.path.exists(repo_path):
        git.Repo.clone_from(repo_url, repo_path)

    return repo_path


def load_code_files(repo_path):
    code_chunks = []

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith((".py", ".js", ".ts", ".java", ".cpp")):
                path = os.path.join(root, file)

                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                code_chunks.append({
                    "file": path,
                    "content": content
                })

    return code_chunks


if __name__ == "__main__":
    repo_url = "https://github.com/SanketJadhav7d3/ParkourGame"

    repo_path = clone_repo(repo_url)

    code_chunks = load_code_files(repo_path)

    print(code_chunks)