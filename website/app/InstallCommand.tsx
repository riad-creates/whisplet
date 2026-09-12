'use client';
import { useState } from 'react';
const command = `(
  set -e
  whisplet_installer=$(mktemp)
  trap 'rm -f "$whisplet_installer"' EXIT
  curl -fsSL https://raw.githubusercontent.com/riad-creates/whisplet/main/scripts/bootstrap.sh -o "$whisplet_installer"
  /bin/bash "$whisplet_installer"
)`;
export default function InstallCommand() {
  const [status, setStatus] = useState('Copy setup command');
  async function copy() {
    try { await navigator.clipboard.writeText(command); setStatus('Copied'); }
    catch { setStatus('Select and copy the text above'); }
  }
  return <div className="install-prompt"><p>Copy this command, paste it into Terminal, and press Return. Setup handles the tools and opens Whisplet when it’s ready.</p><pre><code>{command}</code></pre><button onClick={copy} aria-label="Copy setup command">{status}<span aria-hidden="true">⧉</span></button><span className="sr-only" aria-live="polite">{status}</span></div>;
}
