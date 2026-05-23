import os
import sys
import json
import subprocess
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

console = Console()

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS) / "honeydl"
    PROJECT_DIR = Path.home() / ".config" / "honeydl"
else:
    BASE_DIR = Path(__file__).resolve().parent
    PROJECT_DIR = BASE_DIR.parent

PROJECT_DIR.mkdir(parents=True, exist_ok=True)

LOGO_ASCII = BASE_DIR / "assets" / "honey_logo.txt"
TITLE_ASCII = BASE_DIR / "assets" / "honey_title.txt"
CONFIG_PATH = PROJECT_DIR / "config.json"

DOWNLOAD_DIR = Path.home() / "Downloads" / "HoneyDL"
MUSIC_DIR = DOWNLOAD_DIR / "Music"
VIDEO_DIR = DOWNLOAD_DIR / "Videos"
PLAYLIST_DIR = DOWNLOAD_DIR / "Playlists"
SPOTIFY_DIR = DOWNLOAD_DIR / "Spotify"

for folder in [DOWNLOAD_DIR, MUSIC_DIR, VIDEO_DIR, PLAYLIST_DIR, SPOTIFY_DIR]:
    folder.mkdir(parents=True, exist_ok=True)


DEFAULT_CONFIG = {
    "quick_format": "mp3",
    "quick_quality": "320",
    "embed_metadata": True,
    "embed_thumbnail": True,
}


def load_config():
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            json.dumps(DEFAULT_CONFIG, indent=4),
            encoding="utf-8"
        )
        return DEFAULT_CONFIG

    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_CONFIG


CONFIG = load_config()


def read_ascii_file(path):
    if path.exists():
        return path.read_text(encoding="utf-8").splitlines()
    return []


