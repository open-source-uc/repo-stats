"Get the readme and the last 100 PRs and Forks of a repository"

import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from httpx import Client
from pydantic import BaseModel, BaseSettings


# Env variables
class Settings(BaseSettings):
    # Personal access token for the GitHub API
    pat: str
    # Repository
    owner: str
    repo: str
    # Readme blob
    blob = "main:readme.md"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# User data
class User(BaseModel):
    pr = False
    pr_at: datetime | None = None
    fork = False
    fork_at: datetime | None = None
    readme = False


# Setup
settings = Settings()  # type: ignore
query = Path("query.graphql").read_text()
variables = {"owner": settings.owner, "repo": settings.repo, "blob": settings.blob}
users: dict[str, User] = defaultdict(User)
client = Client(
    base_url="https://api.github.com",
    headers={"Authorization": f"Bearer {settings.pat}"},
)

# Query
response = client.post("/graphql", json={"query": query, "variables": variables})
data = response.json().get("data")


# Save PR info
for pr in data["repository"]["pullRequests"]["nodes"]:
    user_id = pr["author"]["login"]
    users[user_id].pr = True
    users[user_id].pr_at = datetime.fromisoformat(
        pr["createdAt"].replace("Z", "+00:00")
    ).astimezone(ZoneInfo("America/Santiago"))


# Save Fork info
for fork in data["repository"]["forks"]["nodes"]:
    user_id = fork["owner"]["login"]
    users[user_id].fork = True
    users[user_id].fork_at = datetime.fromisoformat(
        fork["createdAt"].replace("Z", "+00:00")
    ).astimezone(ZoneInfo("America/Santiago"))


# Match markdown links in a list
md = data["repository"]["object"]["text"]
for match in re.findall(r"- \[@?(.*)\]\((.*)\)", md):
    users[match[0]].readme = True


# Create a CSV file with the users
keys = ["login", "pr", "pr_at", "fork_not_deleted", "fork_at", "in_readme"]
with Path("out.csv").open("w", newline="") as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(keys)
    for login, user in users.items():
        row = [login, user.pr, user.pr_at, user.fork, user.fork_at, user.readme]
        writer.writerow(row)
