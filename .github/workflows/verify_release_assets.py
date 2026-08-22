name: Verify 2017 Release Assets

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  verify-release-assets:
    runs-on: ubuntu-latest

    steps:
      - name: Verify GitHub release assets
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          python - <<'PY'
          import json
          import os
          import urllib.request

          owner = "myswingbtsttrading"
          repo = "nifty-options-btst"
          tag = "data-2017-v1"

          api_url = (
              f"https://api.github.com/repos/"
              f"{owner}/{repo}/releases/tags/{tag}"
          )

          request = urllib.request.Request(
              api_url,
              headers={
                  "Accept": "application/vnd.github+json",
                  "Authorization": (
                      f"Bearer {os.environ['GH_TOKEN']}"
                  ),
                  "User-Agent": "nifty-options-btst",
              },
          )

          with urllib.request.urlopen(request) as response:
              release = json.loads(
                  response.read().decode("utf-8")
              )

          print("Release verification")
          print("====================")
          print(f"Tag: {release.get('tag_name')}")
          print(f"Name: {release.get('name')}")
          print(f"Release ID: {release.get('id')}")

          assets_url = release.get("assets_url")

          if not assets_url:
              raise SystemExit(
                  "ERROR: Release has no assets_url."
              )

          assets_request = urllib.request.Request(
              assets_url,
              headers={
                  "Accept": "application/vnd.github+json",
                  "Authorization": (
                      f"Bearer {os.environ['GH_TOKEN']}"
                  ),
                  "User-Agent": "nifty-options-btst",
              },
          )

          with urllib.request.urlopen(
              assets_request
          ) as response:
              assets = json.loads(
                  response.read().decode("utf-8")
              )

          print()
          print(f"API asset count: {len(assets)}")
          print()

          for asset in assets:
              print(
                  f"- {asset.get('name')} "
                  f"| size={asset.get('size')} "
                  f"| id={asset.get('id')} "
                  f"| state={asset.get('state')}"
              )

          expected = {
              "NiftyOptions 2017.zip",
              "NiftyOptions 2017091.zip",
          }

          actual = {
              asset.get("name")
              for asset in assets
          }

          missing = expected - actual

          if missing:
              raise SystemExit(
                  "ERROR: Missing release assets: "
                  + ", ".join(sorted(missing))
              )

          print()
          print("STATUS: PASS")
          print("Both required release assets are visible")
          print("through the GitHub release-assets API.")
          PY