#!/usr/bin/env python3
import json
import os
import re

PACKAGE_JSON_FILE = "package.json"
VERSION_FILE = "VERSION"
PACKAGE_JSON_FILE_EXISTS = False

# Function definitions
def get_latest_development_branch():
    os.system("git stash && git checkout development && git pull")


def get_merge_request_url():
    remotes = os.popen("git remote -v").read().split("\n")

    # Get <group>/<project-name> for merge request url
    # For example, 'peerlogictech/peerlogic-callpop-app'
    github_group_and_project = re.compile(r"(?<=git@github.com:)(.*)(?=.git)")
    github_group_and_project = github_group_and_project.search(remotes[0])

    if github_group_and_project is None:
        raise Exception(f"Git remote {remotes[0]} does not match expected pattern! Could not determine github_project!")

    github_group_and_project = github_group_and_project.group()
    return f"https://github.com/{github_group_and_project}/compare/main...release/{NEW_VERSION}?expand=1"


def update_version_in_files():
    global PACKAGE_JSON_FILE_EXISTS
    print("Updating VERSION file...")
    with open(VERSION_FILE, "w") as f:
        f.write(f"{NEW_VERSION}")
    print("Done updating VERSION file!")
    print("Updating package.json file...")
    try:
        with open(PACKAGE_JSON_FILE, "r") as f:
            data = json.load(f)
        PACKAGE_JSON_FILE_EXISTS = True
        data["version"] = NEW_VERSION
        with open(PACKAGE_JSON_FILE, "w") as f:
            json.dump(data, f, indent=2)
            print("Done updating package.json file!")
    except FileNotFoundError:
        print("No package.json to update. Skipping!")


def commit_updates():
    os.system(f"git add {VERSION_FILE}")
    if PACKAGE_JSON_FILE_EXISTS:
        os.system(f"git add {PACKAGE_JSON_FILE}")
    is_ok = input("Commit the above to development and subsequently cut release? (yes) ") or "yes"
    if is_ok != "yes":
        print("Cancelling.")
        exit(1)
    os.system(f'git commit -m "Updated version to {NEW_VERSION}."')
    os.system(f"git push")


def tag_commit_and_push_tag():
    os.system(f"git tag v{NEW_VERSION}")
    os.system(f"git push origin v{NEW_VERSION}")


def create_release_branch():
    os.system(f"git checkout -b release/{NEW_VERSION}")
    os.system(f"git push -u origin release/{NEW_VERSION}")


def create_merge_request():
    open_pr = input("Create merge request? (yes) ") or "yes"
    if open_pr:
        mr_url = get_merge_request_url()
        os.system(f'open "{mr_url}"')


# Start of main release script
get_latest_development_branch()

# Read current and new versions
with open(VERSION_FILE, "r") as f:
    CURRENT_VERSION = f.read().strip()
NEW_VERSION = input(f"What version are we releasing? ({CURRENT_VERSION}) ") or CURRENT_VERSION


if NEW_VERSION.strip() == CURRENT_VERSION:
    # No need to update any files, just tag release
    tag_commit_and_push_tag()

if NEW_VERSION.strip() != CURRENT_VERSION:
    update_version_in_files()
    commit_updates()
    tag_commit_and_push_tag()
    create_release_branch()
    create_merge_request()
