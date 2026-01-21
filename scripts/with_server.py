#!/usr/bin/env python3
"""
Server lifecycle manager for e2e testing.
Starts servers, waits for readiness, runs tests, and cleans up.

Usage:
  python scripts/with_server.py --server "backend command" --port 8000 \\
                                  --server "frontend command" --port 5173 \\
                                  -- python test_script.py
"""

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import List, Tuple


class ServerManager:
    def __init__(self, servers: List[Tuple[str, int]], max_wait: int = 60):
        self.servers = servers
        self.max_wait = max_wait
        self.processes = []

    def start_servers(self):
        """start all servers"""
        print("starting servers...")
        for cmd, port in self.servers:
            print(f"  starting: {cmd} (port {port})")
            # use shell=True to support commands with cd and &&
            # don't pipe stdout/stderr to avoid deadlock when buffers fill
            proc = subprocess.Popen(
                cmd,
                shell=True,
                preexec_fn=os.setsid,  # create process group for cleanup
            )
            self.processes.append((proc, port))

    def wait_for_ready(self):
        """wait for all servers to be ready"""
        print("waiting for servers to be ready...")
        for proc, port in self.processes:
            url = f"http://localhost:{port}"
            if port == 8000:
                url = f"{url}/health"  # backend health endpoint

            start_time = time.time()
            while time.time() - start_time < self.max_wait:
                try:
                    with urllib.request.urlopen(url, timeout=2) as response:
                        if response.status == 200:
                            print(f"  server on port {port} is ready")
                            break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(1)
            else:
                print(f"  timeout waiting for server on port {port}")
                self.cleanup()
                sys.exit(1)

    def cleanup(self):
        """stop all servers"""
        print("stopping servers...")
        for proc, port in self.processes:
            try:
                # kill process group to clean up child processes
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=5)
                print(f"  stopped server on port {port}")
            except Exception as e:
                print(f"  error stopping server on port {port}: {e}")
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except OSError:
                    pass

    def run_command(self, command: List[str]) -> int:
        """run test command and return exit code"""
        print(f"running: {' '.join(command)}")
        try:
            result = subprocess.run(command)
            return result.returncode
        except KeyboardInterrupt:
            print("\ninterrupted by user")
            return 130


def main():
    parser = argparse.ArgumentParser(
        description="Start servers, run command, and cleanup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # single server
  python scripts/with_server.py --server "npm run dev" --port 5173 -- python test.py

  # multiple servers
  python scripts/with_server.py \\
    --server "cd backend && python server.py" --port 3000 \\
    --server "cd frontend && npm run dev" --port 5173 \\
    -- python test.py
        """,
    )

    parser.add_argument(
        "--server",
        action="append",
        dest="servers",
        help="server command (can be specified multiple times)",
    )
    parser.add_argument(
        "--port",
        action="append",
        dest="ports",
        type=int,
        help="server port (must match --server order)",
    )
    parser.add_argument(
        "--max-wait",
        type=int,
        default=60,
        help="max seconds to wait for servers (default: 60)",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command to run")

    args = parser.parse_args()

    # validate arguments
    if not args.servers or not args.ports:
        parser.error("at least one --server and --port required")

    if len(args.servers) != len(args.ports):
        parser.error("number of --server and --port must match")

    # strip leading '--' from command if present
    command = args.command
    if command and command[0] == "--":
        command = command[1:]

    if not command:
        parser.error("command to run is required after --")

    # create server list
    servers = list(zip(args.servers, args.ports))

    # run with server lifecycle management
    manager = ServerManager(servers, max_wait=args.max_wait)

    try:
        manager.start_servers()
        manager.wait_for_ready()
        exit_code = manager.run_command(command)
    finally:
        manager.cleanup()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
