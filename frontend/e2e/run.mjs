import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
const python = fileURLToPath(new URL(process.platform === 'win32' ? '../../.venv/Scripts/python.exe' : '../../.venv/bin/python', import.meta.url))
const result = spawnSync(python, ['-B', 'e2e/run.py', ...process.argv.slice(2)], { stdio: 'inherit' })
if (result.error) console.error(result.error.message)
process.exit(result.status ?? 1)
