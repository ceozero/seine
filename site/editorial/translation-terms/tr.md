# Turkish (tr) shared terms

Siz form (formal), like src/i18n/messages/tr.json ("seine'i indirin", "bilgisayarınız"). One line per term: `English -> rendering`. Append, don't rewrite others' lines.

mining / miner -> madencilik / madenci (the program: madenci yazılımı, "seine madencisi")
mine (verb) -> madencilik yapmak; "Blocknet madenciliği yapmak", "Blocknet kazmak" avoided
mining pool -> madencilik havuzu (havuz)
hashrate -> hashrate (hash gücü on first mention where natural); tr.json uses "hashrate"
thread (CPU) -> iş parçacığı (thread); plural iş parçacıkları; never "worker"
kernel (CPU code path) -> kernel (kernel'ler, kernel'ini) as in tr.json
core (CPU) -> çekirdek
share / accepted share -> share (kabul edilen share'ler)
block / block reward -> blok / blok ödülü
payout -> ödeme
privacy coin -> gizlilik coini (gizlilik coin'leri) as in tr.json
private -> gizli / gizlilik odaklı (never anonim / izlenemez / takip edilemez)
ring signature -> halka imza
stealth address -> gizli adres (stealth address)
seed / recovery phrase -> seed ifadesi / kurtarma ifadesi
huge pages -> huge pages (büyük sayfalar on first mention)
Windows large pages -> Windows'ta large pages
commitment -> taahhüt (commitment)
range proof -> aralık kanıtı (range proof)
view key / spend key -> görüntüleme anahtarı (view key) / harcama anahtarı (spend key)
key image -> anahtar görüntüsü (key image)
decoy -> sahte girdi (decoy)
output / input -> çıktı / girdi
confirmation -> onay
difficulty -> zorluk (difficulty)
memory-hard -> bellek yoğun (memory-hard)
proof of work / proof of stake -> iş kanıtı (Proof of Work) / hisse kanıtı (Proof of Stake); PoW / PoS
daemon -> daemon
node -> düğüm (node) as in tr.json
dashboard -> panel as in tr.json
@name / shortname -> @name / kısa ad
wallet -> cüzdan
solo mining -> solo madencilik
rig -> rig (rig'ler)
worker name (pool) -> worker adı
transaction fee -> işlem ücreti
fair launch -> adil başlangıç (fair launch)
tag: Mining guide / Mining / CPU mining -> Madencilik rehberi / Madencilik / CPU madenciliği
tag: Huge pages / Performance / Servers / Laptop / Hardware -> Huge pages / Performans / Sunucular / Dizüstü / Donanım
tag: Privacy / Privacy coins / Ring signatures / Stealth addresses -> Gizlilik / Gizlilik coinleri / Halka imzalar / Gizli adresler
tag: Cryptography / Security / Wallet / Seed phrase -> Kriptografi / Güvenlik / Cüzdan / Seed ifadesi
tag: Proof of work / Proof of stake / Consensus / Dashboard / Auto-tuning -> İş kanıtı / Hisse kanıtı / Konsensüs / Panel / Otomatik ayar
numbers in prose -> 6.000 BNT, 16,8 GiB, 0,1 BNT, %5 (percent sign before the number); code, inline code, commands stay byte-identical
suffixes on names -> apostrophe + vowel harmony: seine'i / seine'in / seine'de / seine'e (front vowels, matching tr.json "seine'i indirin"); Blocknet'i / Blocknet'in / Blocknet'te; bntpool.com'da / bntpool.com'u; Linux'ta, macOS'ta, Windows'ta, NVIDIA GPU'lar, CPU'nuz
one-time address -> tek kullanımlık adres
Pedersen commitment / blinding factor -> Pedersen taahhüdü / körleme faktörü (blinding factor)
trusted setup -> güvenilir kurulum (trusted setup)
stem / fluff (Dandelion++) -> stem (gövde) aşaması / fluff (yayılma) aşaması
memo / encrypted memo -> memo / şifreli memo (memo'lar)
pay by name -> isimle ödeme
payment link -> ödeme bağlantısı
payout address -> ödeme adresi
memory bandwidth -> bellek bant genişliği
arena (2 GiB Argon2id block) -> 2 GiB'lık bellek bloğu
tag: Payments / Payment links / Memos / Networking -> Ödemeler / Ödeme bağlantıları / Memo'lar / Ağ
recovery seed (wallet UI) -> kurtarma ifadesi (12 kelime); bare "seed" -> seed
arena, where the post also talks about Argon2id's 1 KiB blocks (huge pages, servers, dashboard) -> 2 GiB'lık bellek alanı (alan), so it doesn't clash with "blok"
TLB miss -> TLB ıskalaması
page mode / reserved pages -> sayfa modu / ayrılmış sayfalar
Lock pages in memory (Windows right) -> Bellekteki sayfaları kilitle (Lock pages in memory); Yerel İlkeler → Kullanıcı Hakları Ataması
macOS UI -> Sistem Ayarları → Gizlilik ve Güvenlik; Uygulamalar → İzlenceler; Return tuşu
headless -> terminalsiz (çalıştırma)
control API / endpoint / bearer token -> kontrol API'si / uç nokta / bearer token
service manager / systemd unit -> hizmet yöneticisi / systemd birimi
NUMA node / L3 cache group / SMT sibling -> NUMA düğümü / L3 önbellek grubu / SMT kardeşi
affinity / placement / pin -> yerleşim / sabitlemek
dashboard UI labels (Current, Average, Threads, Submitted, Pending...) -> keep English in bold/backticks, explain in Turkish
validator / staking / slashing -> validatör / stake etmek, staking / slashing (cezası)
reorganization -> yeniden düzenleme (reorg)
target (PoW) -> hedef değer
key image -> anahtar görüntüsü (key image); linkable ring signature -> bağlanabilir halka imza
private key / public key -> özel anahtar / açık anahtar
view-only / watch-only wallet -> yalnızca görüntüleme amaçlı cüzdan / yalnızca izleme amaçlı (watch-only) cüzdan
fungibility -> değiştirilebilirlik (fungibility)
block explorer -> blok gezgini
premine / genesis block / tail reward -> premine / genesis bloğu / kuyruk ödülü
checksum -> sağlama toplamı
