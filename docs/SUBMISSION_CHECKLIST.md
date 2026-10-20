# Submission checklist — OpenCV AI Competition 2026

**このファイルは提出直前の作業台。** 各項目は「この作業場で実測した事実」か「人間にしかできない手」の
どちらかで、`[x]` は再現コマンド付きの実測、`[ ]` は人間待ち。English quotes are copied from
`evidence/page.txt` / `evidence/rules.txt` with line numbers so nothing here is retyped from memory.

## 0. 締切・条件（ルールの再抽出）

| 項目 | 実測値 | 出典 |
|---|---|---|
| 締切 | `2026-10-27T02:45:00-04:00` = **2026-10-27 15:45 JST**（= 10-27 11:45pm PDT） | `evidence/page.html:661`, `:780`, `:793` |
| 提出物リスト | 7項目（下の §2） | `evidence/page.txt:162-169` |
| 年齢条件 | "Participants must be at least 13 years old. Anyone who has not reached the legal age of majority where they live must obtain permission from a parent or legal guardian and complete any required platform forms." | `evidence/rules.txt:123` |
| 賞金（現金） | 最大 $12,000（1st $5,000 / 2nd $3,000 / 3rd $2,000 / COOL $1,000 / Agentic Vision $1,000）。ページ見出しの $20,250 は現金総額ではない | `evidence/rules.txt` §Prizes |
| 審査 | Technical execution **30%** / Innovation **20%** / Real-world impact **20%** / User experience **10%** / Documentation and presentation **10%** / Cloud delivery, reproducibility, and responsible operation **10%** | `evidence/page.txt:232-244` |

作業日: 2026-10-20（このワークスペースの実測）。残り 6 日。

## 1. 今回の実測結果（すべて再実行して得た値）

### 動画 — 完成

```
docs/demo_video.mp4
duration 260.021354 s (4:20)   ← 上限 5:00 に対して 40 s の余裕
h264 High, 1280x720, yuv420p, 30/1 fps, aac LC 48 kHz (無音トラック)
17,864,159 bytes
生成: .venv/bin/python docs/make_video_slides.py && bash docs/make_video.sh
```

- 画面は 10 枚（`docs/video_frames/s01..s10*.png`）で、全枚がこのリポジトリの産物を撮ったもの:
  `docs/record_terminal.sh` の生ログ、`results/eval.json`、`src/make_evidence.py` の注釈画像。
- 字幕（telop）は `docs/video_frames/telops/*.txt`。音声ナレーションは無し（この環境に TTS が無い）。
- 動画内で「AWS は未デプロイ」と明示している（s08）。デプロイしていないのに稼働を主張する箇所は無い。

### リポジトリ束 — 完成（push は未実施）

```
git commit 98f830f3719397d5b094ced66f1fccd712a3a010  (author maebahesioru <250837564+maebahesioru@users.noreply.github.com>)
72 files, 7,291 lines added
.git = 31 MB (86 objects, size 30.56 MiB)  ← 動画 17.9 MB を含む
除外: .venv/ results/scenes/*.png docs/video_frames/build/ docs/video_src/server.log
```

### 主張の裏付け（再現コマンドと実測値）

| 主張 | コマンド | 実測 |
|---|---|---|
| テストが通る | `.venv/bin/python -m pytest -q` | `5 passed in 1.62s` |
| OpenCV 5 を使っている | `.venv/bin/python src/probe.py` | `opencv 5.0.0`, `numpy 2.5.4` |
| ループの効果 | `.venv/bin/python src/eval_harness.py --scenes 80` | 下表 |
| HTTP で同じループが動く | `uvicorn src.service:app --port 8080` ＋ `curl` | `/healthz` `{"ok":true,"opencv":"5.0.0",...}`, `/inspect/scene/2002?hard=true` = 2 step, 3/3, 151 ms |

| 条件 | P | R | F1 | tp/fp/fn | median |
|---|---|---|---|---|---|
| single-shot / degraded | 0.976 | 0.494 | 0.656 | 41/1/42 | 72.1 ms |
| agent loop / degraded | 0.920 | 0.976 | 0.947 | 81/7/2 | 218.5 ms |
| agent loop / normal | 0.975 | 0.952 | 0.963 | 79/2/4 | 67.5 ms |

## 2. 必須提出物 7 項目（`evidence/page.txt:162-169` の逐語）

