# Routine Blocknet desktop wallet updates

Checked October 27, 2026 (EDT). The owner approved the recommendation and publication with “proceed”. One translation agent handles 13 locales; the parent handles English and six locales. Translations remain draft for optional linguistic review. No rented hardware, mining benchmark or real wallet is used.

## Intent

Replace the existing desktop application and verify the same receiving destination and synchronized history afterward. Desktop setup owns creating/opening; backup/restore owns recovery and moving computers; sync diagnosis owns a stale balance; Faraday owns the announced future migration. This guide links those procedures rather than replicating recovery commands or migration speculation. Search demand is inferred from ordinary maintenance, not measured queries.

## Primary evidence

- Latest GUI release verified through GitHub REST and the public release page: https://github.com/blocknetprivacy/blocknet-gui/releases/tag/v0.22.0, source `661fff98e047f395489a0d2eba88f572c2a89935`. Released October 15, 2026 at 10:11:06 PM EDT. The release assets include Windows amd64 EXE, Apple Silicon DMG, Intel macOS app.zip, Linux amd64 AppImage/DEB/Flatpak/RPM and SHA256SUMS.txt. The actual asset list takes precedence over the older example filenames in README.
- Pinned `main.js:5809` and `src-tauri/src/lib.rs:1176`: get_app_version uses package_info.version; index.html:122 renders it on the opening screen. `main.js:869` and Rust:1135–1173: both About labels return daemon_version_string. No claim that Wallet Version independently measures the GUI version.
- Rust:1264–1291: tray Quit stops API events and daemon before exit. Rust:1348–1361: macOS CloseRequested prevents close and hides; other desktop platforms stop events/daemon. Therefore the cross-platform instruction uses tray/menu-bar Quit.
- Rust:238–269: app_data_dir holds named wallets and active_wallet selection, with blockchain data in its data child. Routine application replacement retains that data. No automatic conversion or universal installer-retention guarantee is claimed: readers explicitly preserve saved data and follow release notes.
- Rust:1099–1132, index.html:600–617, main.js:4615: Backup Wallet File copies the active wallet to a user-selected destination using native save dialog. Existing source and interface identify it as an encrypted .dat file; its password is still needed. Each active wallet is backed up separately.
- https://github.com/blocknetprivacy/blocknet-gui/blob/v0.22.0/README.md: official download, package installation and SHA-256 verification. Versioned package names in README are examples from an older release; article uses generic package directions and actual v0.22.0 asset formats. It does not tell readers to bypass antivirus or disable security software.
- GUI main.js:1022–1165, 1313–1447, 1515–1610: synchronization, scan progress, spendable/pending/total, receiving address and transaction history. Existing backup/restore research pins CLI v1.2.0 and core v0.22.0 for same-address recovery verification.
- Existing wallet/node/miner research and released seine v0.2.39 docs establish that separate pool mining takes a public payout address and can continue with the recipient wallet closed. Direct mining depends on its upstream node. No miner installation, new performance or payout-rate claim is added.

## Download verification

Downloaded the official Windows v0.22.0 installer and SHA256SUMS.txt through release asset URLs, calculated the installer SHA-256 locally and matched the exact filename entry. Retain the result in the showcase’s download-verification.json. The installer was not executed; this verifies download integrity, not native installation or an operating-system upgrade. macOS/Linux update directions are source-based.

## Visual evidence

Actual pinned released GUI frontend, served locally with deterministic demo responses and a visible DEMO DATA banner. main.js, styles.css, loader.js and qr.js are unchanged. CSP blocks network connections; sound and desktop notifications are disabled. No real keys, funds, signing, broadcast, installation or native backup execution. Version screenshot shows the existing-wallet unlock screen; Settings screenshot shows the real backup control. Dashboard image is reused from the first-BNT article and depicts a labeled illustrative 1.25 BNT. Article screenshots cover desktop/mobile, language selector open/closed and representative long/RTL/Greek/Thai layouts. The static document does not introduce loading/error/disabled app states.

Stable showcase: http://localhost:8874/wallet-update/. GUI source hashes, source translations and verification reports are retained there.

## Incoming links

Related-reading links from desktop wallet, backup/restore and synchronization troubleshooting point here in all 20 languages. Only related arrays and corresponding translation hashes change in those existing articles; replaced links remain in their bodies. The new article also appears in every blog index under getting started.

## Additional release drift check

The prepublication live seine check detected v0.2.41, replacing the previously reviewed v0.2.39. All four protected source files are byte-identical and the five archive names are unchanged. CPU kernel/tuning/Linux startup improvements do not change the wallet instructions. Reviewed the mining, NVIDIA, Linux and antivirus guides: retain their dated examples and measured historical results. Updated the Seine release manifest and pool release manifest to the verified tag; the pool calculator consumes only the unchanged fee value, so generated calculator behavior is unchanged and this metadata correction does not require restarting pool services. See miner-release-verification.json in the showcase.

Overlap report: 0.3% shared eight-word phrases with desktop wallet and 0.2% with first-BNT. The distinct routine-update intent was checked separately.
