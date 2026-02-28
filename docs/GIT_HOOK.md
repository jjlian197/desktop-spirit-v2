# Git Auto-Push Hook

This project uses a Git post-commit hook to automatically push changes to GitHub.

## How it works

After every `git commit`, the hook automatically runs `git push origin main`.

## Setup

The hook is located at:
```
.git/hooks/post-commit
```

If you need to recreate it:
```bash
#!/bin/bash
echo "🐱 Auto-pushing to GitHub..."
git push origin main
```

Make it executable:
```bash
chmod +x .git/hooks/post-commit
```

## Usage

Simply commit as usual:
```bash
git commit -m "Your message"
# Automatically pushes to GitHub!
```

---
Configured by Sherry 💜
