# Disclaimer and GPT Authorship Disclosure

Applies to: Deadlock Native Camera Repair Tool  
Document date: October 17, 2026

## AI authorship

The custom Python, C#, PowerShell and batch scripts, together with the documentation, were primarily **generated and iteratively revised by OpenAI GPT through Codex in response to the publisher's requests**. Bundled third-party libraries, including ValveResourceFormat, were developed by their respective maintainers, not by GPT.

AI-generated code may contain errors, omissions and unhandled cases. The tool has undergone limited local file checks and operational tests, and the publisher reports that it works in their own environment. These results are not a comprehensive audit or a guarantee of effectiveness on other computers, mods, game modes or future versions.

## Unofficial status and account risks

This is an independent community tool. It is not officially approved, endorsed or supported by Valve, Steam, Deadlock, OpenAI or the relevant mod authors. References to GPT, Codex and third-party projects identify the development process and dependencies; they do not imply responsibility from those organizations.

**The tool is not guaranteed to be ban-safe or compliant with all current or future Valve rules. No explicit permission from Valve for its use in online play has been obtained at publication.**

As currently implemented, the tool edits camera data in mod VPK files while the game is closed and maintains a startup configuration block. It does not inject code into the game process, modify game executables or game DLLs, or bypass anti-cheat. These characteristics do not establish official permission or eliminate the possibility of account bans, matchmaking restrictions, integrity errors or other penalties.

Users should review and comply with applicable Steam, Deadlock and server rules. If account risk is unacceptable, disable third-party modifications and use the original game without mods loaded. Sandbox testing checks functionality; it does not provide an anti-cheat exemption.

## Functionality, compatibility and backups

The tool attempts to restore supported mods' camera settings from the user's currently installed original hero assets. It cannot guarantee a fix for every camera problem. Missing or incompatible bones, custom paths, external meshes, special abilities, model occlusion and game updates may cause skipped models, failures or unexpected behavior.

“Universal” means that one tool can batch-process supported mods for different heroes. It does not mean that every mod is supported or that repairs remain effective permanently. Game or mod-manager updates may overwrite repaired files.

Read the instructions, keep an independent backup, and close the game and mod manager before use. Automatic backups, verification and rollback cannot guarantee recovery after power loss, disk failure, concurrent file changes or other exceptional conditions.

## Warranties and liability

To the maximum extent permitted by applicable law, the tool is provided “as is” and “as available,” without warranties of merchantability, fitness for a particular purpose, non-infringement, continued compatibility or error-free operation. To that extent, the publisher and contributors disclaim liability for file or data loss, game problems, account penalties, service interruptions or other losses resulting from using or being unable to use the tool.

Nothing in this statement excludes or limits rights or liability that cannot legally be excluded or limited. It does not change the terms or rights of Valve, OpenAI or other rights holders. AI authorship does not replace the publisher's responsibility to review what they distribute.

## Third-party materials and distribution

Keep `ThirdPartyNotices.txt`, the licenses in `licenses/`, and associated copyright notices. Third-party libraries remain subject to their own licenses. This statement does not replace those licenses or separately grant rights to use or redistribute game or mod assets.

Public distributions should contain the tool and necessary dependencies, not unauthorized game assets, other authors' complete mods, repaired VPKs or runtime backups. `runs/` may contain models, complete mod copies, usernames and local paths. Review and redact personal information before sharing logs.

References: [Steam's official VAC information](https://help.steampowered.com/en/faqs/view/571A-97DA-70E9-FF74) and the [Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/). Consult the latest official rules.

The Chinese and English versions are intended to convey the same meaning. Ask the publisher to clarify any discrepancy; a discrepancy should not be interpreted as additional permission or a warranty.