def open_folder(path):
    if os.name == "nt":
        os.startfile(path)
    else:
        subprocess.run(
            ["xdg-open", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )


def clean_title_template():
    return "%(title).180B.%(ext)s"


def header():
    os.system("cls" if os.name == "nt" else "clear")

    title = read_ascii_file(TITLE_ASCII) or ["HoneyDL"]
    logo = read_ascii_file(LOGO_ASCII) or ["🍯"]

    max_lines = max(len(title), len(logo))

    while len(title) < max_lines:
        title.append("")

    while len(logo) < max_lines:
        logo.append("")

    title_width = max(len(line) for line in title)

    colors = [
        "#FFF176",
        "#FFE066",
        "#FFD54F",
        "#FFCA28",
        "#FFB300",
        "#FB8C00",
        "#D97706",
        "#B45309",
    ]

    for i, (left, right) in enumerate(zip(title, logo)):
        color = colors[min(i, len(colors) - 1)]

        console.print(
            f"[bold {color}]{left.ljust(title_width + 6)}[/bold {color}]"
            f"[bold {color}]{right}[/bold {color}]"
        )

    console.print(
        Panel(
            "[bold #FFD54F]Paste. Choose. Download.[/bold #FFD54F]\n"
            "[dim]YouTube / Spotify downloader minimal • honey edition[/dim]",
            border_style="#FFB300",
        )
    )


def is_spotify_url(url):
    return "open.spotify.com" in url or "spotify.link" in url


def run_download(command, message="🐝 Gathering nectar"):
    honey_steps = [
        "🐝 Gathering nectar",
        "🍯 Filtering sweetness",
        "✨ Polishing metadata",
        "📦 Preparing file",
    ]

    with Progress(
        TextColumn("[bold #FFD54F]{task.description}[/bold #FFD54F]"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:

        task = progress.add_task(message, total=100)

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            universal_newlines=True,
        )

        step_index = 0

        for line in process.stdout:
            if "[download]" in line and "%" in line:
                try:
                    percent = float(line.split("%")[0].split()[-1])

                    if percent > 30 and step_index == 0:
                        step_index = 1
                    elif percent > 65 and step_index == 1:
                        step_index = 2
                    elif percent > 90 and step_index == 2:
                        step_index = 3

                    progress.update(
                        task,
                        completed=percent,
                        description=honey_steps[step_index]
                    )

                except Exception:
                    pass

        process.wait()

        progress.update(
            task,
            completed=100,
            description="🍯 Done brewing"
        )

        return process.returncode == 0


def base_audio_command(url, output_dir, audio_format="mp3", quality="320"):

    if audio_format in ["wav", "flac"]:
        quality = "0"

    command = [
        "yt-dlp",
        url,
        "-x",
        "--audio-format",
        audio_format,
        "--audio-quality",
        quality,
        "--no-mtime",
        "--windows-filenames",
        "--restrict-filenames",
        "--replace-in-metadata",
        "title",
        r"(?i)\s*[\(\[]?(official\s*(music\s*)?video|lyrics?|audio|visualizer|hd|4k)[\)\]]?",
        "",
        "-o",
        str(output_dir / clean_title_template()),
    ]

    if CONFIG.get("embed_metadata", True):
        command.append("--add-metadata")

    if CONFIG.get("embed_thumbnail", True) and audio_format != "wav":
        command.extend([
            "--embed-thumbnail",
            "--convert-thumbnails",
            "jpg"
        ])

    return command


def spotify_command(url):
    return [
        "spotdl",
        url,
        "--output",
        str(SPOTIFY_DIR / "{artist} - {title}.{output-ext}")
    ]


def get_video_format_selector(video_quality):

    if video_quality == "Best":
        return "bv*+ba/b"

    height_map = {
        "2160p / 4K": "2160",
        "1440p / 2K": "1440",
        "1080p": "1080",
        "720p": "720",
        "480p": "480",
    }

    height = height_map[video_quality]

    return f"bv*[height<={height}]+ba/b[height<={height}]"


def video_command(url, format_selector):

    return [
        "yt-dlp",
        url,
        "-f",
        format_selector,
        "--merge-output-format",
        "mp4",
        "--no-mtime",
        "--windows-filenames",
        "--restrict-filenames",
        "--replace-in-metadata",
        "title",
        r"(?i)\s*[\(\[]?(official\s*(music\s*)?video|lyrics?|audio|visualizer|hd|4k)[\)\]]?",
        "",
        "-o",
        str(VIDEO_DIR / clean_title_template()),
    ]


def ask_audio_quality(audio_format):

    if audio_format in ["wav", "flac"]:
        return "0"

    quality = questionary.select(
        "Choose quality:",
        choices=["Best", "320kbps", "192kbps"],
    ).ask()

    return {
        "Best": "0",
        "320kbps": "320",
        "192kbps": "192",
    }[quality]


def main():

    while True:

        header()

        url = questionary.text(
            "Paste your YouTube / Spotify link:"
        ).ask()

        if not url:
            console.print("[red]No link provided.[/red]")
            return

        output_folder = DOWNLOAD_DIR

        if is_spotify_url(url):

            console.print("[yellow]Spotify link detected.[/yellow]")
            console.print(
                "[dim]Saving Spotify downloads inside HoneyDL/Spotify[/dim]\n"
            )

            command = spotify_command(url)

            output_folder = SPOTIFY_DIR

            success = run_download(
                command,
                "🎧 Searching Spotify track"
            )

            if not success:
                console.print(
                    Panel(
                        "[red]Spotify download failed.[/red]\n\n"
                        "Install spotdl with:\n"
                        "[bold]pip install spotdl[/bold]",
                        border_style="red",
                    )
                )

        else:

            mode = questionary.select(
                "Choose mode:",
                choices=[
                    "Quick Download",
                    "Audio",
                    "Video",
                    "Playlist Audio"
                ],
            ).ask()

            if mode == "Quick Download":

                quick_format = questionary.select(
                    "Quick audio format:",
                    choices=["mp3", "m4a", "wav", "opus", "flac"],
                    default=CONFIG.get("quick_format", "mp3"),
                ).ask()

                quality = ask_audio_quality(quick_format)

                output_folder = MUSIC_DIR

                command = base_audio_command(
                    url,
                    MUSIC_DIR,
                    quick_format,
                    quality
                )

            elif mode == "Audio":

                audio_format = questionary.select(
                    "Choose audio format:",
                    choices=["mp3", "m4a", "wav", "opus", "flac"],
                ).ask()

                bitrate = ask_audio_quality(audio_format)

                output_folder = MUSIC_DIR

                command = base_audio_command(
                    url,
                    MUSIC_DIR,
                    audio_format,
                    bitrate
                )

            elif mode == "Playlist Audio":

                playlist_format = questionary.select(
                    "Playlist audio format:",
                    choices=["mp3", "m4a", "opus", "flac"],
                    default=CONFIG.get("quick_format", "mp3"),
                ).ask()

                quality = ask_audio_quality(playlist_format)

                output_folder = PLAYLIST_DIR

                command = base_audio_command(
                    url,
                    PLAYLIST_DIR,
                    playlist_format,
                    quality
                )

            else:

                video_quality = questionary.select(
                    "Choose video quality:",
                    choices=[
                        "Best",
                        "2160p / 4K",
                        "1440p / 2K",
                        "1080p",
                        "720p",
                        "480p",
                    ],
                ).ask()

                format_selector = get_video_format_selector(video_quality)

                output_folder = VIDEO_DIR

                command = video_command(
                    url,
                    format_selector
                )

            console.print()

            success = run_download(command)

        console.print()

        if success:

            console.print(
                Panel(
                    f"[bold green]Done.[/bold green]\n"
                    f"Saved to:\n[bold]{output_folder}[/bold]",
                    border_style="green",
                )
            )

            if questionary.confirm(
                "Open downloads folder?",
                default=False
            ).ask():
                open_folder(output_folder)

        else:
            console.print("[red]Download failed.[/red]")

        again = questionary.confirm(
            "Download another one?",
            default=True
        ).ask()

        if not again:
            console.print(
                "[bold #FFD54F]See you next harvest 🍯[/bold #FFD54F]"
            )
            break


if __name__ == "__main__":
    main()