| # | 要求 | 状態 | 実体 |
|---|---|---|---|
| 1 | "A technical report describing the problem, users, architecture, OpenCV 5 implementation, AWS deployment, evaluation, limitations, and responsible-use considerations." | [x] | `docs/REPORT.md`（§1–§9、AWS は「書いたが実行していない」と明記） |
| 2 | "A public or private judge-accessible code repository or archive." | [~] | ローカル束は完成。**公開ホストへの push が未実施**（下 §3-1） |
| 3 | "Pinned dependencies plus clear build, deployment, and test instructions." | [x] | `requirements.txt` 固定版、`Makefile`、README、REPORT §8 |
| 4 | "An architecture diagram showing the OpenCV 5 and AWS components and, where relevant, COOL or agent components." | [x] | `docs/ARCHITECTURE.md` §2 ＋ 動画 s07/s08 |
| 5 | "A working web endpoint or an arranged live screen-share demonstration." | [x]※ | ローカル `POST /inspect` を実測（動画 s06 に生ログ）。**公開エンドポイントは未デプロイ**なので、動画＋ローカル起動手順で代替している。AWS を出さない限りこれは「arranged screen-share」側の充足 |
| 6 | "A public or unlisted judge-accessible video of no more than five minutes that shows the team, the application working, its architecture, and its principal results." | [~] | `docs/demo_video.mp4`（4:20）完成。**YouTube 等への公開アップロードが未実施**（下 §3-2）。チームは s01/s10 のカードで表示、顔出しは任意 |
| 7 | "Evaluation evidence appropriate to the project, including failure cases or limitations." | [x] | `results/eval.json`、`results/EVAL_SUMMARY.md`、`docs/REPORT.md` §5（失敗例 4 シーンの実測トレース）、動画 s09 |

Agentic Vision Award の追加証拠（`evidence/page.txt` §Additional Evidence）も同ファイルで充足:
"An agent workflow diagram" = `docs/ARCHITECTURE.md` §2、\"A trace or demonstration showing that OpenCV 5
output changes a later decision\" = 動画 s06 の `step 1 raise_exposure … | mean luma 29 < 34`。

## 3. 残りは人間の手だけ（この順で、所要 約35分）

1. **public リポジトリへ push**（5分）— GitHub で空リポジトリを作り、この作業場で
   `git remote add origin git@github.com:<user>/<repo>.git && git push -u origin main`。
   公開したら URL を `docs/REPORT.md` 冒頭と `README.md` に書き、その 2 行だけ amend して再 push。
   （判定者アクセスが要件なので、private にする場合は Devpost 側で招待が必要 — public が最短）
2. **動画を YouTube へ unlisted でアップ**（10分）— `docs/demo_video.mp4` をそのまま。
   タイトル例: `PanelScan Agent — OpenCV AI Competition 2026 (4:20)`。説明欄に §2 の 7 項目と
   リポジトリ URL を貼る。限定公開でよい（ルールは "public or unlisted"）。
3. **保護者同意**（5分）— `evidence/rules.txt:123` の条文どおり、16 歳は保護者の許可と
   「required platform forms」が必要。Devpost の eligibility 質問に親の同意確認が出たら保護者と一緒に回答。
4. **Devpost プロジェクト作成→提出**（10分）— 実測済みの素材をそのまま流し込む:
   - Project name: `PanelScan Agent`
   - Elevator pitch: `An inspection loop where the camera moves because of what the pixels say.`
   - Built with: `opencv`, `python`, `fastapi`, `docker`, `aws-fargate`, `graviton`
   - Thumbnail: `evidence/scene_2011.png`（黄=GT, 赤=予測が 1 枚で読める）
   - Gallery: `evidence/scene_2002.png`, `evidence/scene_2005.png`, `evidence/scene_2011.png`
   - Video demo link: 手順 2 の URL
   - "Try it out" / repository: 手順 1 の URL
   - Additional info: `docs/REPORT.md` の冒頭 3 段落＋「AWS は deploy/ に書いたが未実行」
5. **AI 利用の開示**（2分）— ルールが求める開示欄に、AI コーディング支援と
   `--scenes 80` 評価の再現コマンドを書く（数値は AI の主張ではなく `results/eval.json` の実測）。
6. **提出ボタン**（1分）— AWS 未デプロイは 10 点分のルブリック項目であって門ではない。
   ここで止めない（`evidence/page.txt:244` が 10% と明記）。

### Devpost フォーム項目について（実測の限界）

