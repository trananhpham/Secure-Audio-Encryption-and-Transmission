import time
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from src.sender import Sender
from src.receiver import Receiver
from src.utils.logger import logger
from src.crypto.hashing import Hashing
from src.config import Config
from src.audio.input_loader import InputLoader
from src.audio.metadata import AudioMetadata
import shutil

class Benchmark:
    def __init__(self, mp3_dir: Path, wav_dir: Path, output_base: Path, iterations: int = 5):
        self.mp3_dir = mp3_dir
        self.wav_dir = wav_dir
        self.output_base = output_base
        self.iterations = iterations
        self.benchmark_dir = self.output_base / "benchmark"
        self.benchmark_dir.mkdir(parents=True, exist_ok=True)
        self.results = []

    def _get_size_and_duration(self, input_dir: Path, fmt: str) -> tuple[int, float]:
        paths = InputLoader.load_and_validate(input_dir, fmt)
        total_size = sum(p.stat().st_size for p in paths)
        total_duration = sum(AudioMetadata.get_info(p)["duration"] for p in paths)
        return total_size, total_duration

    def run_iteration(self, fmt: str, input_dir: Path) -> dict:
        total_size, total_duration = self._get_size_and_duration(input_dir, fmt)
        
        # Clean temp
        if (self.output_base / "sender").exists():
            shutil.rmtree(self.output_base / "sender")
        if (self.output_base / "channel").exists():
            shutil.rmtree(self.output_base / "channel")
        if (self.output_base / "receiver").exists():
            shutil.rmtree(self.output_base / "receiver")

        t_start = time.time()
        
        # Sender
        t0 = time.time()
        sender = Sender(input_dir, self.output_base, fmt, "alice", "bob")
        channel_path = sender.process_and_send()
        t_send = time.time() - t0
        
        # Receiver
        t0 = time.time()
        receiver = Receiver(Path(channel_path), self.output_base)
        reconstructed_path = receiver.receive_and_process()
        t_recv = time.time() - t0
        
        t_total = time.time() - t_start
        
        # Throughput
        enc_mbps = (total_size / (1024 * 1024)) / t_send if t_send > 0 else 0
        dec_mbps = (total_size / (1024 * 1024)) / t_recv if t_recv > 0 else 0
        
        # Get hash
        orig_hash = Hashing.hash_file(self.output_base / "reference" / f"original_reference.{fmt}")
        recon_hash = Hashing.hash_file(reconstructed_path)
        
        # Storage overhead (Manifest size + Nonces + HMAC)
        channel_size = sum(f.stat().st_size for f in Path(channel_path).iterdir() if f.is_file())
        overhead = channel_size - total_size

        return {
            "format": fmt,
            "total_size_bytes": total_size,
            "total_duration_sec": total_duration,
            "send_time_sec": t_send,
            "recv_time_sec": t_recv,
            "total_time_sec": t_total,
            "enc_throughput_mbps": enc_mbps,
            "dec_throughput_mbps": dec_mbps,
            "storage_overhead_bytes": overhead,
            "original_hash": orig_hash,
            "reconstructed_hash": recon_hash,
            "hash_match": "PASS" if orig_hash == recon_hash else "FAIL"
        }

    def run_all(self):
        for i in range(self.iterations):
            logger.log_benchmark(f"Iteration {i+1} - MP3")
            self.results.append(self.run_iteration("mp3", self.mp3_dir))
            logger.log_benchmark(f"Iteration {i+1} - WAV")
            self.results.append(self.run_iteration("wav", self.wav_dir))
        
        df = pd.DataFrame(self.results)
        
        # Save CSV
        df.to_csv(self.benchmark_dir / "benchmark_results.csv", index=False)
        
        # Save JSON
        with open(self.benchmark_dir / "benchmark_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Create Chart
        self._plot_results(df)
        
        # Create Report
        self._create_markdown_report(df)

    def _plot_results(self, df: pd.DataFrame):
        avg = df.groupby("format")[["send_time_sec", "recv_time_sec"]].mean()
        avg.plot(kind="bar", figsize=(8, 5))
        plt.title("Average Processing Time by Format")
        plt.ylabel("Time (seconds)")
        plt.tight_layout()
        plt.savefig(self.benchmark_dir / "benchmark_chart.png")

    def _create_markdown_report(self, df: pd.DataFrame):
        avg = df.groupby("format").mean(numeric_only=True)
        report = f"""# Benchmark Report

## Average Results

{avg.to_markdown()}

## Chart
![Benchmark Chart](benchmark_chart.png)
"""
        with open(Config.PROJECT_ROOT / "docs" / "benchmark_report.md", "w", encoding="utf-8") as f:
            f.write(report)
