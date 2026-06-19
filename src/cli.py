import typer
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

from src.crypto.key_manager import KeyManager
from src.sender import Sender
from src.receiver import Receiver
from src.protocol.manifest import ManifestManager
from src.crypto.hashing import Hashing
from src.config import Config
from src.transport.local_transport import LocalTransport

app = typer.Typer(help="Secure Audio Segment Transfer CLI")
console = Console()

@app.command()
def keygen():
    """Generates a master key."""
    try:
        km = KeyManager(Config.MASTER_KEY_PATH)
        km.generate_master_key()
        console.print(f"[green]Master key generated successfully at {Config.MASTER_KEY_PATH}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@app.command()
def send(
    input_dir: Path = typer.Argument(..., help="Path to directory containing at1 to at5"),
    format: str = typer.Option("mp3", "--format", help="Audio format (mp3 or wav)"),
    sender: str = typer.Option("alice", "--sender", help="Sender ID"),
    receiver: str = typer.Option("bob", "--receiver", help="Receiver ID")
):
    """Sends 5 audio segments."""
    try:
        sender_obj = Sender(input_dir, Config.OUTPUT_DIR, format, sender, receiver)
        channel_path = sender_obj.process_and_send()
        console.print(f"[green]Successfully sent segments to channel: {channel_path}[/green]")
    except Exception as e:
        console.print(f"[red]Transfer failed: {e}[/red]")

@app.command()
def receive(
    channel_dir: Path = typer.Argument(..., help="Path to channel directory containing manifest and encrypted files")
):
    """Receives and reconstructs audio segments."""
    try:
        receiver_obj = Receiver(channel_dir, Config.OUTPUT_DIR)
        output_file = receiver_obj.receive_and_process()
        console.print(f"[green]Successfully reconstructed audio: {output_file}[/green]")
        console.print("[green]HASH MATCH: PASS[/green]")
    except Exception as e:
        console.print(f"[red]Receive failed: {e}[/red]")
        console.print("[red]HASH MATCH: FAIL[/red]")

@app.command()
def verify(
    original_path: Path = typer.Argument(..., help="Path to original reference file"),
    reconstructed_path: Path = typer.Argument(..., help="Path to reconstructed file")
):
    """Verifies SHA-256 hash between original and reconstructed file."""
    try:
        if not original_path.exists():
            console.print(f"[red]Original file not found: {original_path}[/red]")
            return
        if not reconstructed_path.exists():
            console.print(f"[red]Reconstructed file not found: {reconstructed_path}[/red]")
            return

        h1 = Hashing.hash_file(original_path)
        h2 = Hashing.hash_file(reconstructed_path)

        table = Table(title="Hash Verification")
        table.add_column("File", style="cyan")
        table.add_column("SHA-256 Hash", style="magenta")
        table.add_row("Original Reference", h1)
        table.add_row("Reconstructed File", h2)
        console.print(table)

        if h1 == h2:
            console.print("[green]RESULT: HASH MATCH: PASS[/green]")
        else:
            console.print("[red]RESULT: HASH MISMATCH: FAIL[/red]")
    except Exception as e:
        console.print(f"[red]Verification error: {e}[/red]")

@app.command()
def inspect(
    channel_dir: Path = typer.Argument(..., help="Path to channel directory")
):
    """Inspects manifest.json in the channel directory."""
    manifest_path = channel_dir / "manifest.json"
    if not manifest_path.exists():
        console.print(f"[red]Manifest not found at {manifest_path}[/red]")
        return
        
    try:
        manifest = ManifestManager.load_manifest(manifest_path)
        console.print("[bold]Manifest Info[/bold]")
        console.print(f"Session ID: {manifest.session_id}")
        console.print(f"Sender: {manifest.sender_id}")
        console.print(f"Receiver: {manifest.receiver_id}")
        console.print(f"Format: {manifest.format}")
        
        table = Table(title="Segments")
        table.add_column("Seq")
        table.add_column("Original")
        table.add_column("Encrypted")
        for seg in manifest.segments:
            table.add_row(str(seg.sequence_number), seg.original_filename, seg.encrypted_filename)
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error inspecting manifest: {e}[/red]")

# ----------------- Attack Simulation Commands -----------------

@app.command("simulate-missing")
def simulate_missing(
    channel_dir: Path,
    segment: str = typer.Option(..., "--segment", help="Segment filename to remove (e.g. at3)")
):
    """Simulates missing segment attack."""
    target = channel_dir / f"{segment}_stego.wav"
    if not target.exists():
        target = channel_dir / f"{segment}.enc"
    if target.exists():
        target.unlink()
        console.print(f"[yellow]Removed {target.name} to simulate missing segment.[/yellow]")
    else:
        console.print(f"[red]File not found: {target}[/red]")

@app.command("simulate-tampering")
def simulate_tampering(
    channel_dir: Path,
    segment: str = typer.Option(..., "--segment", help="Segment filename to tamper (e.g. at2)")
):
    """Simulates tampering by modifying 1 byte."""
    target = channel_dir / f"{segment}_stego.wav"
    if not target.exists():
        target = channel_dir / f"{segment}.enc"
    if target.exists():
        with open(target, "r+b") as f:
            f.seek(10)
            byte = f.read(1)
            f.seek(10)
            f.write(bytes([byte[0] ^ 0xFF]))
        console.print(f"[yellow]Tampered 1 byte in {target.name}[/yellow]")
    else:
        console.print(f"[red]File not found: {target}[/red]")

@app.command("simulate-reorder")
def simulate_reorder(
    channel_dir: Path,
    order: str = typer.Option(..., "--order", help="Comma separated order, e.g. at1,at3,at2,at4,at5")
):
    """Simulates out-of-order segment delivery."""
    # Assuming the current transfer used _stego.wav or .enc
    ext = "_stego.wav" if any(f.name.endswith("_stego.wav") for f in channel_dir.iterdir()) else ".enc"
    order_list = [f"{o.strip()}{ext}" for o in order.split(",")]
    order_path = channel_dir / "received_order.json"
    with open(order_path, "w") as f:
        json.dump(order_list, f)
    console.print(f"[yellow]Simulated receive order: {order_list}[/yellow]")

@app.command("simulate-duplicate")
def simulate_duplicate(
    channel_dir: Path,
    segment: str = typer.Option(..., "--segment", help="Segment to duplicate (e.g. at3)")
):
    """Simulates duplicate segment delivery."""
    target = channel_dir / f"{segment}_stego.wav"
    if not target.exists():
        target = channel_dir / f"{segment}.enc"
    if target.exists():
        dup = channel_dir / f"{target.stem}_copy{target.suffix}"
        import shutil
        shutil.copy2(target, dup)
        console.print(f"[yellow]Duplicated {target.name} as {dup.name}[/yellow]")
    else:
        console.print(f"[red]File not found: {target}[/red]")

@app.command("simulate-replay")
def simulate_replay(
    channel_dir: Path
):
    """Simulates replay attack by calling receive again."""
    console.print(f"[yellow]Simulating replay attack on {channel_dir}...[/yellow]")
    try:
        receive(channel_dir)
    except Exception:
        # Errors expected
        pass

@app.command()
def benchmark(
    mp3_dir: Path = typer.Argument(..., help="Path to mp3 sample data"),
    wav_dir: Path = typer.Argument(..., help="Path to wav sample data"),
    iterations: int = typer.Option(5, "--iterations", help="Number of iterations")
):
    """Runs benchmark."""
    from src.benchmark import Benchmark
    bench = Benchmark(mp3_dir, wav_dir, Config.OUTPUT_DIR, iterations)
    bench.run_all()
    console.print("[green]Benchmark completed. See output/benchmark/.[/green]")

if __name__ == "__main__":
    app()
