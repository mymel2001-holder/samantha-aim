# Samantha AIM

An **Ollama-powered chatbot** for AOL Instant Messenger (AIM) using the OSCAR protocol. Instead of a plain interactive client, this bot connects to an AIM-compatible server and automatically replies to every incoming message using a local Ollama model. Each buddy gets their own conversation history so the bot keeps context per person.

## Features

- Connect to an AIM server with username and password.
- Automatically reply to incoming messages using a local **Ollama** model.
- Per-buddy conversation history for context-aware replies.
- Set away status with custom auto-reply: `/away <message>`.
- Auto-reply to incoming messages when away, with a 5-minute cooldown per buddy to avoid spamming.
- Disable away status: `/back`.
- Clear all conversation history: `/reset`.
- Switch the active Ollama model on the fly: `/model <name>`.
- Quit the session: `/quit`.
- Chat logging to `chat_log.txt` with timestamps.
- Colorful console output using the `rich` library.

## Requirements

- Python 3.12+
- A running **Ollama** server (default: `http://localhost:11434`) with at least one model pulled (e.g. `llama3.2`).
- Dependencies:
  - `aimpyfly`: For OSCAR protocol handling.
  - `rich`: For enhanced console output.
  - `ollama`: For talking to the local Ollama server.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/MyMel2001/python-oscar-cli.git
cd python-oscar-cli
```
2. Create a virtual environment and install dependencies:
```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```
3. Make sure Ollama is running and pull a model:
```bash
ollama pull llama3.2
```

## Usage

Run the script with the required arguments:
```
oscar-client.py [-h] --server SERVER [--port PORT] --username USERNAME --password PASSWORD [--model MODEL] [--endpoint ENDPOINT]
```

- `--server`: The AIM server address (required).
- `--port`: The server port (default: 5190).
- `--username`: Your AIM username (required).
- `--password`: Your AIM password (required).
- `--model`: The Ollama model to use for replies (default: `llama3.2`).
- `--endpoint`: The Ollama server endpoint, e.g. `http://localhost:11434` (default: local Ollama).

### Example
```bash
.venv/bin/python3 oscar-client.py \
  --server aim.example.com \
  --username myuser \
  --password mypass \
  --model llama3.2
```

Once connected, the bot automatically replies to every incoming message using the configured Ollama model. A `>` prompt is available for admin commands:

- Set away: `/away Out for lunch`
- Return: `/back`
- Clear history: `/reset`
- Switch model: `/model llama3.1`
- Quit: `/quit`

Incoming messages and AI replies are displayed in real-time with timestamps. Chats are logged to `chat_log.txt`.

## Notes

- The auto-reply feature only triggers if you're away and hasn't replied to that buddy within the last 5 minutes.
- Logs are appended to `chat_log.txt` in the current directory.
- Error handling is basic; connection failures are displayed in the console.
- This is a stateful CLI session—use Ctrl+C to exit if needed.

## Contributing

Contributions are welcome! Feel free to open issues or pull requests on [GitHub](https://github.com/MyMel2001/python-oscar-cli).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