ログインが必要なため、提出フォームの**入力欄そのものは未実測**（アカウント操作は本タスクの禁止事項）。
実測できたのは公開ページの `Final Submission Requirements`（§2 の 7 項目）と `Judging Criteria`（§0）まで。
上の手順 4 のフィールド名は Devpost の一般的なプロジェクト提出フォーム（name / tagline / built with /
thumbnail / gallery / video / repo / additional info / team）に対応させた**作業用の見出し**であり、
実フォームのラベルではない。フォームを開いたら項目名を 1 行ずつこのファイルに追記すること。

## 4. 審査基準への対応（提出文にそのまま書ける形）

| 基準 | 重み | 証拠 |
|---|---|---|
| Technical execution | 30% | `src/perception.py`（ArUco 1.5× upsample＋refine、findHomography、NCC TM_CCOEFF_NORMED、absdiff+Otsu、Laplacian 分散）、`src/agent.py` の決定ラダー、`tests/` 5 passed |
| Innovation | 20% | 同一カメラを撮り直す閉ループ（知覚→判断→行動が 5 step で閉じる）、`results/eval.json` の R 0.494→0.976 |
| Real-world impact | 20% | 1 枚では検査不能な現場（低照度・ピンぼけ・マーカー欠け）での見逃し削減。degraded 40 面で fn 42→2 |
| User experience | 10% | `verdict` と `steps[].reason` が常に返る（ブラックボックスにしない）、`/annotated/{seed}.jpg` |
| Documentation and presentation | 10% | `docs/REPORT.md`、`docs/ARCHITECTURE.md`、4:20 の動画、README の再現 3 コマンド |
| Cloud delivery, reproducibility, responsible operation | 10% | 再現は完全（同一 seed で同一数値）。AWS は `deploy/` に記述のみ＝**この 10 点は取らない**。responsible use は REPORT §7 |

## 5. 弱点（隠さず提出文に書く）

- 合成シーンのみ。実機・実工場データは無い。
- 縮退 40 面で偽スクラッチ 7 個（P 0.920）。統合の副作用で、precision を 0.056 落としている。
- 照明 1 条件・真上カメラ・4 fiducial 可視が前提。実ラインの反射や遮蔽は未評価。
- **AWS 未デプロイ**（`deploy/` は書いてあるが実行していない、課金も無い）。
- 音声ナレーション無し（字幕のみ）。

## 6. この作業場の現在地

```
[x] 実装・テスト（5 passed 実測）
[x] 評価（80 面、eval.json 実測）
[x] レポート／アーキテクチャ図／失敗例
[x] 4:20 のデモ動画（docs/demo_video.mp4・ffprobe 実測済み）
[x] git 1 コミット（98f830f・72 files・31 MB）
[ ] push / YouTube / Devpost フォーム / 保護者同意  ← 人間のみ（§3）
```

## 提出可否の結論（2026-10-20 実測）

- **(A) アカウントはこのコンペに未登録**: `https://devpost.com/submit-to/30984-.../manage/submissions` を開くと「Register for this hackathon.」と表示された（実測）。
- **(B) 登録フォームの必須チェックが「法的成年以上」**: 登録フォーム（`https://opencv26.devpost.com/register?...challenge_id=30984`）の必須チェックボックスの文言は
  `I have read and agree to the eligibility requirements for this hackathon: Above legal age of majority in country of residence`
  ＋ `I have read and agree to be bound by the Official Rules and the Devpost Terms of Service`。
  **未成年者向けの代替経路（保護者同意フォーム等）は画面上に表示されなかった。**
- **(C) 公式ルール本文は13歳以上＋保護者同意**: `evidence/rules.txt:123` =「Participants must be at least 13 years old」＋未成年は保護者/後見人の許可と required platform forms。
- **(D) 結論: 提出しない。** 本人は16歳（未成年）であり、上記 (B) のチェックは事実に反する法定誓約になる。年齢偽装は本プロジェクトの禁止事項（`sushi-money-execution` 規約）に該当するため、代行入力しない。
- **成果物は保全済み**（再利用可）: 公開リポジトリ `https://github.com/maebahesioru/panelscan-agent`（public・main・実測）/ デモ動画 `https://www.youtube.com/watch?v=IoTRT7jfG5M`（限定公開・4:21・HTTP 200 実測）。
- **任意の人間判断ルート**: 保護者が Devpost の未成年者用フォーム（存在する場合）に記入できる状況なら提出可能。本エージェントは実行しない。
- 参考: AWS はルーブリックの 10%（"Cloud delivery, reproducibility, and responsible operation"）であり、**失格要件ではない**（`rules.txt:101-102`）。ブロッカーは AWS ではなく上記 (B) の年齢適誓約。

