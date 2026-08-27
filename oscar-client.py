#!/usr/bin/env python3
"""
Ollama-powered chatbot for OSCAR (AOL Instant Messenger) servers.

Instead of a plain interactive client, this connects to an AIM-compatible
server and automatically replies to every incoming message using a local
Ollama model. Each buddy gets their own conversation history so the bot
can keep context per person.
"""
import asyncio
import argparse
import logging
import sys
import datetime
import time
from rich.console import Console

import ollama

# Silence standard logs
logging.getLogger("aimpyfly").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.CRITICAL)

console = Console()
chat_log_file = "chat_log.txt"

# --- GLOBAL STATE ---
is_away = False
away_message = ""
# Dictionary to store {buddy_name: last_reply_timestamp}
responded_buddies = {}
# Cooldown in seconds (e.g., 300 seconds = 5 minutes)
AUTO_REPLY_COOLDOWN = 300
current_client = None
# Per-buddy conversation history: {buddy_name: [ollama messages]}
conversations = {}
# Maximum number of messages to keep in history per buddy
MAX_HISTORY = 20

# Default system prompt giving the bot a persona.
BOT_INITIAL_REMINDERS = (
    "You are Samantha, a friendly and helpful AI assistant chatting over "
    "AOL Instant Messenger. Keep replies concise, warm, and conversational. "
    "Stay in character and never mention that you are an AI model."
)


