# GitHub Push Checklist - Phoenix Real Estate Data Collector

## Pre-Push Security Audit

### 1. Secrets and Credentials Check
- [ ] Run secret scanner: `git secrets --scan` or `truffleHog .`
- [ ] Verify `.env` is in `.gitignore`
- [ ] Check for hardcoded values in:
  ```bash
  grep -r "mongodb://" --exclude-dir=node_modules --exclude-dir=.git .
  grep -r "api_key\|apikey\|API_KEY" --exclude-dir=node_modules --exclude-dir=.git .
  grep -r "password\|secret\|token" --exclude-dir=node_modules --exclude-dir=.git .
  ```
- [ ] Verify no proxy credentials in `config/proxies.yaml`
- [ ] Check `config/production-secrets.yaml.template` contains only placeholders
- [ ] Ensure no API keys in test files: `scripts/test_*.py`

### 2. MongoDB Configuration Verification
- [ ] Confirm connection strings use `localhost:27017` (not production URLs)
- [ ] Check `src/database/config.py` uses environment variables
- [ ] Verify test database configs don't contain production data
- [ ] Ensure MongoDB dumps/backups are excluded in `.gitignore`

### 3. File Cleanup Tasks
- [ ] Remove temporary files:
  ```bash
  find . -name "*.pyc" -delete
  find . -name "__pycache__" -type d -exec rm -rf {} +
  find . -name ".pytest_cache" -type d -exec rm -rf {} +
  find . -name "*.log" -not -path "./.git/*" -delete
  ```
- [ ] Clean up test outputs: `rm -rf htmlcov/ .coverage .tox/`
- [ ] Remove local data files:
  ```bash
  rm -rf data/*.json data/*.csv
  rm -rf backups/*.bak backups/*.dump
  ```
- [ ] Check for large files: `find . -size +50M -not -path "./.git/*"`
- [ ] Remove IDE-specific files not in `.gitignore`

### 4. Code Quality Verification
- [ ] Run linting: `make ruff`
- [ ] Run type checking: `make quick_pyright`
- [ ] Run tests: `uv run pytest`
- [ ] Check test coverage: `uv run pytest --cov`

## Git Commands Sequence

### 5. Pre-Push Git Operations
```bash
# 1. Check current status
git status

# 2. Review changes
git diff --staged
git diff

# 3. Verify .gitignore is working
git check-ignore -v .env
git check-ignore -v config/production-secrets.yaml
git check-ignore -v data/*

# 4. Add files selectively (avoid git add .)
git add src/
git add scripts/
git add tests/
git add docs/
git add pyproject.toml
git add .github/

# 5. Final review before commit
git status
git diff --staged --name-only

# 6. Commit with descriptive message
git commit -m "feat: [component] brief description

- Detail 1
- Detail 2

Refs: #issue_number"
```

### 6. Push to GitHub
```bash
# 1. Verify remote
git remote -v

# 2. Push to feature branch first
git push -u origin feature/your-branch-name

# 3. After PR approval, push to main
git checkout main
git pull origin main
git merge feature/your-branch-name
git push origin main
```

## Post-Push Verification

### 7. GitHub Repository Checks
- [ ] Visit GitHub repo and verify:
  - [ ] No `.env` file visible
  - [ ] No hardcoded secrets in recent commits
  - [ ] GitHub Secrets are configured for Actions
  - [ ] Branch protection rules are active
- [ ] Check Actions tab for workflow status
- [ ] Verify `.github/workflows/` files don't expose secrets
- [ ] Review file sizes in web interface

### 8. Security Scan
- [ ] Enable GitHub security features:
  - Dependabot alerts
  - Secret scanning
  - Code scanning
- [ ] Check Security tab for any alerts
- [ ] Review dependency graph for vulnerabilities

## Emergency Rollback Procedures

### 9. If Secrets Were Exposed
```bash
# 1. Immediately remove from GitHub
git reset --hard HEAD~1  # Undo last commit
git push --force origin main

# 2. Or revert specific file
git rm --cached sensitive_file.txt
git commit -m "Remove sensitive file"
git push

# 3. Rotate all exposed credentials immediately:
# - Generate new API keys
# - Update MongoDB passwords
# - Change proxy credentials
# - Update .env file locally
```

### 10. Complete History Cleanup (Nuclear Option)
```bash
# Use BFG Repo-Cleaner for thorough removal
java -jar bfg.jar --delete-files .env
java -jar bfg.jar --replace-text passwords.txt
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

## Final Checklist

### 11. Documentation Review
- [ ] Update README.md if needed (but don't create unnecessarily)
- [ ] Ensure setup instructions reference `.env.example`
- [ ] Verify all credential instructions use placeholders

### 12. Team Communication
- [ ] Notify team of any credential rotations
- [ ] Document any new environment variables needed
- [ ] Update shared documentation with deployment changes

---

## Quick Reference - Most Common Issues

1. **Exposed MongoDB URL**: Search for `mongodb://` that isn't `localhost`
2. **API Keys in Code**: Look for strings matching key patterns
3. **Large Data Files**: Check `data/` and `backups/` directories
4. **Test Artifacts**: Remove `.pytest_cache`, `htmlcov`, `.coverage`
5. **Log Files**: Clean up `*.log` files with sensitive data

## Emergency Contacts
- GitHub Support: https://support.github.com/
- Security Team: [Your security contact]
- Project Lead: [Your contact]

---
*Last Updated: [Current Date]*
*Review this checklist before every push to main branch*