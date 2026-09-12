'use client';
import { useState } from 'react';
const prompt = 'Clone https://github.com/tobiwsa/whisplet, read AGENTS.md, and help me install it on this Mac. Use F5 hold-to-record with S1 cleanup off.';
export default function InstallCommand() {
  const [status, setStatus] = useState('Copy prompt');
  async function copy() {
    try { await navigator.clipboard.writeText(prompt); setStatus('Copied'); }
    catch { setStatus('Select and copy the text above'); }
  }
  return <div className="install-prompt"><p>{prompt}</p><button onClick={copy} aria-label="Copy installation prompt">{status}<span aria-hidden="true">⧉</span></button><span className="sr-only" aria-live="polite">{status}</span></div>;
}
