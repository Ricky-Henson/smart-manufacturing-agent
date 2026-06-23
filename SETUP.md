# Setup / environment constraints

Concrete environment rules for this project. The project **code** can stay here on `C:`
(`...\GenAI\smart-manufacturing-agent`), but everything **large** (models, datasets, caches,
vector store, memory) must live on **`D:\`** because `C:` is limited.

## 1. Ollama models → D:\
Default location is `C:\Users\ricky\.ollama\models`. Move it to D: by setting `OLLAMA_MODELS`
before pulling any model:

```
mkdir D:\ollama\models
setx OLLAMA_MODELS "D:\ollama\models"
```
Then **restart Ollama** (quit from the tray and relaunch) so it picks up the new path. After that,
`ollama pull <model>` downloads to D:. (Verify: the GBs land under `D:\ollama\models`.)

## 2. Project data / memory / caches → D:\
Keep code on C:, but put the heavy, regenerable data on D:. Make one data root and point the
project's config at it:

```
mkdir D:\smart-mfg-agent\data        REM datasets, replayed sensor logs
mkdir D:\smart-mfg-agent\vectorstore REM ChromaDB / embeddings index (if RAG)
mkdir D:\smart-mfg-agent\memory      REM agent long-term memory store
```
In code, read these paths from a config/env value (e.g. `DATA_DIR=D:\smart-mfg-agent\data`) — never
hardcode them in committed source.

## 3. Hugging Face cache → D:\  (only if you use local embeddings, e.g. bge-m3)
`sentence-transformers` / HF models default to `C:\Users\ricky\.cache\huggingface`. Redirect:

```
setx HF_HOME "D:\hf-cache"
```
(Restart your terminal / VS Code after `setx`.)

## 4. If you choose the Spring Boot stack (interface option ii / iii)
Prerequisites to install when/if you go this route:
- **JDK 17+** (21 LTS is fine).
- **Maven or Gradle** (Spring Initializr generates either).
- **Spring AI** with the Ollama starter (`spring-ai-ollama-spring-boot-starter`) — gives
  `ChatClient`, embeddings, function/tool calling, and vector-store RAG against your local Ollama.
- Optional, to keep the Maven cache off C:: point the local repo to D: (Maven `settings.xml`
  `<localRepository>D:\m2-repo</localRepository>`).
- UI: Thymeleaf (server-rendered pages) or a small static frontend served by Spring Boot at
  `localhost:8080`.

If you choose **Python + Streamlit** instead, none of section 4 applies — just Python (≥3.10),
your usual venv/conda, Ollama, and (for RAG) ChromaDB + a local embedding model with `HF_HOME` on D:.

## Reminder — Claude config vs this project
This is your **project** folder (code). It is unrelated to `C:\Users\ricky\ricky-claude`, which is
Claude's config (skills/memory). Don't put project files in the config folder.
