# Windows startup and multiple computers — October 26, 2026

## Intent and authorization

The owner approved these two articles, English plus 19 translations, canonical
publication and the pool API-only deployment. No separate linguistic reviewer is
required. Translations remain `draft`; the active model wrote all locales without
subagents or external translation services. No hardware rental or mining run.

- `start-miner-automatically-windows`: configure and verify Windows sign-in startup
  for a working miner. Windows installation, Linux systemd and release replacement
  remain owned by their existing articles.
- `mine-multiple-computers-one-wallet`: add a second computer, identify its shares
  and resolve duplicate rig names. First connection, dashboard field definitions
  and PPLNS allocation remain owned by their existing guides.

## Primary evidence

Latest public Seine release checked through GitHub API: v0.2.36, published
October 26, 2026 at 11:34:54 AM EDT. Release commit:
`f3c8175eac0e01cd31870372b2c4989a598044d3`.

- `seine@v0.2.36:docs/MINER_FLAGS.md`: separate address and pool-worker arguments;
  default data directory `./seine-data`; UI auto selection; backend selection.
- `seine@v0.2.36:src/config.rs:858–910,2445–2483`: initial connection settings are
  persisted in seine.config.json. CLI overrides on an existing configuration do
  not rewrite the saved name. Retain an explicit name in future launch commands.
- Existing release archives and Windows setup require keeping the extracted
  package together. Absolute data directory and explicit working directory avoid
  depending on a scheduler's default working directory. No wallet secrets needed.
- https://learn.microsoft.com/en-us/windows/win32/taskschd/starting-an-executable-when-a-user-logs-on
  A selected-user logon trigger is distinct from boot or workstation unlock.
- https://learn.microsoft.com/en-us/windows/win32/taskschd/execaction-workingdirectory
  The executable action defines its working directory separately from arguments.
- https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-multipleinstances
  Ignore-new applies to instances of the same task, not unrelated manual processes.
- https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-executiontimelimit
  Execution time limit can be disabled for ongoing work. No system-wide sleep or
  power policy changes, elevation, credential storage or background service setup.
- Task disabling prevents future launches; an existing process needs a separate
  normal stop. Guide calls for sign-out/sign-in after saving other work.
- `blocknet-pool@2129bfdc3e790e675154ace236c26c3c09d2e34f:crates/pool-common/src/protocol.rs:79–94`:
  worker normalization removes controls, trims whitespace and retains 64 chars.
- Same pool revision, `crates/pool-runtime/src/stratum.rs:1015–1055`: login resolves
  the receiving identity and records address plus normalized worker name.
- `crates/pool-runtime/src/pgdb.rs:5858–5905`: per-address worker history aggregates
  by worker. Same address/name combines history; rename does not rewrite old shares.
- `crates/pool-runtime/src/stats.rs:122–135`: connection identities and distinct
  address/name pairs are different counts. Do not infer hardware count from them.
- Existing PPLNS and wallet guides: accounting and payouts use the resolved address;
  changing an ID does not transfer previously earned balances. Hardware and uptime
  affect actual submitted work, not fixed rewards per machine or label.

## Art and verification scope

Original language-neutral diagrams show sign-in → scheduled task → miner → accepted
work, and separately numbered computers → pool → receiving wallet. Explanatory
illustrations, not screenshots of Task Scheduler or measured reward results.
The article list layouts are retained. Related links from two existing owners on
each site inherit localization in all 20 languages; source hashes are refreshed.

Automated checks cover source/translation structure, commands, inline literals,
links and metadata. Browser verification covers real rendered pages, desktop,
mobile, Arabic, Greek, Thai, diagrams, commands and list thumbnails. Task Scheduler
was not installed or executed on the user's machine and no mining was started.
The Windows procedure is source/documentation-verified, not a claimed runtime E2E.

Stable verification showcase:
http://localhost:8874/windows-startup-and-multiple-miners/

Mobile QA found long Windows paths in list items extending beyond the page.
Inline article code now forms a bounded left-to-right box and can wrap at any
character; preformatted command blocks retain their horizontal scrolling.
