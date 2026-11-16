# 配音接入与正式男声

## 1. 默认行为

auto：若配置引擎是 auto，检查 espeak-ng；存在则使用本地开发男声，不存在输出明确标识的字幕版。选择 none 表示用户主动不需要音轨。

eSpeak 适合闭环验证，不能代表专业配音品质。正式声音走可替换的 Qwen 服务，不把开发声音称为专业播报效果。

## 2. 准备 Qwen 模型

在独立虚拟环境安装 `services/qwen/requirements.txt`。根据机器选择正确的 PyTorch CPU/CUDA wheel；锁定模型仓库 revision，事先下载官方 VoiceDesign 和 Base 权重及 tokenizer。模型和个人参考录音不随本工程分发。

运行音色设计：

```bash
python services/qwen/design_voice.py \
  --model /absolute/models/Qwen3-TTS-12Hz-1.7B-VoiceDesign \
  --output /absolute/voices/professional-male --device cpu
```

试听 reference.wav，必要时调整风格再生成。固定一条满意的参考，避免每章节重新设计声音。

## 3. 启动服务

```bash
export QWEN_BASE_MODEL=/absolute/models/Qwen3-TTS-12Hz-1.7B-Base
export QWEN_REFERENCE_WAV=/absolute/voices/professional-male/reference.wav
export QWEN_REFERENCE_TEXT=/absolute/voices/professional-male/reference.txt
export QWEN_SERVICE_KEY=replace_with_unique_random_service_key
export QWEN_DEVICE=cpu
uvicorn services.qwen.server:app --host 127.0.0.1 --port 7861
```

在 Studio .env 配置：

```dotenv
EXPLAINER_TTS_ENGINE=qwen
EXPLAINER_TTS_URL=http://127.0.0.1:7861
EXPLAINER_TTS_KEY=与QWEN_SERVICE_KEY相同的值
EXPLAINER_TTS_REVISION=professional-male-v1
```

改变音色、模型或主要生成参数时更新 TTS_REVISION，避免命中旧音频缓存。建议同时清晰管理模型版本和参考授权，不在名字中冒充真实人物。

## 4. 服务协议

`POST /synthesize`，Bearer 服务密钥，JSON `{text,language}`，返回 WAV。只支持本版开放的 zh-CN/en-US，串行锁避免共享模型的并发显存冲突。服务不自动下载权重，环境默认 HF offline，并禁用已知 telemetry。需要严格零网络时，仍应在部署层禁止模型进程出站；环境变量本身不是网络沙箱。

## 5. 音频与字幕

原始音频转 48kHz mono WAV，基础高通与 loudnorm。验收应看最终成片实际听感、响度和真峰值；本版自动质检验证解码和音轨存在，不声称已完成专业播音质量认证。

V2 支持 eSpeak 原生 WORD 事件，以及 stable-ts/Whisper 已知文本强制对齐。安装 services/alignment/requirements.txt，设置 EXPLAINER_ALIGNMENT_ENGINE=stable-ts、ALIGNMENT_PYTHON 与 ALIGNMENT_MODEL（均带 EXPLAINER_ 前缀）。勾选真实对齐后，模型未就绪会失败，不回退到估时。alignment.json 记录逐词时标；小模型对齐仍需人工抽查。


## V2 已验证配置

实际验证使用 Qwen3-TTS-12Hz-0.6B-Base，模型 revision 见验收报告。可使用 `assets/voices/professional-male/reference.wav` 和 `reference.txt`；该参考为之前演示使用的合成男声，不是真实人物录音。风格仍应由使用者试听确认。

Linux 需 `libseccomp.so.2`。HTTP 网关通过管道与常驻模型子进程通信，模型子进程在导入推理库前禁止创建 IPv4/IPv6 socket；内核策略加载失败直接终止。此机制专用于语音模型，不能替代源码执行容器。非 Linux 部署需相应适配，当前不自动放宽。
