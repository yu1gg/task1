# P3 语音面试验证与运行说明

日期：2026-11-14。代码已实现，真实DeepSeek/SiliconFlow联调未完成。

## 已交付

学生可选择岗位、技术面/HR面及可选本人简历，默认完成5题（配置允许5–8题）。启动时快照岗位、资料、简历版本与题数，不把联系方式发送至AI。AI读题、浏览器录音/文件上传、试听重录、语音识别、引用回答追问、评分、失败重试与报告已接通。报告总分为四维均值，沟通分仅评价转写的组织与清晰度，不评价声纹、情绪或口音。

状态存入数据库，后台单消费者处理。转码与网络请求在事务外；条件更新领取任务，完成题目与创建下一题同事务。重启可恢复中断任务，已识别的转写可复用；崩溃恢复可能重复调用外部服务，不保证计费恰好一次。

私有音频通过学生所有权校验读取，轮询不返回本地路径；UUID命名，上传按块限额，原文件保留以供本人回听。临时转码文件和普通失败/竞争中未采用文件会清理。异常断电可能留下未引用文件，首期没有自动清理长期存储的策略，部署时需管理容量和备份。

## 测试证据

最终自动化结果：**175 passed，401 warnings，37.65秒**。警告来自现有Starlette和Python 3.13下的SQLAlchemy `datetime.utcnow()` 弃用提示。JavaScript语法检查通过，修复取消播放竞态后的五题浏览器流程也已重跑通过。

- 原111项基线测试通过。新增语音协议、结构校验、状态恢复、生命周期、上传/重试、私有访问、报告题数、迁移等测试。
- 使用真实ffmpeg验证WAV、MP3、WebM/Opus、M4A/AAC及伪装扩展名的转码；拒绝91秒音频及损坏文件。其他边界由模拟进程测试覆盖，包括视频轨、超大小、进程超时及部分输出清理。
- Edge真实浏览器中注入模拟外部服务，完成5题、生成报告；验证实际MediaRecorder录音和试听、文件上传、刷新恢复、390px手机视口、麦克风拒绝后上传。
- 独立审查发现并修复：关闭消费者只等2秒可能与新消费者重叠；录音开始时旧播放Promise被取消却触发浏览器朗读。对应慢服务与浏览器取消播放回归均纳入验证。
- 测试数据及截图在忽略目录 `data/qa/p3/`，不是10位真实用户的使用证据。模拟ASR结果和评分仅存在测试注入代码，不作为产品降级输出。

复跑自动测试与JS语法检查：

```powershell
.\.venv\Scripts\python.exe -m pytest -o addopts='' -q --disable-warnings
node --check app/static/js/interview.js
```

## 本地配置与启动

复制 `.env.example` 至 `.env` 时保留已有设置，不覆盖现有密钥。请在本机编辑器中填写 `DEEPSEEK_API_KEY` 和 `SILICONFLOW_API_KEY`，不要发送至聊天或提交仓库。语音模型默认为SenseVoiceSmall和CosyVoice2-0.5B，默认音色alex，参数均可在环境变量修改。

本机已将ffmpeg/ffprobe解压到忽略目录 `data/tools/ffmpeg/`，本地 `.env` 已设置对应路径，且生成了会话随机密钥；未填入任何真实外部API Key。新环境需安装ffmpeg并配置 `FFMPEG_PATH`、`FFPROBE_PATH`。Windows下载来源为 [FFmpeg官方下载页列出的Gyan构建](https://ffmpeg.org/download.html)，Linux可用系统包管理器安装。

已有数据库升级（必须先停止服务；新数据库不需要迁移）：

```powershell
.\.venv\Scripts\python.exe -m scripts.migrate_p3
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

迁移使用SQLite backup接口，备份为原数据库旁的 `app.db.p3-backup-时间戳`，只添加缺失列；本机已完成备份迁移并验证重复执行无更改。若启动提示表结构过旧，请停服务执行迁移，不删除旧数据库。恢复备份也必须在服务完全停止后操作。

单数据库只允许一个应用实例及一个消费者，不能通过多个worker横向扩展。优雅关闭会等待当前任务及有限重试完成；不要在旧进程仍退出时启动另一个实例。浏览器录音只在localhost/HTTPS可用，HTTP提供音频上传；录音切到后台时主动停止，避免后台定时器节流。

接口参考：[SiliconFlow识别](https://docs.siliconflow.cn/docs/api/audio-transcriptions-post)、[SiliconFlow合成](https://docs.siliconflow.cn/docs/api/audio-speech-post)。

## 未验证与后续

缺少真实API Key，尚未完成真实识别、音色、追问质量、响应时间及费用验证，不将模拟闭环记作真实联调通过。手机仅做Edge窄视口测试，未实际验证iOS Safari或Android硬件麦克风；公网HTTPS与10用户并发测试留待部署阶段。

本阶段按用户要求替换原视频面试，不再使用摄像头。课程原视频要求是否认可语音方案，仍需用户核实。本记录对应P3阶段；后续P4已实现，P5仍待开发。P3实施时缺少`.git`，当时未执行Git操作；交接时已恢复`p1-foundation`历史，最新状态以HANDOVER和git log为准。
