# Instructions for invoking the UI-less version of gpt-researcher in Docker Compose

## Environment variables

Set up `.env` with the following values (substituting with real values as appropriate):

```
OPENAI_BASE_URL=http://vllm-server:7000/v1
OPENAI_API_BASE=http://vllm-server:7000/v1
OPENAI_API_KEY=token-abc123

FAST_LLM=openai:openai/gpt-oss-20b
SMART_LLM=openai:openai/gpt-oss-20b
STRATEGIC_LLM=openai:openai/gpt-oss-20b
EMBEDDING=huggingface:sentence-transformers/all-MiniLM-L6-v2

TAVILY_API_KEY=tvly-XXX								 <-- update this line
TAVILY_SEARCH_DEPTH=advanced

LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=lsv2_XXX							<-- update this line
LANGCHAIN_PROJECT=gpt-researcher-1
```

Create a Tavily account and generate an API key [here](https://docs.tavily.com/documentation/api-credits).

Create a LangSmith account and generate an API key [here](https://docs.langchain.com/langsmith/create-account-api-key). (Note: you still need the LangSmith account, even to download
the trace CSV file locally.)

## Docker Compose

The `docker-compose.yml` file uses the default latest vLLM Docker image. The `gpt-researcher` image needs to be built:
```
docker compose build gpt-researcher-cli
```

Start the vLLM + gpt-researcher containers with the automated profiling script (includes GPU/CPU/memory monitoring) and a plotting script:
```bash
./profile_docker.sh
```

Alternatively, you can run this command to run and automatically clean up the docker containers:
```bash
docker compose up --abort-on-container-exit --exit-code-from gpt-researcher-cli && docker compose down
```

The output files (STDOUT, LangSmith trace CSV, agent output reports, etc) are all saved to `./outputs/`.