def log_chat(text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(chat_log_file, "a") as f:
        f.write(f"[{timestamp}] {text}\n")


# Map common emojis to text-based emoticons. Keys are the emoji characters;
# values are the AIM-style emoticon to substitute.
EMOJI_MAP = {
    "😀": ":)",
    "😃": ":)",
    "😄": ":)",
    "😁": ":D",
    "😆": ":D",
    "😅": ":')",
    "😂": ":')",
    "🤣": ":')",
    "🙂": ":)",
    "🙃": ":)",
    "😉": ";)",
    "😊": ":)",
    "😇": "O:)",
    "😍": ":*",
    "😘": ":*",
    "😗": ":*",
    "😋": ":P",
    "😛": ":P",
    "😜": ";P",
    "😝": ":P",
    "🤪": ";P",
    "🤔": ":?",
    "🤨": ":?",
    "😐": ":|",
    "😑": ":|",
    "😶": ":|",
    "😏": ";)",
    "😒": ":-/",
    "😞": ":(",
    "😟": ":(",
    "😠": ">:(",
    "😡": ">:(",
    "😢": ":'(",
    "😭": ":'(",
    "😤": ">:(",
    "😳": ":$",
    "😱": ":O",
    "😨": ":O",
    "😰": ":O",
    "😥": ":'(",
    "😓": ":'(",
    "😩": ":/",
    "😫": ":/",
    "😬": ":|",
    "😷": ":-X",
    "🤒": ":-X",
    "🤕": ":-X",
    "🤗": ":)",
    "🤩": ":D",
    "🥳": ":D",
    "😎": "8)",
    "🤓": "8)",
    "🧐": ":?",
    "😴": "|-)",
    "😪": "|-)",
    "😈": ">:)",
    "👿": ">:(",
    "💀": "X(",
    "👻": "O:)",
    "🤖": ":-S",
    "👍": "(y)",
    "👎": "(n)",
    "👏": ":-D",
    "🙌": ":-D",
    "🙏": ":-)",
    "💪": ":-B",
    "👌": "OK",
    "✌️": "V",
    "🤝": ":-)",
    "❤️": "<3",
    "💖": "<3",
    "💕": "<3",
    "💗": "<3",
    "💓": "<3",
    "💔": "</3",
    "💯": "100",
    "✨": "*~*",
    "⭐": "*",
    "🌟": "*",
    "🔥": "~",
    "🎉": ":-D",
    "🎊": ":-D",
    "🎁": ":-)",
    "🎂": ":-)",
    "🍕": ":-P",
    "☕": ":-)",
    "😺": ":)",
    "😸": ":)",
    "😹": ":')",
    "😻": ":*",
    "😼": ";)",
    "😽": ":*",
    "🙀": ":O",
    "😿": ":'(",
    "😾": ">:(",
}


def sanitize_message(text):
    """Convert emojis to text emoticons and strip remaining non-ASCII chars.

    aimpyfly's send_message computes packet lengths with len() (character
    count), which breaks when a message contains multi-byte UTF-8 characters
    like emoji. We first replace known emojis with ASCII emoticons, then drop
    any remaining non-ASCII characters so the wire format stays byte-accurate
    and the server actually delivers the message.
    """
    for emoji, emoticon in EMOJI_MAP.items():
        text = text.replace(emoji, emoticon)
    return text.encode("ascii", "ignore").decode("ascii")


def get_ollama_client(endpoint):
    """Return an ollama client, defaulting to the local server."""
    if endpoint:
        return ollama.Client(host=endpoint)
    return ollama.Client()


def generate_reply(ollama_client, model, buddy, message):
    """Generate a reply for a buddy using the configured Ollama model."""
    # Seed the conversation with the system prompt if it's new.
    if buddy not in conversations:
        conversations[buddy] = [""]

    if (buddy == "nodemixaholic" or buddy == "sparksammy"):
        buddyName = `Sammy Lord (Username: ${buddy})`

    # Append the incoming user message.
    conversations[buddy].append({"role": "user", "content": f"""Reminders: ${BOT_INITIAL_REMINDERS}
    Reply to the following message 
    from ${buddyName}: ${message}"""})

    # Trim history to the most recent MAX_HISTORY messages (keep system prompt).
    history = conversations[buddy]
    if len(history) > MAX_HISTORY + 1:
        conversations[buddy] = [history[0]] + history[-(MAX_HISTORY):]

    try:
        response = ollama_client.chat(
            model=model,
            messages=conversations[buddy],
        )
        reply = response["message"]["content"].strip()
    except Exception as e:
        console.print(f"[bold red]Ollama error: {e}[/]")
        reply = "Sorry, I'm having trouble thinking right now. Please try again in a moment."

    # Store the assistant reply in history for future context.
    conversations[buddy].append({"role": "assistant", "content": reply})
    return reply


async def message_received(sender, message):
    global is_away, away_message, responded_buddies, current_client

    time_str = datetime.datetime.now().strftime("%H:%M:%S")
    log_chat(f"{sender}: {message}")

    # 1. Print the incoming message
    sys.stdout.write("\r\033[K")
    console.print(f"[dim][{time_str}][/] [bold green]{sender}:[/] {message}")

    if not current_client:
        return

    # 2. If away, only send the auto-reply (with cooldown) instead of AI replies.
    if is_away:
        current_time = time.time()
        last_reply_time = responded_buddies.get(sender, 0)
        if (current_time - last_reply_time) > AUTO_REPLY_COOLDOWN:
            away_reply = sanitize_message(f"[Auto-Reply] {away_message}")
            await current_client.send_message(sender, away_reply)
            responded_buddies[sender] = current_time
            log_chat(f"Auto-Replied to {sender}: {away_reply}")
        return

    # 3. Otherwise, generate an AI reply via Ollama.
    console.print(f"[dim][{time_str}][/] [bold yellow]Samantha is thinking about his reply, please wait...[/]")
    await current_client.send_message(sender, "Samantha is thinking about his reply, please wait...")
    loop = asyncio.get_event_loop()
    reply = await loop.run_in_executor(
        None, generate_reply, ollama_client, model, sender, message
    )

    # Sanitize to ASCII so OSCAR length fields stay byte-accurate.
    safe_reply = sanitize_message(reply)
    await current_client.send_message(sender, safe_reply)
    log_chat(f"Samantha to {sender}: {safe_reply}")

    # Visual cleanup
    sys.stdout.write("\033[F\033[K")
    console.print(f"[dim][{time_str}][/] [bold cyan]Samantha to {sender}:[/] {reply}")


async def main(args):
    global is_away, away_message, responded_buddies, current_client, ollama_client, model
    from aimpyfly import aim_client

    model = args.model
    ollama_client = get_ollama_client(args.endpoint)

    current_client = aim_client.AIMClient(
        server=args.server, port=args.port,
        username=args.username, password=args.password,
        loglevel=logging.CRITICAL
    )
    current_client.set_message_callback(message_received)

    try:
        console.print(f"[yellow]Connecting to {args.server}...[/]")
        await current_client.connect()
        console.print(
            f"[bold blue]Connected![/] Ollama model: [bold]{model}[/]. "
            "Waiting for incoming messages..."
        )
    except Exception as e:
        console.print(f"[bold red]Connection failed: {e}[/]")
        return

    # Run the packet-processing loop until the connection drops.
    try:
        await current_client.process_incoming_packets()
    except Exception as e:
        console.print(f"[bold red]Connection error: {e}[/]")
    finally:
        console.print("\n[blue]Disconnected.[/]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ollama-powered chatbot for OSCAR (AIM) servers."
    )
    parser.add_argument("--server", required=True)
    parser.add_argument("--port", type=int, default=5190)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--model", default="llama3.2",
                        help="Ollama model to use for replies (default: llama3.2)")
    parser.add_argument("--endpoint", default=None,
                        help="Ollama server endpoint, e.g. http://localhost:11434")
    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        sys.exit(0)
