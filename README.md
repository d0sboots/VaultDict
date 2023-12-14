# VaultDict
Spoiler-Free Dictionary for Heaven's Vault

The dictionary never went anywhere, so there are two *actual* useful things in this repo: An updated ancientrunes font and a json-parsing tool.

The ancientrunes font is stored as a FontForge project, a WOFF file and a WOFF2 file. It is directly traced from the shapes in the game; the glyphs should have accurate sizes and spacing.

`parse_json.py` is a parser for the game data that outputs a wikitable. You can use it as a starting point for your own explorations into the game files. To use it, you need to extract two files from the Unity bundle: `GameData.json` and `core.json`. Use a program like AssetBundleExtractor for this.