## 提出実行記録（2026-10-20）

### 完了したこと（すべて実測）

| 項目 | 実測値 |
|---|---|
| 公開リポジトリ | https://github.com/maebahesioru/panelscan-agent （`visibility=PUBLIC` / `defaultBranch=main` / HEAD `a0ccc0e`） |
| リポジトリ衛生 | tracked 合計 13MB、`.venv`・secret・`.env` は 0 件、`docs/demo_video.mp4`(17.9MB) は `.gitignore:20-21` で除外（動画は push していない） |
| デモ動画 | https://www.youtube.com/watch?v=IoTRT7jfG5M （限定公開・4:20・oembed HTTP 200） |
| Devpost プロジェクト | https://devpost.com/software/panelscan-agent （12:04 JST 保存 → "Your edits have been saved!"、匿名 curl で HTTP 200 / 136,792B） |
| 動画埋め込み | 公開ページに `youtube.com/embed/IoTRT7jfG5M` を実測 |
| Built with | aruco / docker / fastapi / numpy / opencv / pytest / uvicorn（**AWS は入れていない**） |
| 画像 | 4 枚（`evidence/scene_2000/2002/2005/2011.png`、各 1000x700）＋キャプション 4 件、サムネイル = scene_2000 |
| "Try it out" | https://github.com/maebahesioru/panelscan-agent |
| 説明文 | Markdown 6,071 字（Inspiration / What it does / How we built it / Challenges / Accomplishments / What we learned / What's next / **Honest status**） |
| スクショ | `evidence/devpost_project_page.png`、`evidence/devpost_project_images.png`、`evidence/devpost_register_gate.png` |

### 未完（人間のみ）— 登録と hackathon への Submit

- **ブロッカー**: 登録フォームの必須アテステーション
  `I have read and agree to the eligibility requirements for this hackathon: Above legal age of majority in country of residence`
  ＋ 可視 reCAPTCHA v2（anchor iframe 304x78 / sitekey `6LduGekr…`）。
- 本人は 16 歳（§ 提出可否の結論 (D)）なので、**この法的誓約をエージェントが代行しない**（本記録を書いている時点でも未チェック）。
- 人間/保護者が行う手順:
  1. `https://opencv26.devpost.com/register?flow%5Bdata%5D%5Bchallenge_id%5D=30984&flow%5Bname%5D=register_for_challenge` を開き、保護者と一緒に 2 つの必須チェックの内容を確認
  2. reCAPTCHA を完了 → **Register**
  3. `https://opencv26.devpost.com/` の **Submit project** → 既存プロジェクト **"PanelScan Agent: agentic visual inspection on OpenCV 5"** を選択（`https://devpost.com/software/panelscan-agent`）
  4. 提出完了画面を確認（プロジェクトは作成・保存済みなので、フォームの入力作業は残っていない）
- 代替経路: Devpost support に未成年の参加要件を照会（`support@devpost.com`）。ただし外部への連絡は本エージェントの禁止事項なので未実行。

### 環境メモ（次回の再利用用）

- 共有 brave（CDP 9222）は**他セッションがタブを横取りする**: `opencv26.devpost.com` を開いたタブだけ数秒で他人の `devpost.com/software/<他人>` へ遷移する（`example.com` は安定、server-side curl は 200）。→ **隔離インスタンス CDP 9223**（`--user-data-dir=/tmp/dp_profile`、元プロファイルから `Local State` と `Default/Cookies` のみコピー）で操作した。ログイン状態は引き継がれた。
- `/software/new`（プロジェクト名フォーム）は **reCAPTCHA 必須**で通らない。**GitHub 連携済みなので `/software/add` →「Import panelscan-agent」** でプロジェクトを作ると reCAPTCHA 無しで作成でき、その後 `/software/panelscan-agent/edit` で全項目（name/tagline/tag_list/description/photo/video_url/urls）を保存できる。
- 保存時に reCAPTCHA は出ない。`#software-save` の実クリックで "Your edits have been saved!" を確認。

### 残課題

- [ ] 登録（Register）＋ hackathon への Submit — 人間/保護者のみ
- [ ] 提出後の Edit 可否確認と最終 URL 記録
- [ ] 締切 **2026-10-27 15:45 JST**（公式ルール表記 Oct 26, 2026 @ 11:45pm PDT）
